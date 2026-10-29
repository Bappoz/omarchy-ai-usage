#!/usr/bin/env python3
"""Aggregate local Claude Code / Codex session logs into token and model insights.

Privacy boundary: the logs contain conversations. This module reads them as a
stream, keeps only a timestamp, a model name, an optional effort label and token
counts per request, and never emits prompts, paths, session ids or any other
text. Output is one small JSON document on stdout.

"Tokens" means fresh tokens: input + output (+ cache writes for Claude). Cache
reads are excluded because they re-count the same context on every request.
This is a usage indicator, not a billing figure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
PROVIDERS = ("claude", "codex", "antigravity", "cursor")
HOURS = 24
MODEL_WINDOW_DAYS = 7
MAX_FILES = 500
MAX_FILE_BYTES = 256 * 1024 * 1024
MAX_MODELS = 5
IGNORED_MODELS = {"", "<synthetic>"}


@dataclass(frozen=True)
class Event:
    at: datetime
    model: str
    tokens: int
    effort: str | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def as_count(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def claude_root() -> Path:
    configured = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(configured) if configured else Path.home() / ".claude") / "projects"


def codex_root() -> Path:
    configured = os.environ.get("CODEX_HOME")
    return (Path(configured) if configured else Path.home() / ".codex") / "sessions"


def recent_logs(root: Path, since: datetime) -> list[Path]:
    """Newest-first regular *.jsonl files touched since the cutoff."""
    if not root.is_dir():
        return []
    cutoff = since.timestamp()
    found: list[tuple[float, Path]] = []
    for path in root.rglob("*.jsonl"):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            stat = path.stat()
        except OSError:
            continue
        if stat.st_mtime >= cutoff and stat.st_size <= MAX_FILE_BYTES:
            found.append((stat.st_mtime, path))
    found.sort(reverse=True)
    return [path for _, path in found[:MAX_FILES]]


def read_lines(path: Path) -> Iterator[str]:
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            yield from handle
    except OSError:
        return


def loads(line: str) -> dict[str, Any] | None:
    try:
        value = json.loads(line)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def claude_events(root: Path, since: datetime) -> list[Event]:
    # Claude Code writes one line per content block of a message, repeating the
    # same usage, and resumed sessions copy earlier history. Dedupe by message id
    # across every file and keep the largest reading (streamed usage only grows).
    best: dict[str, Event] = {}
    anonymous: list[Event] = []
    for path in recent_logs(root, since):
        for line in read_lines(path):
            if '"usage"' not in line or '"assistant"' not in line:
                continue
            record = loads(line)
            message = record.get("message") if record else None
            if not record or record.get("type") != "assistant" or not isinstance(message, dict):
                continue
            usage = message.get("usage")
            model = message.get("model")
            at = parse_time(record.get("timestamp"))
            if not isinstance(usage, dict) or not isinstance(model, str) or at is None:
                continue
            if model in IGNORED_MODELS or at < since:
                continue
            tokens = (
                as_count(usage.get("input_tokens"))
                + as_count(usage.get("output_tokens"))
                + as_count(usage.get("cache_creation_input_tokens"))
            )
            effort = record.get("effort")
            event = Event(at, model, tokens, effort if isinstance(effort, str) else None)
            key = message.get("id") or record.get("requestId")
            if not isinstance(key, str):
                anonymous.append(event)
            elif key not in best or event.tokens >= best[key].tokens:
                best[key] = event
    return [*best.values(), *anonymous]


def codex_fresh(usage: object) -> int | None:
    if not isinstance(usage, dict):
        return None
    cached = as_count(usage.get("cached_input_tokens"))
    return max(0, as_count(usage.get("input_tokens")) - cached) + as_count(usage.get("output_tokens"))


def codex_events(root: Path, since: datetime) -> list[Event]:
    # token_count fires for rate-limit refreshes too, with unchanged totals, so
    # the per-request cost is the delta of the cumulative total within a file.
    events: list[Event] = []
    for path in recent_logs(root, since):
        model, effort = "", None
        previous = 0
        for line in read_lines(path):
            if "token_count" not in line and '"turn_context"' not in line:
                continue
            record = loads(line)
            payload = record.get("payload") if record else None
            if not record or not isinstance(payload, dict):
                continue
            if record.get("type") == "turn_context":
                name = payload.get("model")
                model = name if isinstance(name, str) else model
                level = payload.get("effort")
                effort = level if isinstance(level, str) else effort
                continue
            if payload.get("type") != "token_count":
                continue
            info = payload.get("info")
            total = codex_fresh(info.get("total_token_usage")) if isinstance(info, dict) else None
            at = parse_time(record.get("timestamp"))
            if total is None or at is None or model in IGNORED_MODELS:
                continue
            delta = total - previous if total >= previous else total
            previous = total
            if delta > 0 and at >= since:
                events.append(Event(at, model, delta, effort))
    return events


COLLECTORS = {"claude": (claude_root, claude_events), "codex": (codex_root, codex_events)}


def build_insights(provider_id: str, events: list[Event], now: datetime, *, available: bool) -> dict[str, Any]:
    end = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    start = end - timedelta(hours=HOURS)
    hourly = [0] * HOURS
    per_model: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    requests_24h = 0
    for event in events:
        if start <= event.at < end:
            hourly[int((event.at - start).total_seconds() // 3600)] += event.tokens
            requests_24h += 1
        entry = per_model[event.model]
        entry[0] += event.tokens
        entry[1] += 1

    ranked = sorted(per_model.items(), key=lambda item: item[1][0], reverse=True)
    total_tokens = sum(tokens for _, (tokens, _) in ranked)
    models = [
        {
            "name": name,
            "tokens": tokens,
            "requests": requests,
            "share": round(tokens / total_tokens, 4) if total_tokens else 0,
        }
        for name, (tokens, requests) in ranked[:MAX_MODELS]
    ]
    rest = ranked[MAX_MODELS:]
    if rest:
        tokens = sum(t for _, (t, _) in rest)
        models.append(
            {
                "name": "other",
                "tokens": tokens,
                "requests": sum(r for _, (_, r) in rest),
                "share": round(tokens / total_tokens, 4) if total_tokens else 0,
            }
        )

    latest = max(events, key=lambda event: event.at, default=None)
    return {
        "schemaVersion": CONTRACT_VERSION,
        "providerId": provider_id,
        "available": available,
        "generatedAt": isoformat_utc(now),
        "currentModel": None
        if latest is None
        else {"name": latest.model, "effort": latest.effort, "lastSeen": isoformat_utc(latest.at)},
        "hourly": [
            {"start": isoformat_utc(start + timedelta(hours=index)), "tokens": tokens}
            for index, tokens in enumerate(hourly)
        ],
        "totals": {
            "last24hTokens": sum(hourly),
            "last24hRequests": requests_24h,
            "last7dTokens": total_tokens,
            "last7dRequests": sum(requests for _, (_, requests) in ranked),
        },
        "models": models,
    }


def collect(provider_id: str, now: datetime | None = None) -> dict[str, Any]:
    now = now or utc_now()
    if provider_id not in COLLECTORS:
        labels = {"antigravity": "Antigravity", "cursor": "Cursor"}
        return {
            "schemaVersion": CONTRACT_VERSION,
            "providerId": provider_id,
            "available": False,
            "generatedAt": isoformat_utc(now),
            "currentModel": None,
            "hourly": [{"start": isoformat_utc(now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=23-index)), "tokens": 0} for index in range(HOURS)],
            "totals": {"last24hTokens": 0, "last24hRequests": 0, "last7dTokens": 0, "last7dRequests": 0},
            "models": [],
            "message": f"{labels[provider_id]} quota is shown above; local token totals are not available.",
        }
    root_for, collector = COLLECTORS[provider_id]
    root = root_for()
    since = now - timedelta(days=MODEL_WINDOW_DAYS)
    return build_insights(provider_id, collector(root, since), now, available=root.is_dir())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    args = parser.parse_args(argv)
    json.dump(collect(args.provider), sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

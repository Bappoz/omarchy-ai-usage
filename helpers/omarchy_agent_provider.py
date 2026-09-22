#!/usr/bin/env python3
"""Normalize an omarchy.agents usage record into the notch contract."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
MAX_RECORD_BYTES = 1_048_576
PROVIDERS = {"claude": "Claude", "codex": "Codex"}
IDENTIFIER_PART = re.compile(r"[^a-z0-9._-]+")
AUTH_STATUSES = {"waiting for auth", "sign-in expired"}


class ProviderError(Exception):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.safe_message = message


def usage_dir() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    root = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return root / "omarchy" / "agents" / "usage"


def provider_path(provider_id: str) -> Path:
    return usage_dir() / f"{provider_id}.json"


def empty_snapshot(provider_id: str, status: str, message: str) -> dict[str, Any]:
    return {
        "schemaVersion": CONTRACT_VERSION,
        "providerId": provider_id,
        "displayName": PROVIDERS[provider_id],
        "account": None,
        "status": status,
        "lastUpdated": None,
        "stale": False,
        "headlineWindowId": None,
        "windows": [],
        "message": message,
    }


def read_record(path: Path, provider_id: str) -> Mapping[str, Any]:
    try:
        if path.is_symlink() or not path.is_file():
            raise ProviderError("UNAVAILABLE", f"Enable omarchy.agents to show {PROVIDERS[provider_id]} usage.")
        if path.stat().st_size > MAX_RECORD_BYTES:
            raise ProviderError("ERROR", "The Omarchy agent usage record is too large.")
        record = json.loads(path.read_bytes())
    except ProviderError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProviderError("ERROR", "The Omarchy agent usage record could not be read.") from exc
    if not isinstance(record, Mapping):
        raise ProviderError("ERROR", "The Omarchy agent usage record is invalid.")
    if record.get("schemaVersion") != 1 or record.get("id") != provider_id:
        raise ProviderError("ERROR", "The Omarchy agent usage record is invalid.")
    return record


def safe_text(value: object, maximum: int = 200) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:maximum]


def slug(value: object, fallback: str) -> str:
    candidate = IDENTIFIER_PART.sub("-", str(value).strip().lower()).strip("-._")
    return (candidate or fallback)[:48]


def parse_time(value: object) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ProviderError("ERROR", "The Omarchy agent usage record has an invalid timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProviderError("ERROR", "The Omarchy agent usage record has an invalid timestamp.") from exc
    if parsed.tzinfo is None:
        raise ProviderError("ERROR", "The Omarchy agent usage record has an invalid timestamp.")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def percent(value: object) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderError("ERROR", "The Omarchy agent usage record has invalid quota data.")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ProviderError("ERROR", "The Omarchy agent usage record has invalid quota data.")
    scaled = round(number * 100, 4)
    return int(scaled) if scaled.is_integer() else scaled


def duration_minutes(label: str) -> int | None:
    lowered = label.lower()
    hours = re.search(r"\b(\d+)\s*[- ]?h(?:our)?\b", lowered)
    if hours:
        return int(hours.group(1)) * 60
    days = re.search(r"\b(\d+)\s*[- ]?day\b", lowered)
    if days:
        return int(days.group(1)) * 1440
    if "weekly" in lowered or "week" in lowered:
        return 10080
    if "monthly" in lowered or "month" in lowered:
        return 43200
    return None


def normalize_record(record: Mapping[str, Any], provider_id: str) -> dict[str, Any]:
    status_text = safe_text(record.get("usageStatusText"), 80).lower()
    windows: list[dict[str, Any]] = []
    seen: set[str] = set()
    limits = record.get("limits")
    if not isinstance(limits, list):
        raise ProviderError("ERROR", "The Omarchy agent usage record has invalid quota data.")

    for index, raw in enumerate(limits[:32]):
        if not isinstance(raw, Mapping):
            raise ProviderError("ERROR", "The Omarchy agent usage record has invalid quota data.")
        label = safe_text(raw.get("label"), 80) or f"Limit {index + 1}"
        window_id = slug(raw.get("title") or label, f"limit-{index + 1}")
        if window_id in seen:
            window_id = f"{window_id[:40]}-{index + 1}"
        seen.add(window_id)
        used = percent(raw.get("percent"))
        windows.append(
            {
                "id": window_id,
                "name": safe_text(raw.get("title"), 80) or label,
                "usedPercent": used,
                "remainingPercent": round(100 - used, 4),
                "resetAt": parse_time(raw.get("resetsAt")),
                "durationMinutes": duration_minutes(label),
                "fidelity": "OFFICIAL",
            }
        )

    if status_text in AUTH_STATUSES or record.get("ready") is not True:
        status = "NEEDS_AUTH"
    elif not windows:
        status = "UNAVAILABLE"
    elif any(float(window["usedPercent"]) >= 100 for window in windows):
        status = "RATE_LIMITED"
    else:
        status = "ACTIVE"

    headline = max(windows, key=lambda item: float(item["usedPercent"])) if windows else None
    plan = safe_text(record.get("tierLabel"), 80) or None
    messages = {
        "NEEDS_AUTH": f"Sign in through {PROVIDERS[provider_id]} and let omarchy.agents refresh usage.",
        "UNAVAILABLE": f"omarchy.agents has no {PROVIDERS[provider_id]} quota data yet.",
        "RATE_LIMITED": f"{PROVIDERS[provider_id]} quota is currently exhausted.",
    }
    return {
        "schemaVersion": CONTRACT_VERSION,
        "providerId": provider_id,
        "displayName": PROVIDERS[provider_id],
        "account": {"label": None, "plan": plan} if plan else None,
        "status": status,
        "lastUpdated": parse_time(record.get("updatedAt")),
        "stale": False,
        "headlineWindowId": headline["id"] if headline else None,
        "windows": windows,
        "message": messages.get(status),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    parser.add_argument("--record-path", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        record = read_record(args.record_path or provider_path(args.provider), args.provider)
        snapshot = normalize_record(record, args.provider)
    except ProviderError as exc:
        snapshot = empty_snapshot(args.provider, exc.status, exc.safe_message)
    json.dump(snapshot, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

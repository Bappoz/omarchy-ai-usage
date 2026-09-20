#!/usr/bin/env python3
"""Normalize Omarchy's Claude Code collector into the plugin contract."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROVIDER_ID = "claude"
DISPLAY_NAME = "Claude"
CONTRACT_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_OUTPUT_BYTES = 1_048_576
DEFAULT_MAX_CACHE_AGE_SECONDS = 7 * 24 * 60 * 60
DEFAULT_COLLECTOR = "/usr/share/omarchy/bin/omarchy-agent-usage-claude"
DEFAULT_UPDATER = "/usr/share/omarchy/bin/omarchy-agent-usage-update"
IDENTIFIER_PART = re.compile(r"[^a-z0-9._-]+")
AUTH_STATUSES = {"waiting for auth", "sign-in expired"}


class ProviderError(Exception):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.safe_message = message


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def default_cache_path() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    root = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return root / "omarchy-ai-usage" / "claude-last-good.json"


def default_shared_usage_path() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    root = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return root / "omarchy" / "agents" / "usage" / "claude.json"


def build_collector_command(collector: str) -> list[str]:
    return [collector, "--limits-only"]


def build_updater_command(updater: str) -> list[str]:
    return [updater, "--limits-only", PROVIDER_ID]


def _parse_payload(raw: bytes) -> Mapping[str, Any]:
    if len(raw) > DEFAULT_MAX_OUTPUT_BYTES:
        raise ProviderError("ERROR", "Claude returned an unreadable response.")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError("ERROR", "Claude returned an unreadable response.") from exc
    if not isinstance(payload, Mapping):
        raise ProviderError("ERROR", "Claude returned an unreadable response.")
    return payload


def collect_claude(
    command: Sequence[str],
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> Mapping[str, Any]:
    try:
        completed = subprocess.run(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise ProviderError("UNAVAILABLE", "Claude usage support is not available in this Omarchy version.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProviderError("ERROR", "Claude did not respond before the refresh deadline.") from exc
    except OSError as exc:
        raise ProviderError("UNAVAILABLE", "Claude usage could not be started.") from exc

    if len(completed.stdout) > max_output_bytes:
        raise ProviderError("ERROR", "Claude returned an unreadable response.")
    if completed.returncode != 0:
        raise ProviderError("ERROR", "Claude usage could not be refreshed.")
    return _parse_payload(completed.stdout)


def collect_shared_claude(
    command: Sequence[str],
    shared_usage_path: Path,
    *,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
) -> Mapping[str, Any]:
    """Refresh and read Omarchy's shared Claude record.

    The official updater owns the on-disk record contract and performs an
    atomic replacement. Keeping this work in the provider runner means the
    shared state remains fresh even when the native agents widget is disabled.
    """
    try:
        completed = subprocess.run(
            list(command),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except FileNotFoundError as exc:
        raise ProviderError("UNAVAILABLE", "Claude usage support is not available in this Omarchy version.") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProviderError("ERROR", "Claude did not respond before the refresh deadline.") from exc
    except OSError as exc:
        raise ProviderError("UNAVAILABLE", "Claude usage could not be started.") from exc

    if completed.returncode != 0:
        raise ProviderError("ERROR", "Claude usage could not be refreshed.")
    try:
        if shared_usage_path.is_symlink() or not shared_usage_path.is_file():
            raise ProviderError("ERROR", "Claude usage could not be refreshed.")
        if shared_usage_path.stat().st_size > max_output_bytes:
            raise ProviderError("ERROR", "Claude returned an unreadable response.")
        raw = shared_usage_path.read_bytes()
    except ProviderError:
        raise
    except OSError as exc:
        raise ProviderError("ERROR", "Claude usage could not be refreshed.") from exc
    return _parse_payload(raw)


def _empty_snapshot(status: str, message: str) -> dict[str, Any]:
    return {
        "schemaVersion": CONTRACT_VERSION,
        "providerId": PROVIDER_ID,
        "displayName": DISPLAY_NAME,
        "account": None,
        "status": status,
        "lastUpdated": None,
        "stale": False,
        "headlineWindowId": None,
        "windows": [],
        "message": message,
    }


def _safe_label(value: object, maximum: int = 80) -> str | None:
    if not isinstance(value, str):
        return None
    label = " ".join(value.split())[:maximum]
    return label or None


def _slug(value: object, fallback: str) -> str:
    slug = IDENTIFIER_PART.sub("-", str(value).strip().lower()).strip("-._")
    return (slug or fallback)[:48]


def _percent(value: object) -> float | int:
    """Convert Omarchy's Claude 0..1 utilization fraction to 0..100."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderError("ERROR", "Claude returned invalid quota data.")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ProviderError("ERROR", "Claude returned invalid quota data.")
    number = round(number * 100, 4)
    return int(number) if number.is_integer() else round(number, 4)


def _reset_at(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderError("ERROR", "Claude returned invalid quota data.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProviderError("ERROR", "Claude returned invalid quota data.") from exc
    if parsed.tzinfo is None:
        raise ProviderError("ERROR", "Claude returned invalid quota data.")
    return isoformat_utc(parsed)


def _duration_minutes(label: str) -> int | None:
    match = re.search(r"\b(\d+)\s*[- ]?hour\b", label, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 60
    match = re.search(r"\b(\d+)\s*[- ]?day\b", label, re.IGNORECASE)
    if match:
        return int(match.group(1)) * 1440
    if re.search(r"\bweekly\b", label, re.IGNORECASE):
        return 10080
    return None


def normalize_claude_payload(payload: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    provider_id = payload.get("id")
    if provider_id is not None and provider_id != PROVIDER_ID:
        raise ProviderError("ERROR", "Claude returned invalid provider data.")

    usage_status = _safe_label(payload.get("usageStatusText"))
    status_key = (usage_status or "").lower()
    raw_limits = payload.get("limits")
    if raw_limits is None:
        raw_limits = []
    if not isinstance(raw_limits, list):
        raise ProviderError("ERROR", "Claude returned invalid quota data.")

    windows: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    for index, raw_limit in enumerate(raw_limits):
        if not isinstance(raw_limit, Mapping):
            raise ProviderError("ERROR", "Claude returned invalid quota data.")
        label = _safe_label(raw_limit.get("label") or raw_limit.get("title"))
        if label is None:
            raise ProviderError("ERROR", "Claude returned invalid quota data.")
        used = _percent(raw_limit.get("percent"))
        base_id = _slug(label, f"limit-{index + 1}")
        window_id = base_id
        suffix = 2
        while window_id in used_ids:
            window_id = f"{base_id}-{suffix}"
            suffix += 1
        used_ids.add(window_id)
        remaining = round(100 - float(used), 4)
        if remaining.is_integer():
            remaining = int(remaining)
        windows.append(
            {
                "id": window_id,
                "name": label,
                "usedPercent": used,
                "remainingPercent": remaining,
                "resetAt": _reset_at(raw_limit.get("resetsAt")),
                "durationMinutes": _duration_minutes(label),
                "fidelity": "OFFICIAL",
            }
        )

    if status_key in AUTH_STATUSES:
        return _empty_snapshot("NEEDS_AUTH", "Sign in to Claude Code to read usage limits.")

    plan = _safe_label(payload.get("tierLabel"))
    if not windows:
        snapshot = _empty_snapshot("UNAVAILABLE", "Claude limits are unavailable for this account.")
        if plan:
            snapshot["account"] = {"label": None, "plan": plan}
        return snapshot

    stale = bool(usage_status) or payload.get("retryAdvised") is True
    return {
        "schemaVersion": CONTRACT_VERSION,
        "providerId": PROVIDER_ID,
        "displayName": DISPLAY_NAME,
        "account": {"label": None, "plan": plan} if plan else None,
        "status": "STALE" if stale else "ACTIVE",
        "lastUpdated": isoformat_utc(now),
        "stale": stale,
        "headlineWindowId": windows[0]["id"],
        "windows": windows,
        "message": "Claude is temporarily showing cached usage." if stale else None,
    }


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def _valid_cached_snapshot(snapshot: object) -> bool:
    if not isinstance(snapshot, Mapping):
        return False
    if snapshot.get("schemaVersion") != 1 or snapshot.get("providerId") != PROVIDER_ID:
        return False
    if snapshot.get("displayName") != DISPLAY_NAME or snapshot.get("status") != "ACTIVE":
        return False
    if snapshot.get("stale") is not False or _parse_time(snapshot.get("lastUpdated")) is None:
        return False
    windows = snapshot.get("windows")
    if not isinstance(windows, list) or not 1 <= len(windows) <= 32:
        return False
    ids: set[str] = set()
    for window in windows:
        if not isinstance(window, Mapping):
            return False
        window_id = window.get("id")
        if not isinstance(window_id, str) or not window_id or window_id in ids:
            return False
        ids.add(window_id)
        for field in ("usedPercent", "remainingPercent"):
            value = window.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 100:
                return False
    return snapshot.get("headlineWindowId") in ids


def write_last_good(path: Path, snapshot: Mapping[str, Any]) -> None:
    if not _valid_cached_snapshot(snapshot):
        raise ValueError("only successful Claude snapshots may be cached")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = json.dumps({"cacheVersion": 1, "snapshot": snapshot}, separators=(",", ":")) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def read_last_good(path: Path, now: datetime, max_age_seconds: int) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > DEFAULT_MAX_OUTPUT_BYTES:
            return None
        envelope = json.loads(path.read_text(encoding="utf-8"))
        snapshot = envelope.get("snapshot") if isinstance(envelope, dict) else None
        if envelope.get("cacheVersion") != 1 or not _valid_cached_snapshot(snapshot):
            return None
        updated = _parse_time(snapshot.get("lastUpdated"))
        assert updated is not None
        age = (now.astimezone(timezone.utc) - updated).total_seconds()
        return copy.deepcopy(dict(snapshot)) if 0 <= age <= max_age_seconds else None
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return None


def refresh_provider(
    fetch: Callable[[], Mapping[str, Any]],
    *,
    cache_path: Path | None,
    now: datetime | None = None,
    max_cache_age_seconds: int = DEFAULT_MAX_CACHE_AGE_SECONDS,
) -> dict[str, Any]:
    current_time = now or utc_now()
    try:
        snapshot = normalize_claude_payload(fetch(), current_time)
    except ProviderError as exc:
        snapshot = _empty_snapshot(exc.status, exc.safe_message)
    except Exception:  # noqa: BLE001
        snapshot = _empty_snapshot("ERROR", "Claude usage could not be refreshed.")

    if snapshot["status"] == "ACTIVE":
        if cache_path is not None:
            try:
                write_last_good(cache_path, snapshot)
            except (OSError, ValueError):
                pass
        return snapshot
    if snapshot["status"] in {"ERROR", "UNAVAILABLE"} and cache_path is not None:
        cached = read_last_good(cache_path, current_time, max_cache_age_seconds)
        if cached is not None:
            cached["status"] = "STALE"
            cached["stale"] = True
            cached["message"] = "Showing the last successful refresh; current Claude data is unavailable."
            return cached
    return snapshot


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collector", help="Explicit Omarchy Claude collector path")
    parser.add_argument("--updater", help="Explicit Omarchy usage updater path")
    parser.add_argument("--shared-usage-path", type=Path, default=default_shared_usage_path())
    parser.add_argument("--cache-path", type=Path, default=default_cache_path())
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-cache-age", type=int, default=DEFAULT_MAX_CACHE_AGE_SECONDS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0 or args.max_cache_age < 0:
        print("timeout must be positive and max-cache-age cannot be negative", file=sys.stderr)
        return 2
    if args.updater:
        updater = args.updater
        collector = None
    elif args.collector:
        updater = None
        collector = args.collector
    else:
        updater = DEFAULT_UPDATER if Path(DEFAULT_UPDATER).is_file() else shutil.which("omarchy-agent-usage-update")
        collector = DEFAULT_COLLECTOR if Path(DEFAULT_COLLECTOR).is_file() else shutil.which("omarchy-agent-usage-claude")
    cache_path = None if args.no_cache else args.cache_path
    if updater:
        fetch = lambda: collect_shared_claude(
            build_updater_command(str(updater)),
            args.shared_usage_path,
            timeout_seconds=args.timeout,
        )
    elif collector:
        fetch = lambda: collect_claude(build_collector_command(str(collector)), timeout_seconds=args.timeout)
    else:
        fetch = lambda: (_ for _ in ()).throw(ProviderError("UNAVAILABLE", "Claude usage support is not available in this Omarchy version."))
    snapshot = refresh_provider(fetch, cache_path=cache_path, max_cache_age_seconds=args.max_cache_age)
    print(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

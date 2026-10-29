#!/usr/bin/env python3
"""Expose Orca's supported local quota snapshots to Omarchy AI Usage.

This adapter reads only the machine-readable ``orca account list --json``
response. It does not inspect credentials or make provider network requests.
Only Antigravity and Cursor quota pools are exposed. This module does not add a
separate Gemini provider card.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
PROVIDERS = {"antigravity": "Antigravity", "cursor": "Cursor"}
MAX_OUTPUT_BYTES = 1_048_576
TIMEOUT_SECONDS = 12
CACHE_TTL_SECONDS = 20
IDENTIFIER_PART = re.compile(r"[^a-z0-9._-]+")
CONTROL = re.compile(r"[\x00-\x1f\x7f]+")


def _state_dir() -> Path:
    root = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(root) / "omarchy-ai-usage"


def _empty(provider_id: str, status: str, message: str) -> dict[str, Any]:
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


def _safe_label(value: object, maximum: int = 80) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(CONTROL.sub(" ", value).split())[:maximum]
    return text or None


def _slug(value: object, fallback: str) -> str:
    text = IDENTIFIER_PART.sub("-", str(value).strip().lower()).strip("-._")
    return (text or fallback)[:48]


def _timestamp(value: object) -> str | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            return None
        # Orca's rate-limit snapshots use Unix milliseconds.
        if number > 10_000_000_000:
            number /= 1000
        try:
            return datetime.fromtimestamp(number, UTC).isoformat().replace("+00:00", "Z")
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return None


def _percent(value: object) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 100:
        return None
    return int(number) if number.is_integer() else round(number, 4)


def _windows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_buckets = record.get("buckets")
    buckets: list[Mapping[str, Any]] = []
    if isinstance(raw_buckets, list):
        buckets = [item for item in raw_buckets[:32] if isinstance(item, Mapping)]
    if not buckets:
        for name in ("session", "weekly", "daily", "monthly"):
            item = record.get(name)
            if isinstance(item, Mapping):
                buckets.append({**item, "windowName": item.get("windowName") or name})

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, bucket in enumerate(buckets):
        used = _percent(bucket.get("usedPercent", bucket.get("percent")))
        if used is None:
            continue
        group = _safe_label(bucket.get("group"), 60)
        title = _safe_label(bucket.get("name") or bucket.get("windowName"), 60)
        window_name = _safe_label(bucket.get("windowName"), 60)
        label = " · ".join(part for part in (group or title, window_name if group and window_name != group else None) if part)
        label = label or title or f"Limit {index + 1}"
        base = _slug(bucket.get("group") or bucket.get("name") or label, f"limit-{index + 1}")
        window_id = base
        suffix = 2
        while window_id in seen:
            window_id = f"{base[:40]}-{suffix}"
            suffix += 1
        seen.add(window_id)
        duration = bucket.get("windowMinutes", bucket.get("durationMinutes"))
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            duration = None
        else:
            duration = min(525600, int(duration))
        reset_at = _timestamp(bucket.get("resetsAt", bucket.get("resetAt")))
        result.append(
            {
                "id": window_id,
                "name": label,
                "usedPercent": used,
                "remainingPercent": round(100 - float(used), 4),
                "resetAt": reset_at,
                "durationMinutes": duration,
                "fidelity": "OFFICIAL",
            }
        )
    return result


def _headline(windows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if not windows:
        return None
    known = [item for item in windows if isinstance(item.get("durationMinutes"), int)]
    return min(known, key=lambda item: int(item["durationMinutes"])) if known else windows[0]


def _from_record(provider_id: str, record: object, *, display_name: str | None = None) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        return _empty(provider_id, "UNAVAILABLE", f"No {PROVIDERS[provider_id]} quota data is available from Orca.")

    windows = _windows(record)
    updated = _timestamp(record.get("updatedAt"))
    status_text = str(record.get("status") or "").lower()
    error = str(record.get("error") or "").lower()
    plan = _safe_label(record.get("planType"), 60)

    if windows and status_text == "ok":
        primary = _headline(windows)
        status = "RATE_LIMITED" if any(float(item["usedPercent"]) >= 100 for item in windows) else "ACTIVE"
        return {
            "schemaVersion": CONTRACT_VERSION,
            "providerId": provider_id,
            "displayName": display_name or PROVIDERS[provider_id],
            "account": {"label": None, "plan": plan.title() if plan else None},
            "status": status,
            "lastUpdated": updated,
            "stale": False,
            "headlineWindowId": primary["id"] if primary else None,
            "windows": windows,
            "message": None,
        }

    auth_terms = ("not signed in", "sign in", "unauthenticated", "missing-credentials", "not authenticated")
    if status_text in {"needs_auth", "unauthenticated"} or any(term in error for term in auth_terms):
        return _empty(provider_id, "NEEDS_AUTH", f"Sign in to {display_name or PROVIDERS[provider_id]} to show its quota.")
    return _empty(provider_id, "UNAVAILABLE", f"Orca has no live {display_name or PROVIDERS[provider_id]} quota data.")


def _desktop_appimage() -> list[str] | None:
    candidates = (
        Path.home() / ".local/share/applications/orca-ide.desktop",
        Path.home() / ".local/share/applications/orca.desktop",
        Path("/usr/share/applications/orca-ide.desktop"),
    )
    for desktop in candidates:
        try:
            text = desktop.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if not line.startswith("Exec="):
                continue
            try:
                parts = shlex.split(line[5:])
            except ValueError:
                continue
            parts = [part for part in parts if not re.fullmatch(r"%[fFuUdDnNickvm]", part)]
            if parts and Path(parts[0]).is_file() and os.access(parts[0], os.X_OK):
                return parts
    return None


def _orca_commands() -> list[list[str]]:
    commands: list[list[str]] = []
    installed = shutil.which("orca-ide")
    if installed:
        commands.append([installed])
    # The running AppImage registers this checked, app-scoped CLI shim. Never
    # fall back to bare `orca`, which is the GNOME screen reader on Linux.
    shim = Path.home() / ".config/orca/linux-orca-cli-shim/orca"
    if shim.is_file() and os.access(shim, os.X_OK):
        commands.append([str(shim)])
    appimage = _desktop_appimage()
    if appimage:
        commands.append(appimage)
    return commands


def _read_orca_rate_limits() -> Mapping[str, Any]:
    for command in _orca_commands():
        try:
            completed = subprocess.run(
                [*command, "account", "list", "--json"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=TIMEOUT_SECONDS,
                check=False,
                shell=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if completed.returncode != 0 or len(completed.stdout) > MAX_OUTPUT_BYTES:
            continue
        try:
            payload = json.loads(completed.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(payload, Mapping):
            continue
        result = payload.get("result")
        limits = result.get("rateLimits") if isinstance(result, Mapping) else None
        if isinstance(limits, Mapping):
            return limits
    raise RuntimeError("Orca CLI is unavailable or did not return quota data.")


def _build_snapshots(rate_limits: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "antigravity": _from_record("antigravity", rate_limits.get("antigravity")),
        "cursor": _from_record("cursor", rate_limits.get("cursor")),
    }


def _cache_file() -> Path:
    return _state_dir() / "orca-provider-snapshots.json"


def _read_cache() -> dict[str, dict[str, Any]] | None:
    path = _cache_file()
    try:
        if path.is_symlink() or not path.is_file() or time.time() - path.stat().st_mtime > CACHE_TTL_SECONDS:
            return None
        if path.stat().st_size > MAX_OUTPUT_BYTES:
            return None
        data = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, Mapping) or not isinstance(data.get("snapshots"), Mapping):
        return None
    snapshots = data["snapshots"]
    return {key: value for key, value in snapshots.items() if key in PROVIDERS and isinstance(value, dict)}


def _write_cache(snapshots: Mapping[str, Mapping[str, Any]]) -> None:
    directory = _state_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    fd, name = tempfile.mkstemp(prefix=".orca-usage-", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"snapshots": snapshots}, stream, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, _cache_file())
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def collect(provider_id: str) -> dict[str, Any]:
    cached = _read_cache()
    if cached and provider_id in cached:
        return cached[provider_id]

    directory = _state_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = directory / "orca-provider.lock"
    if lock_path.is_symlink():
        raise RuntimeError("Unsafe Orca usage cache path.")
    with lock_path.open("a", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        cached = _read_cache()
        if cached and provider_id in cached:
            return cached[provider_id]
        snapshots = _build_snapshots(_read_orca_rate_limits())
        _write_cache(snapshots)
        return snapshots[provider_id]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=sorted(PROVIDERS), required=True)
    args = parser.parse_args(argv)
    try:
        snapshot = collect(args.provider)
    # Keep unexpected runtime failures behind the provider-neutral JSON boundary.
    except Exception:  # noqa: BLE001
        snapshot = _empty(args.provider, "UNAVAILABLE", f"Orca could not provide {PROVIDERS[args.provider]} quota data.")
    json.dump(snapshot, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Standalone Antigravity quota provider — works without Orca open.

Resolution order (most direct and honest first):
  1. Local Antigravity language server / ``agy --hub`` loopback RPC
     (discovered via ``/proc`` for the current user; POST to
     ``https://127.0.0.1:<port>/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary``
     with ``x-codeium-csrf-token`` and ``{"forceRefresh":true}``).
  2. Official standalone ``agy`` CLI (``agy --print /usage`` in a bounded PTY
     with ``AGY_CLI_DISABLE_AUTO_UPDATE=true``), cached for 5 minutes.
  3. Optional Orca CLI fallback if Orca happens to be running and direct
     sources did not answer.
  4. Last-known-good private cache marked ``STALE`` on transient failures.

Never logs credentials or tokens; cache files are private (0600).
"""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import pty
import re
import select
import shutil
import signal
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

CONTRACT_VERSION = 1
PROVIDER_ID = "antigravity"
DISPLAY_NAME = "Antigravity"
LS_RPC_PATH = "/exa.language_server_pb.LanguageServerService/RetrieveUserQuotaSummary"
CSRF_HEADER = "x-codeium-csrf-token"
CLI_CACHE_TTL_SECONDS = 300
STALE_CACHE_MAX_AGE_SECONDS = 7 * 86400
CLI_TIMEOUT_SECONDS = 15
BRIDGE_TIMEOUT_SECONDS = 8
MAX_OUTPUT_BYTES = 1_048_576
ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\)|[@-Z\\-_])")
IDENTIFIER_PART = re.compile(r"[^a-z0-9._-]+")
CONTROL = re.compile(r"[\x00-\x1f\x7f]+")


def _cache_dir() -> Path:
    root = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(root) / "omarchy-ai-usage"


def _cache_file() -> Path:
    return _cache_dir() / "antigravity-snapshot.json"


def _empty(status: str, message: str) -> dict[str, Any]:
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


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_label(value: object, maximum: int = 80) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(CONTROL.sub(" ", value).split())[:maximum]
    return text or None


def _slug(value: object, fallback: str) -> str:
    text = IDENTIFIER_PART.sub("-", str(value).strip().lower()).strip("-._")
    return (text or fallback)[:48]


def _parse_iso(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _duration_from_label(label: str) -> int | None:
    lower = label.lower()
    if "five hour" in lower or "5h" in lower or "5-hour" in lower:
        return 300
    if "weekly" in lower or "7d" in lower or "week" in lower:
        return 10080
    if "daily" in lower or "24h" in lower or "day" in lower:
        return 1440
    if "monthly" in lower or "month" in lower:
        return 43200
    return None


def _headline(windows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    if not windows:
        return None
    known = [item for item in windows if isinstance(item.get("durationMinutes"), int)]
    return min(known, key=lambda item: int(item["durationMinutes"])) if known else windows[0]


def _build_snapshot(
    windows: list[dict[str, Any]],
    *,
    plan: str | None = None,
    updated: str | None = None,
) -> dict[str, Any]:
    if not windows:
        return _empty("UNAVAILABLE", "No Antigravity quota windows were reported.")
    primary = _headline(windows)
    status = "RATE_LIMITED" if any(float(item["usedPercent"]) >= 100 for item in windows) else "ACTIVE"
    return {
        "schemaVersion": CONTRACT_VERSION,
        "providerId": PROVIDER_ID,
        "displayName": DISPLAY_NAME,
        "account": {"label": None, "plan": plan} if plan else None,
        "status": status,
        "lastUpdated": updated or _now_iso(),
        "stale": False,
        "headlineWindowId": primary["id"] if primary else None,
        "windows": windows,
        "message": None,
    }


# ---------------------------------------------------------------------------
# 1. Local language server / agy --hub bridge (via /proc, zero external deps)
# ---------------------------------------------------------------------------

def _flag_value(args: Sequence[str], flag: str) -> str | None:
    for idx, part in enumerate(args):
        if part == flag and idx + 1 < len(args):
            return args[idx + 1].strip('"')
        if part.startswith(flag + "="):
            return part.split("=", 1)[1].strip('"')
    return None


def _listening_ports_for_pid(pid: int, proc: Path = Path("/proc")) -> list[int]:
    """Find loopback/wildcard TCP listening ports owned by ``pid`` using /proc."""
    inodes: set[str] = set()
    fd_dir = proc / str(pid) / "fd"
    try:
        for entry in fd_dir.iterdir():
            try:
                target = os.readlink(entry)
            except OSError:
                continue
            if target.startswith("socket:[") and target.endswith("]"):
                inodes.add(target[8:-1])
    except OSError:
        return []
    if not inodes:
        return []

    ports: set[int] = set()
    for table_name in ("tcp", "tcp6"):
        table_path = proc / "net" / table_name
        try:
            lines = table_path.read_text(encoding="ascii", errors="ignore").splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            cols = line.split()
            if len(cols) < 10:
                continue
            # 0A == TCP_LISTEN
            if cols[3] != "0A" or cols[9] not in inodes:
                continue
            local_addr = cols[1]
            if ":" not in local_addr:
                continue
            try:
                port = int(local_addr.rsplit(":", 1)[1], 16)
            except ValueError:
                continue
            if 1 <= port <= 65535:
                ports.add(port)
    return sorted(ports)


def discover_bridge_endpoints(proc: Path = Path("/proc")) -> list[tuple[list[int], str]]:
    """Find running same-user Antigravity language_server / agy --hub processes."""
    uid = os.getuid()
    candidates: list[tuple[int, int, str]] = []  # (priority, pid, csrf)
    try:
        entries = list(proc.iterdir())
    except OSError:
        return []
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            raw = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if not raw or b"--csrf_token" not in raw:
            continue
        args = [part.decode("utf-8", errors="ignore") for part in raw.split(b"\x00") if part]
        joined = " ".join(args)
        is_ls = "language_server" in joined
        is_agy = any(Path(a).name in {"agy", "antigravity"} for a in args[:2]) or "--hub" in args
        if not (is_ls or is_agy):
            continue
        csrf = _flag_value(args, "--csrf_token")
        if not csrf:
            continue
        candidates.append((0 if is_ls else 1, int(entry.name), csrf))

    candidates.sort(key=lambda item: (item[0], item[1]))
    endpoints: list[tuple[list[int], str]] = []
    for _, pid, csrf in candidates:
        ports = _listening_ports_for_pid(pid, proc)
        if ports:
            endpoints.append((ports, csrf))
    return endpoints


def windows_from_bridge(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Parse ``RetrieveUserQuotaSummary`` JSON into normalized quota windows."""
    response = payload.get("response")
    groups = response.get("groups") if isinstance(response, Mapping) else payload.get("groups")
    if not isinstance(groups, list):
        return []

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for g_idx, group in enumerate(groups[:16]):
        if not isinstance(group, Mapping):
            continue
        gname = _safe_label(group.get("displayName"), 60)
        buckets = group.get("buckets")
        if not isinstance(buckets, list):
            continue
        for b_idx, bucket in enumerate(buckets[:16]):
            if not isinstance(bucket, Mapping):
                continue
            rem = bucket.get("remainingFraction")
            if isinstance(rem, bool) or not isinstance(rem, (int, float)):
                continue
            rem_f = float(rem)
            if not math.isfinite(rem_f) or not 0.0 <= rem_f <= 1.0:
                continue
            used = round((1.0 - rem_f) * 100.0, 4)
            used_val: int | float = int(used) if used.is_integer() else used
            bname = _safe_label(bucket.get("displayName"), 60)
            raw_id = _safe_label(bucket.get("bucketId"), 60) or gname or bname or f"limit-{g_idx + 1}-{b_idx + 1}"
            label = " · ".join(
                part for part in (gname, bname if bname and bname != gname else None) if part
            ) or bname or raw_id
            base = _slug(raw_id, f"limit-{len(result) + 1}")
            window_id = base
            suffix = 2
            while window_id in seen:
                window_id = f"{base[:40]}-{suffix}"
                suffix += 1
            seen.add(window_id)
            duration = _duration_from_label(f"{raw_id} {label}")
            reset_at = _parse_iso(bucket.get("resetTime"))
            result.append(
                {
                    "id": window_id,
                    "name": label,
                    "usedPercent": used_val,
                    "remainingPercent": round(100.0 - float(used_val), 4),
                    "resetAt": reset_at,
                    "durationMinutes": duration,
                    "fidelity": "OFFICIAL",
                }
            )
    return result


def fetch_from_bridge() -> dict[str, Any] | None:
    endpoints = discover_bridge_endpoints()
    if not endpoints:
        return None
    # Self-signed TLS is used ONLY for 127.0.0.1 loopback connections.
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    body = b'{"forceRefresh":true}'

    for ports, csrf in endpoints:
        for port in ports:
            url = f"https://127.0.0.1:{port}{LS_RPC_PATH}"
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    CSRF_HEADER: csrf,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=BRIDGE_TIMEOUT_SECONDS, context=ctx) as resp:
                    raw = resp.read(MAX_OUTPUT_BYTES + 1)
                    if len(raw) > MAX_OUTPUT_BYTES:
                        continue
                    data = json.loads(raw)
            except (OSError, urllib.error.URLError, ValueError):
                continue
            if not isinstance(data, Mapping):
                continue
            windows = windows_from_bridge(data)
            if windows:
                return _build_snapshot(windows)
    return None


# ---------------------------------------------------------------------------
# 2. Official standalone `agy` CLI (`agy --print /usage`)
# ---------------------------------------------------------------------------

def find_agy_binary() -> Path | None:
    candidates: list[Path] = []
    which = shutil.which("agy")
    if which:
        candidates.append(Path(which))
    home = Path.home()
    candidates.extend(
        [
            home / ".gemini" / "bin" / "agy",
            home / ".local" / "bin" / "agy",
            home / ".local" / "share" / "mise" / "shims" / "agy",
            home / ".local" / "share" / "mise" / "installs" / "antigravity-cli" / "latest" / "agy",
        ]
    )
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return path
    return None


def _sanitize_ansi(text: str) -> str:
    cleaned = ANSI_ESCAPE.sub("", text)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return cleaned


def _parse_cli_reset_time(text: str) -> str | None:
    raw = text.strip()
    if not raw:
        return None
    iso = _parse_iso(raw)
    if iso:
        return iso
    parts = raw.split()
    if len(parts) < 3:
        return None
    date_part = f"{parts[0]} {parts[1]}"
    zone = parts[2]
    try:
        naive = datetime.strptime(date_part, "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    if zone in {"UTC", "GMT", "Z"}:
        return naive.replace(tzinfo=UTC).isoformat().replace("+00:00", "Z")
    if re.fullmatch(r"[+-]\d{2}(?:\d{2})?", zone):
        sign = 1 if zone[0] == "+" else -1
        digits = zone[1:]
        hours = int(digits[:2])
        minutes = int(digits[2:]) if len(digits) == 4 else 0
        if hours > 14 or minutes > 59 or (hours == 14 and minutes != 0):
            return None
        tz = timezone(timedelta(seconds=sign * (hours * 3600 + minutes * 60)))
        return naive.replace(tzinfo=tz).astimezone(UTC).isoformat().replace("+00:00", "Z")
    if zone.isalpha():
        local_tz = datetime.now().astimezone().tzinfo or UTC
        return naive.replace(tzinfo=local_tz).astimezone(UTC).isoformat().replace("+00:00", "Z")
    return None


def parse_agy_cli_usage(text: str) -> list[dict[str, Any]]:
    """Parse ``agy --print /usage`` output into normalized quota windows."""
    clean = _sanitize_ansi(text)
    lines = clean.splitlines()
    has_header = any(line.strip() == "Quota:" for line in lines)
    has_rows = any(
        "\t" in line and ("Limit Remaining" in line or ("Argon" in line and "Limit" in line))
        for line in lines
    )
    if not has_header and not has_rows:
        return []

    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line in lines:
        if "Limit Remaining" not in line and not ("Argon" in line and "Limit" in line):
            continue
        if "%" not in line:
            continue
        left, reset_raw = line.rsplit("%", 1)
        left_parts = left.strip().rsplit(None, 1)
        if len(left_parts) != 2:
            continue
        raw_label, rem_str = left_parts
        try:
            remaining = float(rem_str)
        except ValueError:
            continue
        if not math.isfinite(remaining) or not 0.0 <= remaining <= 100.0:
            continue
        label = " ".join(raw_label.split())
        if label.endswith(" Remaining"):
            label = label[: -len(" Remaining")]
        short = (
            label.replace(" Models", "")
            .replace(" models", "")
            .replace(" and ", "/")
            .replace(" Weekly Limit", " · Weekly")
            .replace(" Five Hour Limit", " · 5h")
        )
        base = _slug(label, f"limit-{len(result) + 1}")
        window_id = base
        suffix = 2
        while window_id in seen:
            window_id = f"{base[:40]}-{suffix}"
            suffix += 1
        seen.add(window_id)
        used = round(max(0.0, min(100.0, 100.0 - remaining)), 4)
        used_val: int | float = int(used) if used.is_integer() else used
        result.append(
            {
                "id": window_id,
                "name": _safe_label(short, 60) or f"Limit {len(result) + 1}",
                "usedPercent": used_val,
                "remainingPercent": round(100.0 - float(used_val), 4),
                "resetAt": _parse_cli_reset_time(reset_raw),
                "durationMinutes": _duration_from_label(label),
                "fidelity": "OFFICIAL",
            }
        )
    return result


def fetch_from_agy_cli() -> dict[str, Any] | None:
    binary = find_agy_binary()
    if binary is None:
        return None
    env = {**os.environ, "AGY_CLI_DISABLE_AUTO_UPDATE": "true", "NO_COLOR": "1", "TERM": "dumb"}
    master_fd, slave_fd = pty.openpty()
    output = bytearray()
    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = subprocess.Popen(
            [str(binary), "--print", "/usage"],
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            env=env,
            start_new_session=True,
            close_fds=True,
        )
        os.close(slave_fd)
        slave_fd = -1
        deadline = time.monotonic() + CLI_TIMEOUT_SECONDS
        while time.monotonic() < deadline and len(output) < 65536:
            remaining = max(0.05, deadline - time.monotonic())
            ready, _, _ = select.select([master_fd], [], [], min(0.25, remaining))
            if ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output.extend(chunk)
            elif proc.poll() is not None:
                break
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except OSError:
                proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    proc.kill()
    except OSError:
        return None
    finally:
        if slave_fd >= 0:
            try:
                os.close(slave_fd)
            except OSError:
                pass
        try:
            os.close(master_fd)
        except OSError:
            pass

    text = output.decode("utf-8", errors="replace")
    lower = text.lower()
    if any(term in lower for term in ("not signed in", "sign in", "unauthenticated", "login required")):
        return _empty("NEEDS_AUTH", "Sign in to Antigravity to show its quota.")
    windows = parse_agy_cli_usage(text)
    if windows:
        return _build_snapshot(windows)
    return None


# ---------------------------------------------------------------------------
# 3. Private cache + optional Orca fallback
# ---------------------------------------------------------------------------

def _read_cache(max_age: float) -> dict[str, Any] | None:
    path = _cache_file()
    try:
        if path.is_symlink() or not path.is_file():
            return None
        stat = path.stat()
        age = time.time() - stat.st_mtime
        if age < -60 or age > max_age or stat.st_size > MAX_OUTPUT_BYTES:
            return None
        data = json.loads(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or data.get("providerId") != PROVIDER_ID:
        return None
    return data


def _write_cache(snapshot: Mapping[str, Any]) -> None:
    directory = _cache_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(directory, 0o700)
    fd, name = tempfile.mkstemp(prefix=".antigravity-usage-", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(snapshot, stream, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, _cache_file())
    except Exception:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def _try_orca_fallback() -> dict[str, Any] | None:
    try:
        from helpers import orca_usage_provider  # type: ignore[import-not-found]
    except ImportError:
        try:
            import orca_usage_provider  # type: ignore[import-not-found]
        except ImportError:
            return None
    try:
        snap = orca_usage_provider.collect(PROVIDER_ID)
    except Exception:  # noqa: BLE001
        return None
    if isinstance(snap, dict) and snap.get("status") in {"ACTIVE", "RATE_LIMITED"} and snap.get("windows"):
        return snap
    return None


def collect(*, force: bool = False) -> dict[str, Any]:
    # 1. Fast local language server bridge (live IDE / extension / agy --hub)
    live = fetch_from_bridge()
    if live and live.get("windows"):
        _write_cache(live)
        return live

    # 2. Fresh CLI cache avoids spawning the heavy `agy` binary too often.
    if not force:
        fresh = _read_cache(CLI_CACHE_TTL_SECONDS)
        if fresh and fresh.get("status") in {"ACTIVE", "RATE_LIMITED"} and fresh.get("windows"):
            return fresh

    # 3. Standalone `agy --print /usage` CLI (works with IDE & Orca closed)
    directory = _cache_dir()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = directory / "antigravity-provider.lock"
    if not lock_path.is_symlink():
        with lock_path.open("a", encoding="utf-8") as lock:
            os.chmod(lock_path, 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if not force:
                fresh = _read_cache(CLI_CACHE_TTL_SECONDS)
                if fresh and fresh.get("status") in {"ACTIVE", "RATE_LIMITED"} and fresh.get("windows"):
                    return fresh
            cli_snap = fetch_from_agy_cli()
            if cli_snap:
                if cli_snap.get("status") == "NEEDS_AUTH":
                    return cli_snap
                if cli_snap.get("windows"):
                    _write_cache(cli_snap)
                    return cli_snap

    # 4. Optional Orca fallback (never required)
    orca_snap = _try_orca_fallback()
    if orca_snap:
        _write_cache(orca_snap)
        return orca_snap

    # 5. Last-known-good stale cache
    stale = _read_cache(STALE_CACHE_MAX_AGE_SECONDS)
    if stale and stale.get("windows"):
        return {**stale, "status": "STALE", "stale": True, "message": "Showing last known Antigravity quota."}

    return _empty(
        "UNAVAILABLE",
        "Open Antigravity or install the agy CLI to show Antigravity quota.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    try:
        snapshot = collect(force=args.force)
    except Exception:  # noqa: BLE001
        snapshot = _empty("UNAVAILABLE", "Antigravity quota could not be read.")
    json.dump(snapshot, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

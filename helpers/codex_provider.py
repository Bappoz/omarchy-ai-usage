#!/usr/bin/env python3
"""Collect a privacy-preserving Codex quota snapshot.

The helper delegates authentication to ``codex app-server``. It never reads a
credential file and emits exactly one provider-neutral JSON object on stdout.
Provider failures are data, not process crashes: valid invocations exit zero
with an ERROR, UNAVAILABLE, NEEDS_AUTH, or STALE snapshot.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Self

PROVIDER_ID = "codex"
DISPLAY_NAME = "Codex"
CONTRACT_VERSION = 1
DEFAULT_TIMEOUT_SECONDS = 12.0
DEFAULT_MAX_OUTPUT_BYTES = 1_048_576
MAX_IGNORED_NON_JSON_LINES = 16
DEFAULT_MAX_CACHE_AGE_SECONDS = 7 * 24 * 60 * 60

TOKEN_PATTERNS = (
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
)
EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
CONTROL_PATTERN = re.compile(r"[\x00-\x1f\x7f]+")
IDENTIFIER_PART = re.compile(r"[^a-z0-9._-]+")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ProviderError(Exception):
    """A classified provider failure with a static, user-safe message."""

    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status
        self.safe_message = message


class RpcTimeout(ProviderError):
    def __init__(self) -> None:
        super().__init__("ERROR", "Codex did not respond before the refresh deadline.")


class RpcProtocolError(ProviderError):
    def __init__(self) -> None:
        super().__init__("ERROR", "Codex returned an unreadable response.")


class RpcRequestError(ProviderError):
    def __init__(self) -> None:
        super().__init__("ERROR", "Codex could not provide account limits.")


def redact_text(value: object, limit: int = 200) -> str:
    """Redact common secret and identity patterns from diagnostic text."""

    text = CONTROL_PATTERN.sub(" ", str(value))
    for pattern in TOKEN_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    text = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    home = str(Path.home())
    if home and home != "/":
        text = text.replace(home, "$HOME")
    return " ".join(text.split())[:limit]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def default_cache_path() -> Path:
    state_home = os.environ.get("XDG_STATE_HOME")
    root = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return root / "omarchy-ai-usage" / "codex-last-good.json"


def build_codex_command(codex_binary: str) -> list[str]:
    """Return the fixed, non-shell command used for the app-server child."""

    return [
        codex_binary,
        "--sandbox",
        "read-only",
        "--ask-for-approval",
        "on-request",
        "app-server",
        "--listen",
        "stdio://",
    ]


class CodexRpcClient:
    """Small bounded JSON-lines client for one Codex app-server refresh."""

    def __init__(
        self,
        command: Sequence[str],
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
        env: Mapping[str, str] | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if max_output_bytes < 1024:
            raise ValueError("max_output_bytes must be at least 1024")
        self.command = list(command)
        self.timeout_seconds = timeout_seconds
        self.max_output_bytes = max_output_bytes
        self.env = dict(env) if env is not None else None
        self.process: subprocess.Popen[bytes] | None = None
        self.selector: selectors.BaseSelector | None = None
        self.buffer = bytearray()
        self.output_bytes = 0
        self.ignored_non_json_lines = 0

    def __enter__(self) -> Self:
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                shell=False,
                env=self.env,
            )
        except FileNotFoundError as exc:
            raise ProviderError("UNAVAILABLE", "Codex is not installed or is not on PATH.") from exc
        except OSError as exc:
            raise ProviderError("UNAVAILABLE", "Codex could not be started.") from exc

        assert self.process.stdout is not None
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        return self

    def __exit__(self, *_: object) -> None:
        if self.selector is not None:
            self.selector.close()
        if self.process is None:
            return
        if self.process.stdin is not None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=1)
        if self.process.stdout is not None:
            self.process.stdout.close()

    def _send(self, payload: Mapping[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise RpcProtocolError()
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        try:
            self.process.stdin.write(encoded)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise RpcProtocolError() from exc

    def notify(self, method: str, params: Mapping[str, Any] | None = None) -> None:
        self._send({"method": method, "params": dict(params or {})})

    def request(
        self,
        request_id: int,
        method: str,
        params: Mapping[str, Any] | None,
        deadline: float,
    ) -> dict[str, Any]:
        self._send({"id": request_id, "method": method, "params": dict(params or {})})
        while True:
            message = self._read_message(deadline)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise RpcRequestError()
            result = message.get("result")
            if not isinstance(result, dict):
                raise RpcProtocolError()
            return result

    def _read_message(self, deadline: float) -> dict[str, Any]:
        if self.process is None or self.process.stdout is None or self.selector is None:
            raise RpcProtocolError()

        while True:
            newline = self.buffer.find(b"\n")
            if newline >= 0:
                raw = bytes(self.buffer[:newline])
                del self.buffer[: newline + 1]
                if not raw.strip():
                    continue
                try:
                    message = json.loads(raw)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    # Launchers such as mise may write a short status line to
                    # stdout before execing Codex. Discard bounded noise and
                    # never log it because it is outside the RPC contract.
                    self.ignored_non_json_lines += 1
                    if self.ignored_non_json_lines > MAX_IGNORED_NON_JSON_LINES:
                        raise RpcProtocolError()
                    continue
                if not isinstance(message, dict):
                    raise RpcProtocolError()
                return message

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RpcTimeout()
            events = self.selector.select(min(remaining, 0.25))
            if not events:
                if self.process.poll() is not None:
                    raise RpcProtocolError()
                continue

            try:
                chunk = os.read(self.process.stdout.fileno(), 4096)
            except OSError as exc:
                raise RpcProtocolError() from exc
            if not chunk:
                raise RpcProtocolError()
            self.output_bytes += len(chunk)
            if self.output_bytes > self.max_output_bytes:
                raise RpcProtocolError()
            self.buffer.extend(chunk)

    def collect(self) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        self.request(
            1,
            "initialize",
            {
                "clientInfo": {
                    "name": "omarchy-ai-usage",
                    "title": "Omarchy AI Usage",
                    "version": "0.8.0",
                },
                "capabilities": {"experimentalApi": False},
            },
            deadline,
        )
        self.notify("initialized")
        account = self.request(2, "account/read", {"refreshToken": False}, deadline)

        if account.get("account") is None and account.get("requiresOpenaiAuth") is True:
            return {"account": account, "limits": None}

        limits = self.request(3, "account/rateLimits/read", {}, deadline)
        return {"account": account, "limits": limits}


def _safe_label(value: object, maximum: int = 80) -> str | None:
    if not isinstance(value, str):
        return None
    value = CONTROL_PATTERN.sub(" ", value)
    value = " ".join(value.split())[:maximum]
    return value or None


def _slug(value: object, fallback: str) -> str:
    slug = IDENTIFIER_PART.sub("-", str(value).strip().lower()).strip("-._")
    return (slug or fallback)[:48]


def _percent(value: object) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProviderError("ERROR", "Codex returned invalid quota data.")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 100:
        raise ProviderError("ERROR", "Codex returned invalid quota data.")
    return int(number) if number.is_integer() else round(number, 4)


def _optional_positive_integer(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ProviderError("ERROR", "Codex returned invalid quota data.")
    return value


def _reset_timestamp(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ProviderError("ERROR", "Codex returned invalid quota data.")
    try:
        return isoformat_utc(datetime.fromtimestamp(value, timezone.utc))
    except (OverflowError, OSError, ValueError) as exc:
        raise ProviderError("ERROR", "Codex returned invalid quota data.") from exc


def _duration_label(minutes: int | None) -> str:
    if minutes == 10080:
        return "Weekly limit"
    if minutes and minutes % 1440 == 0:
        days = minutes // 1440
        return f"{days}-day limit"
    if minutes and minutes % 60 == 0:
        hours = minutes // 60
        return f"{hours}-hour limit"
    if minutes:
        return f"{minutes}-minute limit"
    return "Usage limit"


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


def normalize_codex_payload(payload: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    account_result = payload.get("account")
    if not isinstance(account_result, Mapping):
        raise ProviderError("ERROR", "Codex returned invalid account data.")

    raw_account = account_result.get("account")
    requires_auth = account_result.get("requiresOpenaiAuth")
    if raw_account is None and requires_auth is True:
        return _empty_snapshot("NEEDS_AUTH", "Sign in to Codex to read ChatGPT limits.")
    if raw_account is not None and not isinstance(raw_account, Mapping):
        raise ProviderError("ERROR", "Codex returned invalid account data.")

    limits_result = payload.get("limits")
    if not isinstance(limits_result, Mapping):
        return _empty_snapshot("UNAVAILABLE", "ChatGPT limits are unavailable for this Codex account.")

    multi = limits_result.get("rateLimitsByLimitId")
    buckets: list[tuple[str, Mapping[str, Any]]] = []
    if isinstance(multi, Mapping) and multi:
        for key in sorted(multi, key=str):
            value = multi[key]
            if isinstance(value, Mapping):
                buckets.append((str(key), value))
    else:
        legacy = limits_result.get("rateLimits")
        if isinstance(legacy, Mapping):
            buckets.append((str(legacy.get("limitId") or "codex"), legacy))

    plan: str | None = None
    if isinstance(raw_account, Mapping):
        plan = _safe_label(raw_account.get("planType"))
    windows: list[dict[str, Any]] = []
    primary_ids: list[tuple[str, str]] = []
    rate_limited = limits_result.get("ordinaryUsageAllowed") is False
    used_ids: set[str] = set()

    for bucket_key, bucket in buckets:
        bucket_id = _slug(bucket.get("limitId") or bucket_key, "codex")
        bucket_name = _safe_label(bucket.get("limitName"))
        if plan is None:
            plan = _safe_label(bucket.get("planType"))
        if bucket.get("rateLimitReachedType") is not None:
            rate_limited = True
        if bucket.get("spendControlReached") is True:
            rate_limited = True

        for slot in ("primary", "secondary"):
            raw_window = bucket.get(slot)
            if raw_window is None:
                continue
            if not isinstance(raw_window, Mapping):
                raise ProviderError("ERROR", "Codex returned invalid quota data.")
            used = _percent(raw_window.get("usedPercent"))
            duration = _optional_positive_integer(raw_window.get("windowDurationMins"))
            reset_at = _reset_timestamp(raw_window.get("resetsAt"))
            window_id = _slug(f"{bucket_id}-{slot}", slot)
            suffix = 2
            base_id = window_id
            while window_id in used_ids:
                window_id = f"{base_id}-{suffix}"
                suffix += 1
            used_ids.add(window_id)

            duration_name = _duration_label(duration)
            name = f"{bucket_name} · {duration_name}" if bucket_name else duration_name
            remaining = round(100 - float(used), 4)
            if remaining.is_integer():
                remaining = int(remaining)
            windows.append(
                {
                    "id": window_id,
                    "name": name,
                    "usedPercent": used,
                    "remainingPercent": remaining,
                    "resetAt": reset_at,
                    "durationMinutes": duration,
                    "fidelity": "OFFICIAL",
                }
            )
            if slot == "primary":
                primary_ids.append((bucket_id, window_id))

    if not windows:
        snapshot = _empty_snapshot(
            "UNAVAILABLE", "ChatGPT limits are unavailable for this Codex account."
        )
        if plan:
            snapshot["account"] = {"label": None, "plan": plan}
        return snapshot

    headline = next((item for bucket, item in primary_ids if bucket == "codex"), None)
    if headline is None and primary_ids:
        headline = primary_ids[0][1]
    if headline is None:
        headline = windows[0]["id"]

    return {
        "schemaVersion": CONTRACT_VERSION,
        "providerId": PROVIDER_ID,
        "displayName": DISPLAY_NAME,
        "account": {"label": None, "plan": plan} if plan else None,
        "status": "RATE_LIMITED" if rate_limited else "ACTIVE",
        "lastUpdated": isoformat_utc(now),
        "stale": False,
        "headlineWindowId": headline,
        "windows": windows,
        "message": "A Codex limit is currently active." if rate_limited else None,
    }


def _parse_snapshot_time(snapshot: Mapping[str, Any]) -> datetime | None:
    value = snapshot.get("lastUpdated")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _valid_cached_snapshot(snapshot: object) -> bool:
    if not isinstance(snapshot, Mapping):
        return False
    if snapshot.get("schemaVersion") != CONTRACT_VERSION:
        return False
    if snapshot.get("providerId") != PROVIDER_ID:
        return False
    if snapshot.get("displayName") != DISPLAY_NAME:
        return False
    if snapshot.get("status") not in {"ACTIVE", "RATE_LIMITED"}:
        return False
    if snapshot.get("stale") is not False:
        return False
    if set(snapshot) - {
        "schemaVersion",
        "providerId",
        "displayName",
        "account",
        "status",
        "lastUpdated",
        "stale",
        "headlineWindowId",
        "windows",
        "message",
    }:
        return False
    account = snapshot.get("account")
    if account is not None:
        if not isinstance(account, Mapping) or set(account) != {"label", "plan"}:
            return False
        for value in account.values():
            if value is not None and (not isinstance(value, str) or not 1 <= len(value) <= 80):
                return False
    message = snapshot.get("message")
    if message is not None and (not isinstance(message, str) or not 1 <= len(message) <= 200):
        return False

    windows = snapshot.get("windows")
    if not isinstance(windows, list) or not 1 <= len(windows) <= 32:
        return False
    window_ids: set[str] = set()
    for window in windows:
        if not isinstance(window, Mapping) or set(window) != {
            "id",
            "name",
            "usedPercent",
            "remainingPercent",
            "resetAt",
            "durationMinutes",
            "fidelity",
        }:
            return False
        window_id = window.get("id")
        if not isinstance(window_id, str) or not IDENTIFIER.fullmatch(window_id):
            return False
        if window_id in window_ids:
            return False
        window_ids.add(window_id)
        name = window.get("name")
        if not isinstance(name, str) or not 1 <= len(name) <= 80:
            return False
        if window.get("fidelity") not in {"OFFICIAL", "DERIVED", "MANUAL"}:
            return False
        percentages: list[float] = []
        for field in ("usedPercent", "remainingPercent"):
            value = window.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or not 0 <= value <= 100
            ):
                return False
            percentages.append(float(value))
        if not math.isclose(sum(percentages), 100, abs_tol=0.01):
            return False
        duration = window.get("durationMinutes")
        if duration is not None and (
            isinstance(duration, bool) or not isinstance(duration, int) or duration < 1
        ):
            return False
        reset_at = window.get("resetAt")
        if reset_at is not None:
            if not isinstance(reset_at, str):
                return False
            try:
                parsed_reset = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
            except ValueError:
                return False
            if parsed_reset.tzinfo is None:
                return False

    if snapshot.get("headlineWindowId") not in window_ids:
        return False
    return _parse_snapshot_time(snapshot) is not None


def read_last_good(path: Path, now: datetime, max_age_seconds: int) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > DEFAULT_MAX_OUTPUT_BYTES:
            return None
        envelope = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(envelope, dict) or envelope.get("cacheVersion") != 1:
            return None
        snapshot = envelope.get("snapshot")
        if not _valid_cached_snapshot(snapshot):
            return None
        updated = _parse_snapshot_time(snapshot)
        assert updated is not None
        age = (now.astimezone(timezone.utc) - updated).total_seconds()
        if age < 0 or age > max_age_seconds:
            return None
        return copy.deepcopy(dict(snapshot))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, TypeError):
        return None


def write_last_good(path: Path, snapshot: Mapping[str, Any]) -> None:
    if not _valid_cached_snapshot(snapshot):
        raise ValueError("only current successful snapshots may be cached")
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    payload = json.dumps(
        {"cacheVersion": 1, "snapshot": snapshot},
        ensure_ascii=False,
        separators=(",", ":"),
    ) + "\n"
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
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


def stale_from_cache(
    path: Path, now: datetime, max_age_seconds: int
) -> dict[str, Any] | None:
    snapshot = read_last_good(path, now, max_age_seconds)
    if snapshot is None:
        return None
    snapshot["status"] = "STALE"
    snapshot["stale"] = True
    snapshot["message"] = "Showing the last successful refresh; current Codex data is unavailable."
    return snapshot


def refresh_provider(
    fetch: Callable[[], Mapping[str, Any]],
    *,
    cache_path: Path | None,
    now: datetime | None = None,
    max_cache_age_seconds: int = DEFAULT_MAX_CACHE_AGE_SECONDS,
) -> dict[str, Any]:
    current_time = now or utc_now()
    try:
        snapshot = normalize_codex_payload(fetch(), current_time)
    except ProviderError as exc:
        snapshot = _empty_snapshot(exc.status, exc.safe_message)
    # This is the process boundary: an unforeseen provider/parser failure must
    # become safe data rather than terminate the long-lived shell caller.
    except Exception:  # noqa: BLE001
        snapshot = _empty_snapshot("ERROR", "Codex usage could not be refreshed.")

    if snapshot["status"] in {"ACTIVE", "RATE_LIMITED"}:
        if cache_path is not None:
            try:
                write_last_good(cache_path, snapshot)
            except (OSError, ValueError):
                pass
        return snapshot

    if snapshot["status"] in {"ERROR", "UNAVAILABLE"} and cache_path is not None:
        cached = stale_from_cache(cache_path, current_time, max_cache_age_seconds)
        if cached is not None:
            return cached
    return snapshot


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-bin", help="Explicit Codex executable path")
    parser.add_argument(
        "--cache-path", type=Path, default=default_cache_path(), help="Last-good cache file"
    )
    parser.add_argument("--no-cache", action="store_true", help="Disable cache reads and writes")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="Whole refresh deadline"
    )
    parser.add_argument(
        "--max-cache-age",
        type=int,
        default=DEFAULT_MAX_CACHE_AGE_SECONDS,
        help="Maximum last-good age in seconds",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0 or args.max_cache_age < 0:
        print("timeout must be positive and max-cache-age cannot be negative", file=sys.stderr)
        return 2

    codex_binary = args.codex_bin or shutil.which("codex")
    cache_path = None if args.no_cache else args.cache_path

    if not codex_binary:
        snapshot = refresh_provider(
            lambda: (_ for _ in ()).throw(
                ProviderError("UNAVAILABLE", "Codex is not installed or is not on PATH.")
            ),
            cache_path=cache_path,
            max_cache_age_seconds=args.max_cache_age,
        )
    else:
        command = build_codex_command(codex_binary)

        def fetch() -> Mapping[str, Any]:
            with CodexRpcClient(command, timeout_seconds=args.timeout) as client:
                return client.collect()

        snapshot = refresh_provider(
            fetch,
            cache_path=cache_path,
            max_cache_age_seconds=args.max_cache_age,
        )

    print(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

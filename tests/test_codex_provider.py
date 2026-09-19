from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from test_contract import validate_snapshot

from helpers.codex_provider import (
    CodexRpcClient,
    ProviderError,
    RpcProtocolError,
    RpcRequestError,
    RpcTimeout,
    build_codex_command,
    normalize_codex_payload,
    redact_text,
    refresh_provider,
)

ROOT = Path(__file__).resolve().parents[1]
FAKE_SERVER = ROOT / "tests" / "fakes" / "fake_codex_app_server.py"
NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def fake_collect(scenario: str, timeout: float = 2.0) -> dict:
    env = os.environ.copy()
    env["FAKE_CODEX_SCENARIO"] = scenario
    with CodexRpcClient(
        [sys.executable, str(FAKE_SERVER)], timeout_seconds=timeout, env=env
    ) as client:
        return client.collect()


class RpcClientTests(unittest.TestCase):
    def test_fixed_live_command_has_no_shell_or_write_access(self) -> None:
        self.assertEqual(
            build_codex_command("/usr/bin/codex"),
            [
                "/usr/bin/codex",
                "--sandbox",
                "read-only",
                "--ask-for-approval",
                "on-request",
                "app-server",
                "--listen",
                "stdio://",
            ],
        )

    def test_rpc_error_is_classified_without_returning_server_message(self) -> None:
        with self.assertRaises(RpcRequestError) as raised:
            fake_collect("rpc_error")
        self.assertNotIn("SENSITIVE_MARKER", str(raised.exception))

    def test_malformed_output_is_rejected(self) -> None:
        with self.assertRaises(RpcProtocolError):
            fake_collect("malformed")

    def test_whole_refresh_deadline_is_enforced(self) -> None:
        with self.assertRaises(RpcTimeout):
            fake_collect("timeout", timeout=0.1)

    def test_total_stdout_is_bounded(self) -> None:
        env = os.environ.copy()
        env["FAKE_CODEX_SCENARIO"] = "oversized"
        with self.assertRaises(RpcProtocolError), CodexRpcClient(
            [sys.executable, str(FAKE_SERVER)],
            timeout_seconds=1,
            max_output_bytes=1024,
            env=env,
        ) as client:
            client.collect()

    def test_one_bounded_launcher_status_line_is_ignored(self) -> None:
        snapshot = normalize_codex_payload(fake_collect("launcher_noise"), NOW)
        self.assertEqual(snapshot["status"], "ACTIVE")


class NormalizationTests(unittest.TestCase):
    def test_multi_bucket_view_wins_over_legacy(self) -> None:
        snapshot = normalize_codex_payload(fake_collect("success_multi"), NOW)
        self.assertEqual(snapshot["status"], "ACTIVE")
        self.assertEqual(snapshot["headlineWindowId"], "codex-primary")
        self.assertEqual(len(snapshot["windows"]), 3)
        self.assertNotIn(99, [window["usedPercent"] for window in snapshot["windows"]])
        self.assertEqual(snapshot["windows"][0]["remainingPercent"], 75)
        self.assertEqual(snapshot["account"], {"label": None, "plan": "plus"})
        self.assertNotIn("fixture@example.invalid", json.dumps(snapshot))

    def test_legacy_bucket_is_supported(self) -> None:
        snapshot = normalize_codex_payload(fake_collect("legacy"), NOW)
        self.assertEqual(snapshot["headlineWindowId"], "codex-primary")
        self.assertEqual(snapshot["windows"][0]["name"], "5-hour limit")
        self.assertEqual(snapshot["windows"][0]["resetAt"], "2030-01-01T00:00:00Z")

    def test_missing_auth_is_a_non_crashing_state(self) -> None:
        snapshot = normalize_codex_payload(fake_collect("needs_auth"), NOW)
        self.assertEqual(snapshot["status"], "NEEDS_AUTH")
        self.assertEqual(snapshot["windows"], [])

    def test_invalid_percent_is_rejected_not_clamped(self) -> None:
        with self.assertRaises(ProviderError):
            normalize_codex_payload(fake_collect("invalid_percent"), NOW)

    def test_explicit_backend_limit_state_controls_rate_limited_status(self) -> None:
        payload = fake_collect("legacy")
        payload["limits"]["rateLimits"]["rateLimitReachedType"] = "rate_limit_reached"
        payload["limits"]["rateLimits"]["primary"]["usedPercent"] = 20
        snapshot = normalize_codex_payload(payload, NOW)
        self.assertEqual(snapshot["status"], "RATE_LIMITED")

    def test_redaction_removes_tokens_email_and_home(self) -> None:
        diagnostic = (
            "Bearer " + "abc.def " + "sk-" + "fixturesecret12 "
            + f"user@example.com {Path.home()}/private"
        )
        redacted = redact_text(diagnostic)
        self.assertNotIn("fixturesecret", redacted)
        self.assertNotIn("user@example.com", redacted)
        self.assertNotIn(str(Path.home()), redacted)
        self.assertIn("[REDACTED]", redacted)


class CacheTests(unittest.TestCase):
    def test_success_is_cached_with_private_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "state" / "codex.json"
            snapshot = refresh_provider(
                lambda: fake_collect("legacy"), cache_path=cache, now=NOW
            )
            self.assertEqual(snapshot["status"], "ACTIVE")
            self.assertTrue(cache.is_file())
            self.assertEqual(stat.S_IMODE(cache.stat().st_mode), 0o600)
            envelope = json.loads(cache.read_text())
            self.assertEqual(envelope["cacheVersion"], 1)

    def test_transient_failure_returns_last_good_as_stale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "codex.json"
            refresh_provider(lambda: fake_collect("legacy"), cache_path=cache, now=NOW)

            def fail() -> dict:
                raise RpcTimeout()

            snapshot = refresh_provider(
                fail, cache_path=cache, now=NOW + timedelta(minutes=5)
            )
            self.assertEqual(snapshot["status"], "STALE")
            self.assertTrue(snapshot["stale"])
            self.assertEqual(snapshot["lastUpdated"], "2030-01-01T12:00:00Z")
            self.assertTrue(snapshot["windows"])

    def test_expired_cache_is_not_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "codex.json"
            refresh_provider(lambda: fake_collect("legacy"), cache_path=cache, now=NOW)

            def fail() -> dict:
                raise RpcTimeout()

            snapshot = refresh_provider(
                fail,
                cache_path=cache,
                now=NOW + timedelta(days=8),
                max_cache_age_seconds=7 * 24 * 60 * 60,
            )
            self.assertEqual(snapshot["status"], "ERROR")
            self.assertFalse(snapshot["stale"])

    def test_future_dated_cache_is_not_used(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "codex.json"
            refresh_provider(lambda: fake_collect("legacy"), cache_path=cache, now=NOW)

            def fail() -> dict:
                raise RpcTimeout()

            snapshot = refresh_provider(
                fail, cache_path=cache, now=NOW - timedelta(minutes=1)
            )
            self.assertEqual(snapshot["status"], "ERROR")

    def test_symlinked_cache_is_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            link = Path(directory) / "link.json"
            refresh_provider(lambda: fake_collect("legacy"), cache_path=target, now=NOW)
            link.symlink_to(target)

            def fail() -> dict:
                raise RpcTimeout()

            snapshot = refresh_provider(
                fail, cache_path=link, now=NOW + timedelta(minutes=1)
            )
            self.assertEqual(snapshot["status"], "ERROR")

    def test_needs_auth_does_not_mask_state_with_old_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "codex.json"
            refresh_provider(lambda: fake_collect("legacy"), cache_path=cache, now=NOW)
            snapshot = refresh_provider(
                lambda: fake_collect("needs_auth"),
                cache_path=cache,
                now=NOW + timedelta(minutes=5),
            )
            self.assertEqual(snapshot["status"], "NEEDS_AUTH")

    def test_corrupt_cache_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "codex.json"
            cache.write_text("not-json")

            def fail() -> dict:
                raise RpcProtocolError()

            snapshot = refresh_provider(fail, cache_path=cache, now=NOW)
            self.assertEqual(snapshot["status"], "ERROR")

    def test_structurally_invalid_cache_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "codex.json"
            refresh_provider(lambda: fake_collect("legacy"), cache_path=cache, now=NOW)
            envelope = json.loads(cache.read_text())
            envelope["snapshot"]["windows"][0]["usedPercent"] = 140
            cache.write_text(json.dumps(envelope))

            def fail() -> dict:
                raise RpcProtocolError()

            snapshot = refresh_provider(fail, cache_path=cache, now=NOW)
            self.assertEqual(snapshot["status"], "ERROR")

    def test_all_emitted_states_satisfy_provider_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "codex.json"
            active = refresh_provider(
                lambda: fake_collect("legacy"), cache_path=cache, now=NOW
            )
            needs_auth = refresh_provider(
                lambda: fake_collect("needs_auth"), cache_path=cache, now=NOW
            )

            def fail() -> dict:
                raise RpcTimeout()

            stale = refresh_provider(
                fail, cache_path=cache, now=NOW + timedelta(minutes=1)
            )
            for snapshot in (active, needs_auth, stale):
                validate_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()

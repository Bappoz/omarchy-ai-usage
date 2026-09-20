from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from test_contract import validate_snapshot

from helpers.claude_provider import (
    ProviderError,
    build_collector_command,
    build_updater_command,
    collect_claude,
    collect_shared_claude,
    normalize_claude_payload,
    refresh_provider,
)

ROOT = Path(__file__).resolve().parents[1]
FAKE = ROOT / "tests" / "fakes" / "fake_claude_collector.py"
NOW = datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc)


def collect(scenario: str, timeout: float = 1.0) -> dict:
    old = os.environ.get("FAKE_CLAUDE_SCENARIO")
    os.environ["FAKE_CLAUDE_SCENARIO"] = scenario
    try:
        return dict(collect_claude([sys.executable, str(FAKE)], timeout_seconds=timeout))
    finally:
        if old is None:
            os.environ.pop("FAKE_CLAUDE_SCENARIO", None)
        else:
            os.environ["FAKE_CLAUDE_SCENARIO"] = old


class ClaudeProviderTests(unittest.TestCase):
    def test_fixed_command_uses_limits_only(self) -> None:
        self.assertEqual(build_collector_command("/collector"), ["/collector", "--limits-only"])

    def test_shared_updater_targets_only_claude_limits(self) -> None:
        self.assertEqual(
            build_updater_command("/updater"),
            ["/updater", "--limits-only", "claude"],
        )

    def test_shared_record_is_read_after_official_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            shared = Path(directory) / "claude.json"
            payload = collect("active")

            def fake_run(*args, **kwargs):
                shared.write_text(json.dumps(payload), encoding="utf-8")
                return subprocess.CompletedProcess(args[0], 0)

            with patch("helpers.claude_provider.subprocess.run", side_effect=fake_run) as run:
                result = collect_shared_claude(["/updater", "--limits-only", "claude"], shared)

            self.assertEqual(result["id"], "claude")
            self.assertEqual(run.call_args.args[0], ["/updater", "--limits-only", "claude"])
            self.assertFalse(run.call_args.kwargs["shell"])

    def test_shared_record_rejects_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target.json"
            target.write_text("{}", encoding="utf-8")
            shared = Path(directory) / "claude.json"
            shared.symlink_to(target)
            completed = subprocess.CompletedProcess(["/updater"], 0)
            with (
                patch("helpers.claude_provider.subprocess.run", return_value=completed),
                self.assertRaises(ProviderError),
            ):
                collect_shared_claude(["/updater"], shared)

    def test_active_limits_are_normalized(self) -> None:
        snapshot = normalize_claude_payload(collect("active"), NOW)
        validate_snapshot(snapshot)
        self.assertEqual(snapshot["status"], "ACTIVE")
        self.assertEqual(snapshot["account"], {"label": None, "plan": "Pro"})
        self.assertEqual(snapshot["windows"][0]["usedPercent"], 25)
        self.assertEqual(snapshot["windows"][1]["usedPercent"], 40)
        self.assertEqual(snapshot["windows"][0]["durationMinutes"], 300)
        self.assertEqual(snapshot["windows"][1]["durationMinutes"], 10080)

    def test_fraction_boundary_one_means_one_hundred_percent(self) -> None:
        payload = collect("active")
        payload["limits"][0]["percent"] = 1
        snapshot = normalize_claude_payload(payload, NOW)
        self.assertEqual(snapshot["windows"][0]["usedPercent"], 100)
        self.assertEqual(snapshot["windows"][0]["remainingPercent"], 0)

    def test_auth_state_is_safe_and_non_crashing(self) -> None:
        snapshot = normalize_claude_payload(collect("auth"), NOW)
        validate_snapshot(snapshot)
        self.assertEqual(snapshot["status"], "NEEDS_AUTH")

    def test_collector_stale_payload_remains_visible(self) -> None:
        snapshot = normalize_claude_payload(collect("stale"), NOW)
        validate_snapshot(snapshot)
        self.assertEqual(snapshot["status"], "STALE")
        self.assertTrue(snapshot["windows"])

    def test_timeout_is_classified(self) -> None:
        with self.assertRaises(ProviderError):
            collect("timeout", timeout=0.05)

    def test_last_good_cache_is_private_and_used_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / "claude.json"
            active = refresh_provider(lambda: collect("active"), cache_path=cache, now=NOW)
            self.assertEqual(active["status"], "ACTIVE")
            self.assertEqual(stat.S_IMODE(cache.stat().st_mode), 0o600)

            def fail() -> dict:
                raise ProviderError("ERROR", "safe")

            stale = refresh_provider(fail, cache_path=cache, now=NOW + timedelta(minutes=1))
            validate_snapshot(stale)
            self.assertEqual(stale["status"], "STALE")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from helpers import antigravity_provider
from test_contract import validate_snapshot


class AntigravityProviderTests(unittest.TestCase):
    def test_bridge_payload_normalizes_remaining_fraction_to_used_percent(self) -> None:
        payload = {
            "response": {
                "groups": [
                    {
                        "displayName": "Gemini 2.5 Pro",
                        "buckets": [
                            {
                                "bucketId": "gemini-pro-5h",
                                "displayName": "Five Hour Limit Remaining",
                                "remainingFraction": 0.65,
                                "resetTime": "2026-11-27T04:00:00Z",
                            }
                        ],
                    },
                    {
                        "displayName": "Claude and GPT models",
                        "buckets": [
                            {
                                "bucketId": "third-party-weekly",
                                "displayName": "Weekly Limit Remaining",
                                "remainingFraction": 0.2,
                                "resetTime": "2026-12-01T00:00:00Z",
                            }
                        ],
                    },
                ]
            }
        }
        windows = antigravity_provider.windows_from_bridge(payload)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["usedPercent"], 35)
        self.assertEqual(windows[0]["remainingPercent"], 65)
        self.assertEqual(windows[0]["durationMinutes"], 300)
        self.assertEqual(windows[1]["usedPercent"], 80)
        self.assertEqual(windows[1]["durationMinutes"], 10080)

        snap = antigravity_provider._build_snapshot(windows)
        validate_snapshot(snap)
        self.assertEqual(snap["providerId"], "antigravity")
        self.assertEqual(snap["status"], "ACTIVE")
        self.assertEqual(snap["headlineWindowId"], windows[0]["id"])

    def test_agy_cli_usage_output_parses_ansi_and_resets(self) -> None:
        sample = (
            "\x1b[1mQuota:\x1b[0m\r\n"
            "  Gemini Models Five Hour Limit Remaining\t72%\t2026-11-27 05:30 UTC\r\n"
            "  Claude and GPT Models Weekly Limit Remaining\t100%\t2026-12-02T12:00:00Z\r\n"
        )
        windows = antigravity_provider.parse_agy_cli_usage(sample)
        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["usedPercent"], 28)
        self.assertEqual(windows[0]["durationMinutes"], 300)
        self.assertEqual(windows[0]["resetAt"], "2026-11-27T05:30:00Z")
        self.assertEqual(windows[1]["usedPercent"], 0)
        self.assertEqual(windows[1]["durationMinutes"], 10080)

        snap = antigravity_provider._build_snapshot(windows)
        validate_snapshot(snap)

    def test_collect_works_without_orca_and_caches_privately(self) -> None:
        fake_snap = antigravity_provider._build_snapshot(
            [
                {
                    "id": "gemini-5h",
                    "name": "Gemini · 5h",
                    "usedPercent": 42,
                    "remainingPercent": 58,
                    "resetAt": "2026-11-27T05:30:00Z",
                    "durationMinutes": 300,
                    "fidelity": "OFFICIAL",
                }
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            with (
                mock.patch.dict(os.environ, {"XDG_CACHE_HOME": tmp}),
                mock.patch.object(antigravity_provider, "fetch_from_bridge", return_value=None),
                mock.patch.object(antigravity_provider, "fetch_from_agy_cli", return_value=fake_snap),
                mock.patch.object(antigravity_provider, "_try_orca_fallback") as orca_mock,
            ):
                snap = antigravity_provider.collect(force=True)
                validate_snapshot(snap)
                self.assertEqual(snap["status"], "ACTIVE")
                orca_mock.assert_not_called()
                cache_path = Path(tmp) / "omarchy-ai-usage" / "antigravity-snapshot.json"
                self.assertTrue(cache_path.is_file())
                self.assertEqual(cache_path.stat().st_mode & 0o777, 0o600)

                # Subsequent transient failure falls back to STALE cache without Orca.
                with (
                    mock.patch.object(antigravity_provider, "fetch_from_agy_cli", return_value=None),
                    mock.patch.object(antigravity_provider, "_try_orca_fallback", return_value=None),
                ):
                    stale = antigravity_provider.collect(force=True)
                    validate_snapshot(stale)
                    self.assertEqual(stale["status"], "STALE")
                    self.assertTrue(stale["stale"])


if __name__ == "__main__":
    unittest.main()

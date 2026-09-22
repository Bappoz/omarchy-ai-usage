from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path

from test_contract import validate_snapshot

from helpers.omarchy_agent_provider import ProviderError, normalize_record, read_record


def record(provider_id: str = "claude") -> dict:
    return {
        "schemaVersion": 1,
        "id": provider_id,
        "name": provider_id.title(),
        "ready": True,
        "updatedAt": "2030-01-01T12:00:00+00:00",
        "usageStatusText": "",
        "authHelpText": "do not expose provider text",
        "tierLabel": "Pro",
        "limits": [
            {"label": "Session (5-hour)", "percent": 0.27, "resetsAt": "2030-01-01T17:00:00Z"},
            {"label": "Weekly (7-day)", "percent": 0.42, "resetsAt": "2030-01-08T12:00:00Z"},
        ],
    }


class SharedRecordTests(unittest.TestCase):
    def test_normalizes_official_fractional_limits(self) -> None:
        snapshot = normalize_record(record(), "claude")
        validate_snapshot(snapshot)
        self.assertEqual(snapshot["status"], "ACTIVE")
        self.assertEqual(snapshot["headlineWindowId"], "weekly-7-day")
        self.assertEqual(snapshot["windows"][0]["usedPercent"], 27)
        self.assertEqual(snapshot["windows"][1]["remainingPercent"], 58)
        self.assertEqual(snapshot["account"], {"label": None, "plan": "Pro"})

    def test_codex_uses_the_same_official_contract(self) -> None:
        snapshot = normalize_record(record("codex"), "codex")
        validate_snapshot(snapshot)
        self.assertEqual(snapshot["providerId"], "codex")

    def test_auth_state_does_not_reuse_limits_as_active(self) -> None:
        value = record()
        value["ready"] = False
        value["usageStatusText"] = "Sign-in expired"
        snapshot = normalize_record(value, "claude")
        validate_snapshot(snapshot)
        self.assertEqual(snapshot["status"], "NEEDS_AUTH")

    def test_invalid_percent_is_rejected(self) -> None:
        value = record()
        value["limits"][0]["percent"] = 42
        with self.assertRaises(ProviderError):
            normalize_record(value, "claude")

    def test_reader_rejects_symlink_and_wrong_provider(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "record.json"
            target.write_text(json.dumps(record()), encoding="utf-8")
            target.chmod(0o600)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            link = Path(directory) / "link.json"
            link.symlink_to(target)
            with self.assertRaises(ProviderError):
                read_record(link, "claude")
            with self.assertRaises(ProviderError):
                read_record(target, "codex")


if __name__ == "__main__":
    unittest.main()

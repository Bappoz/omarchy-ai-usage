from __future__ import annotations

import json
import math
import re
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
SCHEMA = json.loads((ROOT / "contracts" / "provider-snapshot.schema.json").read_text())

STATUSES = set(SCHEMA["properties"]["status"]["enum"])
FIDELITIES = set(SCHEMA["$defs"]["usageWindow"]["properties"]["fidelity"]["enum"])
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SENSITIVE_KEY = re.compile(
    r"(?:authorization|cookie|credential|password|secret|token)", re.IGNORECASE
)
SENSITIVE_VALUE = re.compile(
    r"(?:bearer\s+[a-z0-9._~+/=-]+|sk-[a-z0-9_-]{12,})", re.IGNORECASE
)


def parse_datetime(value: str) -> None:
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def walk(value: Any, path: str = "$") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if SENSITIVE_KEY.search(key):
                raise AssertionError(f"sensitive key at {path}.{key}")
            walk(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            walk(child, f"{path}[{index}]")
    elif isinstance(value, str) and SENSITIVE_VALUE.search(value):
        raise AssertionError(f"token-like value at {path}")


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    required = set(SCHEMA["required"])
    allowed = set(SCHEMA["properties"])
    assert required <= set(snapshot), f"missing fields: {required - set(snapshot)}"
    assert set(snapshot) <= allowed, f"unknown fields: {set(snapshot) - allowed}"
    assert snapshot["schemaVersion"] == 1
    assert IDENTIFIER.fullmatch(snapshot["providerId"])
    assert 1 <= len(snapshot["displayName"]) <= 64
    assert snapshot["status"] in STATUSES
    assert isinstance(snapshot["stale"], bool)
    assert isinstance(snapshot["windows"], list)
    assert len(snapshot["windows"]) <= 32

    if snapshot["lastUpdated"] is not None:
        parse_datetime(snapshot["lastUpdated"])

    account = snapshot.get("account")
    if account is not None:
        assert set(account) == {"label", "plan"}
        for value in account.values():
            assert value is None or 1 <= len(value) <= 80

    message = snapshot.get("message")
    assert message is None or 1 <= len(message) <= 200

    window_ids: set[str] = set()
    for window in snapshot["windows"]:
        assert set(window) == {
            "id",
            "name",
            "usedPercent",
            "remainingPercent",
            "resetAt",
            "durationMinutes",
            "fidelity",
        }
        assert IDENTIFIER.fullmatch(window["id"])
        assert window["id"] not in window_ids
        window_ids.add(window["id"])
        assert 1 <= len(window["name"]) <= 80
        assert window["fidelity"] in FIDELITIES

        for field in ("usedPercent", "remainingPercent"):
            value = window[field]
            assert value is None or (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and 0 <= value <= 100
            )

        used = window["usedPercent"]
        remaining = window["remainingPercent"]
        if used is not None and remaining is not None:
            assert math.isclose(used + remaining, 100, abs_tol=0.01)

        reset_at = window["resetAt"]
        if reset_at is not None:
            parse_datetime(reset_at)

        duration = window["durationMinutes"]
        assert duration is None or (
            isinstance(duration, int) and not isinstance(duration, bool) and duration >= 1
        )

    headline = snapshot["headlineWindowId"]
    assert headline is None or headline in window_ids

    if snapshot["status"] == "ACTIVE":
        assert not snapshot["stale"]
        assert snapshot["windows"]
        assert headline is not None
    if snapshot["status"] == "STALE":
        assert snapshot["stale"]
        assert snapshot["lastUpdated"] is not None
        assert snapshot["windows"]
    if snapshot["stale"]:
        assert snapshot["status"] == "STALE"

    walk(snapshot)


class ProviderContractTests(unittest.TestCase):
    def test_all_fixtures_satisfy_contract(self) -> None:
        fixtures = sorted(FIXTURES.glob("*.json"))
        self.assertGreaterEqual(len(fixtures), 3)
        for path in fixtures:
            with self.subTest(path=path.name):
                validate_snapshot(json.loads(path.read_text()))

    def test_contract_contains_every_required_provider_state(self) -> None:
        self.assertEqual(
            STATUSES,
            {
                "ACTIVE",
                "LOADING",
                "STALE",
                "NEEDS_AUTH",
                "RATE_LIMITED",
                "ERROR",
                "UNAVAILABLE",
            },
        )

    def test_headline_window_must_be_explicit(self) -> None:
        snapshot = json.loads((FIXTURES / "active.json").read_text())
        snapshot["headlineWindowId"] = "not-present"
        with self.assertRaises(AssertionError):
            validate_snapshot(snapshot)

    def test_percentages_must_be_complementary_when_both_exist(self) -> None:
        snapshot = json.loads((FIXTURES / "active.json").read_text())
        snapshot["windows"][0]["remainingPercent"] = 80
        with self.assertRaises(AssertionError):
            validate_snapshot(snapshot)

    def test_secret_like_fields_are_rejected(self) -> None:
        snapshot = json.loads((FIXTURES / "active.json").read_text())
        snapshot["accessToken"] = "redacted"
        with self.assertRaises(AssertionError):
            walk(snapshot)


if __name__ == "__main__":
    unittest.main()

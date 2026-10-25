from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from helpers.insights_provider import (
    HOURS,
    Event,
    build_insights,
    claude_events,
    codex_events,
    isoformat_utc,
)

ROOT = Path(__file__).resolve().parents[1]
# Real clock: the helper filters log files by their on-disk mtime.
NOW = datetime.now(UTC).replace(minute=30, second=0, microsecond=0)
SINCE = NOW - timedelta(days=7)
SECRET = "SECRET-PROMPT-TEXT-must-never-leave-the-helper"


def claude_line(message_id: str | None, at: datetime, model: str = "claude-sonnet-5-5", **usage: int) -> str:
    usage = {"input_tokens": 1, "output_tokens": 10, "cache_creation_input_tokens": 5, **usage}
    message: dict[str, object] = {
        "model": model,
        "usage": usage,
        "content": [{"type": "text", "text": SECRET}],
    }
    if message_id:
        message["id"] = message_id
    return json.dumps(
        {"type": "assistant", "timestamp": isoformat_utc(at), "effort": "high", "message": message}
    )


def codex_turn(model: str, effort: str = "medium") -> str:
    return json.dumps({"type": "turn_context", "payload": {"model": model, "effort": effort}})


def codex_count(at: datetime, input_tokens: int, cached: int, output: int) -> str:
    total = {"input_tokens": input_tokens, "cached_input_tokens": cached, "output_tokens": output}
    return json.dumps(
        {
            "type": "event_msg",
            "timestamp": isoformat_utc(at),
            "payload": {"type": "token_count", "info": {"total_token_usage": total}},
        }
    )


class InsightsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name: str, lines: list[str]) -> Path:
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def test_claude_dedupes_streamed_blocks_and_resumed_history(self) -> None:
        at = NOW - timedelta(hours=1)
        self.write("a/one.jsonl", [claude_line("m1", at, output_tokens=4), claude_line("m1", at, output_tokens=10)])
        self.write("b/two.jsonl", [claude_line("m1", at, output_tokens=10), claude_line("m2", at)])
        events = claude_events(self.root, SINCE)
        self.assertEqual(sorted(event.tokens for event in events), [16, 16])

    def test_claude_counts_fresh_tokens_only_and_skips_synthetic_and_old(self) -> None:
        at = NOW - timedelta(hours=2)
        self.write(
            "s.jsonl",
            [
                claude_line("m1", at, cache_read_input_tokens=999_999),
                claude_line("m2", at, model="<synthetic>"),
                claude_line("m3", NOW - timedelta(days=9)),
                "not json",
                json.dumps({"type": "user", "message": {"content": SECRET}}),
            ],
        )
        events = claude_events(self.root, SINCE)
        self.assertEqual([(event.model, event.tokens, event.effort) for event in events], [("claude-sonnet-5-5", 16, "high")])

    def test_codex_uses_cumulative_deltas_and_ignores_repeated_totals(self) -> None:
        base = NOW - timedelta(hours=3)
        self.write(
            "2030/01/08/rollout-1.jsonl",
            [
                codex_turn("gpt-6-luna"),
                codex_count(base, 100, 40, 20),  # fresh 80
                codex_count(base + timedelta(minutes=1), 100, 40, 20),  # rate-limit refresh, no change
                codex_count(base + timedelta(minutes=2), 160, 40, 50),  # fresh 170 -> delta 90
                codex_turn("gpt-6-mini", "low"),
                codex_count(base + timedelta(minutes=3), 10, 0, 5),  # total reset -> 15
            ],
        )
        events = codex_events(self.root, SINCE)
        self.assertEqual([(e.model, e.tokens, e.effort) for e in events], [("gpt-6-luna", 80, "medium"), ("gpt-6-luna", 90, "medium"), ("gpt-6-mini", 15, "low")])

    def test_buckets_totals_shares_and_current_model(self) -> None:
        hour = NOW.replace(minute=0, second=0, microsecond=0)
        events = [
            Event(hour + timedelta(minutes=5), "a", 30, "low"),
            Event(hour - timedelta(hours=5), "a", 50),
            Event(hour - timedelta(hours=30), "b", 20),
        ]
        result = build_insights("claude", events, NOW, available=True)
        tokens = [bucket["tokens"] for bucket in result["hourly"]]
        self.assertEqual(len(tokens), HOURS)
        self.assertEqual((tokens[-1], tokens[-6]), (30, 50))
        self.assertEqual(result["totals"]["last24hTokens"], 80)
        self.assertEqual(result["totals"]["last7dTokens"], 100)
        self.assertEqual([m["name"] for m in result["models"]], ["a", "b"])
        self.assertAlmostEqual(sum(m["share"] for m in result["models"]), 1, places=3)
        self.assertEqual(result["currentModel"]["name"], "a")
        self.assertEqual(result["currentModel"]["effort"], "low")

    def test_long_tail_of_models_collapses_into_other(self) -> None:
        events = [Event(NOW - timedelta(hours=1), f"m{i}", 100 - i) for i in range(8)]
        names = [m["name"] for m in build_insights("codex", events, NOW, available=True)["models"]]
        self.assertEqual(len(names), 6)
        self.assertEqual(names[-1], "other")

    def test_missing_logs_are_unavailable_not_an_error(self) -> None:
        result = build_insights("claude", claude_events(self.root / "nope", SINCE), NOW, available=False)
        self.assertFalse(result["available"])
        self.assertIsNone(result["currentModel"])
        self.assertEqual(result["totals"]["last7dTokens"], 0)

    def test_cli_emits_only_aggregates_never_conversation_text(self) -> None:
        self.write("projects/p/s.jsonl", [claude_line("m1", datetime.now(UTC) - timedelta(minutes=1))])
        completed = subprocess.run(
            [sys.executable, str(ROOT / "helpers" / "insights_provider.py"), "--provider", "claude"],
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_CONFIG_DIR": str(self.root)},
            check=True,
        )
        self.assertNotIn(SECRET, completed.stdout)
        document = json.loads(completed.stdout)
        self.assertEqual(document["schemaVersion"], 1)
        self.assertEqual(document["totals"]["last7dTokens"], 16)


if __name__ == "__main__":
    unittest.main()

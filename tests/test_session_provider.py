from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import session_provider as sp


class SessionProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, path: str, value: object) -> Path:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))
        return target

    def rollout(self, events: list[dict], *, source: object = "cli") -> Path:
        path = self.root / "rollout.jsonl"
        records = [{"type": "session_meta", "payload": {"id": "synthetic-session", "cwd": "/example/workspace", "source": source}}]
        records += [{"type": "event_msg", "payload": event} for event in events]
        path.write_text("\n".join(json.dumps(record) for record in records) + "\n")
        return path

    def test_claude_only_live_processes_and_normalized_states(self) -> None:
        self.write("sessions/live.json", {"pid": 123, "cwd": "/example/project", "status": "busy", "name": "Build"})
        self.write("sessions/dead.json", {"pid": 456, "cwd": "/example/project", "status": "busy"})
        with patch.object(sp, "process_info", side_effect=lambda pid, _: (1, "90") if pid == 123 else None):
            sessions = sp.claude_sessions(self.root)
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["state"], "busy")
        self.assertEqual(sessions[0]["detail"], "Terminal · project")
        self.assertNotIn("/example", json.dumps(sessions))

    def test_claude_blocked_tempo_overrides_busy_status(self) -> None:
        self.write("sessions/live.json", {"pid": 123, "cwd": "/example/project", "tempo": "blocked", "status": "busy", "needs": "private prompt"})
        with patch.object(sp, "process_info", return_value=(1, "90")):
            sessions = sp.claude_sessions(self.root)
        self.assertEqual(sessions[0]["state"], "waiting")
        self.assertNotIn("private prompt", json.dumps(sessions))

    def test_malformed_registry_does_not_crash_or_complete_session(self) -> None:
        self.write("sessions/live.json", {"pid": 123, "cwd": "/example/project", "status": {"unknown": True}})
        self.write("sessions/bad.json", ["not a record"])
        with patch.object(sp, "process_info", return_value=(1, "90")):
            sessions = sp.claude_sessions(self.root)
        self.assertEqual(sessions[0]["state"], "unknown")

    def test_registry_symlinks_are_rejected(self) -> None:
        source = self.write("record.json", {"pid": 123})
        link = self.root / "linked.json"
        link.symlink_to(source)
        self.assertIsNone(sp.regular_json(link))

    def test_claude_transcript_fallback_ignores_sidechains_and_bookkeeping(self) -> None:
        record = {"pid": 123, "cwd": "/example/project", "sessionId": "synthetic", "nameSource": "derived"}
        self.write("sessions/live.json", record)
        path = self.root / "projects/-example-project/synthetic.jsonl"
        path.parent.mkdir(parents=True)
        records = [
            {"type": "custom-title", "customTitle": "Build test"},
            {"type": "assistant", "message": {"stop_reason": "tool_use", "content": "private"}},
            {"type": "assistant", "isSidechain": True, "message": {"stop_reason": "end_turn"}},
            {"type": "bridge-session", "content": "private bookkeeping"},
        ]
        path.write_text("\n".join(json.dumps(r) for r in records))
        reader = sp.ClaudeTranscripts()
        with patch.object(sp, "process_info", return_value=(1, "90")):
            found = sp.claude_sessions(self.root, transcripts=reader)
        self.assertEqual((found[0]["name"], found[0]["state"]), ("Build test", "busy"))
        self.assertNotIn("private", json.dumps(found))
        with path.open("a") as handle:
            handle.write("\n" + json.dumps({"type": "assistant", "message": {"stop_reason": "end_turn"}}))
        self.assertEqual(reader.read(self.root, record)[0], "idle")

    def test_codex_waits_only_for_an_unanswered_input_request(self) -> None:
        path = self.rollout([{"type": "task_started"}])
        with path.open("a") as handle:
            handle.write(json.dumps({"type": "response_item", "payload": {"type": "function_call", "name": "request_user_input", "call_id": "call-1", "arguments": "private question"}}) + "\n")
        reader = sp.RolloutReader()
        self.assertEqual(reader.read(path)["state"], "waiting")
        with path.open("a") as handle:
            handle.write(json.dumps({"type": "response_item", "payload": {"type": "function_call_output", "call_id": "call-1", "output": "private answer"}}) + "\n")
        self.assertEqual(reader.read(path)["state"], "busy")

    def test_tool_completion_is_not_turn_completion(self) -> None:
        path = self.rollout([{"type": "task_started"}, {"type": "item_completed", "output": "private tool output"}])
        reader = sp.RolloutReader()
        self.assertEqual(reader.read(path)["state"], "busy")
        result = reader.collect(self.root, opened={path: (123, "90")})
        self.assertEqual(result[0]["state"], "busy")
        self.assertNotIn("private tool output", json.dumps(result))

    def test_newest_lifecycle_event_wins(self) -> None:
        reader = sp.RolloutReader()
        path = self.rollout([{"type": "task_started"}, {"type": "task_complete"}, {"type": "task_started"}])
        self.assertEqual(reader.read(path)["state"], "busy")
        with path.open("a") as handle:
            handle.write(json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}) + "\n")
        self.assertEqual(reader.read(path)["state"], "success")

    def test_old_open_rollout_stays_busy_and_helper_is_not_announced(self) -> None:
        path = self.rollout([{"type": "task_started"}])
        os.utime(path, (time.time() - 3600, time.time() - 3600))
        reader = sp.RolloutReader()
        self.assertEqual(reader.collect(self.root, opened={path: (123, "90")})[0]["state"], "busy")
        path = self.rollout([{"type": "task_complete"}], source={"subagent": {"parent_thread_id": "parent"}})
        self.assertEqual(reader.collect(self.root, opened={path: (123, "90")}), [])

    def test_tail_is_bounded_and_unchanged_rollout_is_not_reopened(self) -> None:
        path = self.rollout([{"type": "task_started"}])
        with path.open("a") as handle:
            handle.write(json.dumps({"type": "private", "body": "x" * (sp.TAIL_BYTES + 10)}) + "\n")
            handle.write(json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}) + "\n")
        reader = sp.RolloutReader()
        self.assertEqual(reader.read(path)["state"], "success")
        with patch.object(Path, "open", side_effect=AssertionError("unchanged file was reopened")):
            self.assertEqual(reader.read(path)["state"], "success")

    def test_recycled_pid_cannot_focus_a_window(self) -> None:
        with patch.object(sp, "process_info", return_value=(1, "99")), patch.object(sp.subprocess, "run") as run:
            self.assertFalse(sp.focus_session(123, "90"))
            run.assert_not_called()

    def test_focus_resolves_ancestor_with_validated_address(self) -> None:
        def info(pid: int) -> tuple[int, str] | None:
            return {123: (50, "90"), 50: (1, "80")}.get(pid)

        clients = [{"pid": 50, "address": "0x123abc"}]
        with patch.object(sp, "process_info", side_effect=info), patch.object(sp.subprocess, "run") as run:
            run.return_value.stdout = json.dumps(clients).encode()
            self.assertTrue(sp.focus_session(123, "90"))
            self.assertEqual(run.call_args_list[1].args[0], ["hyprctl", "dispatch", "focuswindow", "address:0x123abc"])

    def bot_home(self, name: str, bot_id: str | None) -> str:
        home = self.root / ".orca/bots" / name
        home.mkdir(parents=True)
        if bot_id is not None:
            (home / "bot.json").write_text(json.dumps({"id": bot_id, "name": name.title()}))
        return str(home)

    def bots(self, paused: set[str] | None, clock: list[float] | None = None) -> tuple[sp.OrcaBots, list[int]]:
        calls: list[int] = []

        def fetch() -> set[str] | None:
            calls.append(1)
            return paused

        ticks = clock if clock is not None else [0.0]
        return sp.OrcaBots(self.root / ".orca/bots", fetch=fetch, clock=lambda: ticks[0]), calls

    def test_paused_orca_bot_session_is_hidden_and_others_are_kept(self) -> None:
        paused = self.bot_home("atelier", "id-paused")
        active = self.bot_home("maestro", "id-active")
        self.write("sessions/a.json", {"pid": 1, "cwd": paused, "name": "Home", "status": "idle", "entrypoint": "orca"})
        self.write("sessions/b.json", {"pid": 2, "cwd": active, "name": "Home", "status": "idle", "entrypoint": "orca"})
        self.write("sessions/c.json", {"pid": 3, "cwd": "/example/project", "name": "Work", "status": "busy"})
        bots, _ = self.bots({"id-paused"})
        with patch.object(sp, "process_info", return_value=(1, "90")):
            found = sp.claude_sessions(self.root, bots=bots)
        self.assertEqual(sorted(item["pid"] for item in found), [2, 3])

    def test_bot_session_returns_once_the_bot_is_no_longer_paused(self) -> None:
        home = self.bot_home("atelier", "id-1")
        self.write("sessions/a.json", {"pid": 1, "cwd": home, "name": "Home", "status": "idle"})
        state: dict[str, set[str] | None] = {"paused": {"id-1"}}
        clock = [0.0]
        bots = sp.OrcaBots(self.root / ".orca/bots", fetch=lambda: state["paused"], clock=lambda: clock[0])
        with patch.object(sp, "process_info", return_value=(1, "90")):
            self.assertEqual(sp.claude_sessions(self.root, bots=bots), [])
            state["paused"] = set()
            self.assertEqual(sp.claude_sessions(self.root, bots=bots), [])  # still inside the cache window
            clock[0] += sp.ORCA_BOTS_TTL + 1
            self.assertEqual(len(sp.claude_sessions(self.root, bots=bots)), 1)

    def test_orca_is_not_queried_without_a_bot_session(self) -> None:
        self.bot_home("atelier", "id-1")
        self.write("sessions/c.json", {"pid": 3, "cwd": "/example/project", "status": "busy"})
        bots, calls = self.bots({"id-1"})
        with patch.object(sp, "process_info", return_value=(1, "90")):
            self.assertEqual(len(sp.claude_sessions(self.root, bots=bots)), 1)
        self.assertEqual(calls, [])

    def test_orca_query_is_cached_across_polls(self) -> None:
        home = self.bot_home("atelier", "id-1")
        self.write("sessions/a.json", {"pid": 1, "cwd": home, "status": "idle"})
        bots, calls = self.bots({"id-1"})
        with patch.object(sp, "process_info", return_value=(1, "90")):
            for _ in range(3):
                sp.claude_sessions(self.root, bots=bots)
        self.assertEqual(len(calls), 1)

    def test_unavailable_orca_hides_nothing(self) -> None:
        home = self.bot_home("atelier", "id-1")
        self.write("sessions/a.json", {"pid": 1, "cwd": home, "status": "idle"})
        bots, _ = self.bots(None)
        with patch.object(sp, "process_info", return_value=(1, "90")):
            self.assertEqual(len(sp.claude_sessions(self.root, bots=bots)), 1)

    def test_bot_home_without_readable_identity_is_not_hidden(self) -> None:
        missing = self.bot_home("atelier", None)
        self.write("sessions/a.json", {"pid": 1, "cwd": missing, "status": "idle"})
        bots, _ = self.bots({"id-1"})
        with patch.object(sp, "process_info", return_value=(1, "90")):
            self.assertEqual(len(sp.claude_sessions(self.root, bots=bots)), 1)

    def test_path_escaping_the_bot_root_is_not_a_bot(self) -> None:
        home = self.bot_home("atelier", "id-1")
        bots, _ = self.bots({"id-1"})
        self.assertTrue(bots.hides(home + "/subdir"))
        self.assertFalse(bots.hides(home + "/../../../elsewhere"))
        self.assertFalse(bots.hides(str(self.root / ".orca/bots")))

    def test_paused_bot_codex_rollout_is_hidden(self) -> None:
        home = self.bot_home("atelier", "id-1")
        path = self.root / "rollout.jsonl"
        meta = {"type": "session_meta", "payload": {"id": "s", "cwd": home, "source": "cli"}}
        path.write_text(json.dumps(meta) + "\n" + json.dumps({"type": "event_msg", "payload": {"type": "task_started"}}) + "\n")
        bots, _ = self.bots({"id-1"})
        found = sp.RolloutReader().collect(self.root, now=time.time(), opened={path: (123, "90")}, bots=bots)
        self.assertEqual(found, [])

    def test_orca_paused_ids_parse_cli_json(self) -> None:
        payload = {"ok": True, "result": {"bots": [
            {"id": "a", "paused": True}, {"id": "b", "paused": False}, {"id": 7, "paused": True}, "junk"]}}
        done = subprocess.CompletedProcess([], 0, stdout=json.dumps(payload).encode())
        with patch.object(sp, "orca_commands", return_value=[["orca-cli"]]), \
                patch.object(sp.subprocess, "run", return_value=done) as run:
            self.assertEqual(sp.orca_paused_ids(), {"a"})
        self.assertEqual(run.call_args.args[0], ["orca-cli", "bot", "list", "--json"])
        self.assertIs(run.call_args.kwargs.get("shell", False), False)

    def test_orca_paused_ids_is_none_on_any_failure(self) -> None:
        good = json.dumps({"result": {"bots": []}}).encode()
        cases = [
            ("no cli", [], None),
            ("exit 1", [["x"]], subprocess.CompletedProcess([], 1, stdout=good)),
            ("bad json", [["x"]], subprocess.CompletedProcess([], 0, stdout=b"{nope")),
            ("wrong shape", [["x"]], subprocess.CompletedProcess([], 0, stdout=b"[]")),
            ("no bots key", [["x"]], subprocess.CompletedProcess([], 0, stdout=b'{"result":{}}')),
            ("oversized", [["x"]], subprocess.CompletedProcess([], 0, stdout=b" " * (sp.MAX_ORCA_OUTPUT + 1))),
            ("timeout", [["x"]], subprocess.TimeoutExpired("x", 1)),
            ("oserror", [["x"]], OSError("gone")),
        ]
        for name, commands, outcome in cases:
            with self.subTest(name), patch.object(sp, "orca_commands", return_value=commands), \
                    patch.object(sp.subprocess, "run", side_effect=[outcome] if isinstance(outcome, BaseException) else None,
                                 return_value=outcome):
                self.assertIsNone(sp.orca_paused_ids())

    def test_labels_strip_control_characters_and_sensitive_values(self) -> None:
        text = sp.label("Build\n\x1b test@example.org /home/example/private sk-abcdefghijklmnop")
        self.assertNotIn("@", text)
        self.assertNotIn("/home", text)
        self.assertNotIn("sk-", text)
        self.assertNotIn("\x1b", text)


if __name__ == "__main__":
    unittest.main()

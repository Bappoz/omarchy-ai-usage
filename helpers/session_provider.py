#!/usr/bin/env python3
"""Read local agent lifecycle metadata; never export transcript content.

Claude publishes a pid registry. Codex lifecycle events are read from bounded,
cached rollout tails, with open descriptors keeping long-running turns live.
Only same-user processes are inspected. No hooks, logins or inference are run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

MAX_SESSIONS = 64
TAIL_BYTES = 1024 * 1024
HEAD_BYTES = 32 * 1024
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
SENSITIVE = re.compile(r"(?:bearer\s+\S+|sk-[\w-]{12,}|[\w.+-]+@[\w.-]+\.[a-z]{2,})", re.IGNORECASE)


def label(value: object, fallback: str = "Session") -> str:
    if not isinstance(value, str):
        return fallback
    text = SENSITIVE.sub("[redacted]", CONTROL.sub(" ", value))
    text = re.sub(r"/(?:home|Users)/\S+", "[path]", text)
    return " ".join(text.split())[:80] or fallback


def process_info(pid: int, proc: Path = Path("/proc")) -> tuple[int, str] | None:
    """Return parent and birth ticks; reject stale, foreign and stopped pids."""
    try:
        directory = proc / str(pid)
        if pid <= 0 or directory.stat().st_uid != os.getuid():
            return None
        fields = (directory / "stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] in {"Z", "T", "t", "X"}:
            return None
        return int(fields[1]), fields[19]
    except (OSError, ValueError, IndexError):
        return None


def regular_json(path: Path) -> dict[str, Any] | None:
    try:
        if path.is_symlink() or not path.is_file() or path.stat().st_size > HEAD_BYTES:
            return None
        value = json.loads(path.read_bytes())
        return value if isinstance(value, dict) else None
    except (OSError, ValueError):
        return None


def session(provider: str, key: str, state: str, name: str, detail: str,
            *, pid: int | None = None, started: str | None = None) -> dict[str, Any]:
    return {
        "id": hashlib.sha256((provider + ":" + key).encode()).hexdigest()[:24],
        "providerId": provider, "state": state,
        "name": label(name), "detail": label(detail, provider.title()),
        "waitingFor": "Permission or input required" if state == "waiting" else None,
        "pid": pid, "started": started,
    }


class ClaudeTranscripts:
    def __init__(self) -> None:
        self.cache: dict[Path, tuple[tuple[int, int, int], tuple[str, str | None]]] = {}

    def read(self, config: Path, record: dict[str, Any]) -> tuple[str, str | None]:
        session_id, cwd = record.get("sessionId"), record.get("cwd")
        if not isinstance(session_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", session_id) or not isinstance(cwd, str):
            return "unknown", None
        path = config / "projects" / cwd.replace("/", "-").replace(".", "-") / (session_id + ".jsonl")
        try:
            if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
                return "unknown", None
            stat = path.stat()
            stamp = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
            if path in self.cache and self.cache[path][0] == stamp:
                return self.cache[path][1]
            with path.open("rb") as handle:
                handle.seek(max(0, stat.st_size - 64 * 1024))
                tail = handle.read(64 * 1024)
            state, title, renamed = "unknown", None, False
            for line in reversed(tail.splitlines()):
                try:
                    value = json.loads(line)
                    if not isinstance(value, dict) or value.get("isSidechain") is True:
                        continue
                    kind = value.get("type")
                    if kind == "custom-title" and not renamed:
                        title, renamed = label(value.get("customTitle")), True
                    elif kind == "ai-title" and title is None:
                        title = label(value.get("aiTitle"))
                    if state != "unknown":
                        continue
                    message = value.get("message")
                    if not isinstance(message, dict):
                        continue
                    if kind == "assistant":
                        reason = message.get("stop_reason")
                        state = "idle" if reason in {"end_turn", "stop_sequence", "max_tokens"} else "busy"
                    elif kind == "user":
                        content = message.get("content")
                        interrupted = isinstance(content, str) and content.startswith("[Request interrupted by user")
                        state = "idle" if interrupted else "busy"
                except (ValueError, TypeError):
                    continue
            if len(self.cache) >= MAX_SESSIONS:
                self.cache.pop(next(iter(self.cache)))
            self.cache[path] = (stamp, (state, title))
            return state, title
        except OSError:
            return "unknown", None


def claude_sessions(config: Path, proc: Path = Path("/proc"),
                    transcripts: ClaudeTranscripts | None = None) -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    directory = config / "sessions"
    try:
        paths = sorted(directory.glob("*.json"))[:MAX_SESSIONS * 2]
    except OSError:
        return []
    for path in paths:
        record = regular_json(path)
        pid = record.get("pid") if record else None
        if not isinstance(pid, int) or isinstance(pid, bool) or not isinstance(record.get("cwd"), str):
            continue
        info = process_info(pid, proc)
        if info is None:
            continue
        # A recycled pid must not inherit an old registry's activity.
        started_at = record.get("startedAt")
        if isinstance(started_at, (int, float)) and proc == Path("/proc"):
            try:
                boot = time.time() - float((proc / "uptime").read_text().split()[0])
                birth = boot + int(info[1]) / os.sysconf("SC_CLK_TCK")
                if abs(birth - started_at / 1000) > 10:
                    continue
            except (OSError, ValueError):
                continue
        raw = record.get("tempo") or record.get("status")
        if not isinstance(raw, str):
            raw = ""
        state = {"blocked": "waiting", "waiting": "waiting", "active": "busy",
                 "busy": "busy", "idle": "idle"}.get(raw, "unknown")
        title = None
        if transcripts and (state == "unknown" or record.get("nameSource") in (None, "derived")):
            inferred, title = transcripts.read(config, record)
            if state == "unknown":
                state = inferred
        # An unknown registry state is not evidence of completion.
        folder = Path(str(record.get("cwd") or "Claude")).name
        entry = record.get("entrypoint")
        surface = "VS Code" if entry == "claude-vscode" else "Desktop" if entry == "claude-desktop" else "Terminal"
        key = str(record.get("sessionId") or pid)
        name = record.get("name") or folder
        if title and record.get("nameSource") in (None, "derived"):
            name = title
        found[key] = session("claude", key, state, name,
                             surface + " · " + folder, pid=pid, started=info[1])
    return list(found.values())[:MAX_SESSIONS]


def open_rollouts(root: Path, proc: Path = Path("/proc")) -> dict[Path, tuple[int, str]]:
    found: dict[Path, tuple[int, str]] = {}
    try:
        processes = proc.iterdir()
        for directory in processes:
            if not directory.name.isdigit():
                continue
            try:
                if directory.stat().st_uid != os.getuid():
                    continue
                if (directory / "comm").read_text().strip() not in {"codex", "codex-cli"}:
                    continue
                info = process_info(int(directory.name), proc)
                if info is None:
                    continue
                for fd in (directory / "fd").iterdir():
                    try:
                        target = Path(os.readlink(fd))
                        if target.suffix == ".jsonl" and target.is_relative_to(root):
                            found[target] = (int(directory.name), info[1])
                    except OSError:
                        continue
            except OSError:
                continue
    except OSError:
        pass
    return found


class RolloutReader:
    def __init__(self) -> None:
        self.cache: dict[Path, tuple[tuple[int, int, int], dict[str, Any]]] = {}

    def read(self, path: Path) -> dict[str, Any] | None:
        try:
            if path.is_symlink() or not path.is_file():
                return None
            stat = path.stat()
            stamp = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
            if path in self.cache and self.cache[path][0] == stamp:
                return self.cache[path][1]
            with path.open("rb") as handle:
                head = handle.read(HEAD_BYTES)
                offset = max(0, stat.st_size - TAIL_BYTES)
                handle.seek(offset)
                tail = handle.read(TAIL_BYTES)
            if offset:
                tail = tail.partition(b"\n")[2]
            meta: dict[str, Any] = {}
            for line in head.splitlines():
                try:
                    record = json.loads(line)
                    if record.get("type") == "session_meta":
                        meta = record.get("payload") or {}
                        break
                except (ValueError, AttributeError):
                    continue
            state = "unknown"
            answered: set[str] = set()
            for line in reversed(tail.splitlines()):
                try:
                    record = json.loads(line)
                    payload = record.get("payload")
                    if record.get("type") == "response_item" and isinstance(payload, dict):
                        call_id = payload.get("call_id")
                        if isinstance(call_id, str):
                            if payload.get("type") == "function_call_output":
                                answered.add(call_id)
                            elif payload.get("type") == "function_call" and payload.get("name") == "request_user_input" and call_id not in answered:
                                state = "waiting"
                                break
                    if record.get("type") != "event_msg" or not isinstance(payload, dict):
                        continue
                    event = payload.get("type")
                    if not isinstance(event, str):
                        continue
                    if event in {"task_complete", "turn_aborted"}:
                        state = "success" if event == "task_complete" else "idle"
                        break
                    if event == "task_started":
                        state = "busy"
                        break
                    # Item completion (a single tool) never completes a turn.
                except (ValueError, AttributeError):
                    continue
            value = {"state": state, "meta": meta}
            self.cache[path] = (stamp, value)
            return value
        except OSError:
            return None

    def collect(self, root: Path, *, now: float | None = None,
                opened: dict[Path, tuple[int, str]] | None = None) -> list[dict[str, Any]]:
        now = time.time() if now is None else now
        opened = open_rollouts(root) if opened is None else opened
        candidates = set(opened)
        # Only today's and yesterday's partitions, never a recursive history scan.
        for day in (now, now - 86400):
            directory = root / time.strftime("%Y/%m/%d", time.gmtime(day))
            try:
                for path in directory.glob("*.jsonl"):
                    if path.stat().st_mtime >= now - 30:
                        candidates.add(path)
            except OSError:
                continue
        found = []
        for path in sorted(candidates)[:MAX_SESSIONS]:
            value = self.read(path)
            if value is None:
                continue
            state, meta = value["state"], value["meta"]
            if not isinstance(meta, dict):
                continue
            # A sub-agent completing is not its parent conversation completing.
            source = meta.get("source")
            if isinstance(source, dict) and "subagent" in source:
                continue
            pid, started = opened.get(path, (None, None))
            if path not in opened and state in {"busy", "unknown"}:
                # Recent writes show work, but do not infer completion from age.
                try:
                    if now - path.stat().st_mtime > 8:
                        continue
                except OSError:
                    continue
            folder = Path(str(meta.get("cwd") or "Codex")).name
            found.append(session("codex", str(meta.get("id") or path.name), state,
                                 folder, "Codex · " + folder, pid=pid, started=started))
        self.cache = {path: cached for path, cached in self.cache.items() if path in candidates}
        return found


def focus_session(pid: int, started: str) -> bool:
    """Raise the owning Hyprland client, verifying pid identity before use."""
    info = process_info(pid)
    if info is None or info[1] != started:
        return False
    ancestors = set()
    for _ in range(64):
        if pid in ancestors or pid <= 1:
            break
        ancestors.add(pid)
        info = process_info(pid)
        if info is None:
            break
        pid = info[0]
    try:
        result = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True,
                                timeout=2, check=True)
        if len(result.stdout) > 1024 * 1024:
            return False
        clients = json.loads(result.stdout)
        for client in clients:
            address = client.get("address", "")
            if client.get("pid") in ancestors and re.fullmatch(r"0x[0-9a-fA-F]+", address):
                subprocess.run(["hyprctl", "dispatch", "focuswindow", "address:" + address],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=2, check=True)
                return True
    except (OSError, ValueError, subprocess.SubprocessError, AttributeError, TypeError):
        pass
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--providers", default="claude,codex")
    parser.add_argument("--focus", type=int)
    parser.add_argument("--started", default="")
    args = parser.parse_args()
    if args.focus is not None:
        return 0 if focus_session(args.focus, args.started) else 1
    providers = set(args.providers.split(","))
    if not providers <= {"claude", "codex"}:
        parser.error("unsupported provider")
    reader = RolloutReader()
    transcripts = ClaudeTranscripts()
    claude = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")
    codex = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex") / "sessions"
    previous = ""
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True:
        sessions = []
        if "claude" in providers:
            sessions.extend(claude_sessions(claude, transcripts=transcripts))
        if "codex" in providers:
            sessions.extend(reader.collect(codex))
        doc = json.dumps({"schemaVersion": 1, "sessions": sessions}, separators=(",", ":"))
        if doc != previous:
            print(doc, flush=True)
            previous = doc
        if not args.watch:
            break
        time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

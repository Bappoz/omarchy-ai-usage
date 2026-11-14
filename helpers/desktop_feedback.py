#!/usr/bin/env python3
"""Fixed, bounded desktop alerts; accepts no arbitrary command or sound path."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

PROVIDERS = {"claude": "Claude", "codex": "Codex", "antigravity": "Antigravity", "cursor": "Cursor"}
SOUNDS = {"complete": "complete", "bell": "bell", "message": "message-new-instant"}


def play(sound: str) -> None:
    event = SOUNDS[sound]
    if shutil.which("canberra-gtk-play"):
        command = ["canberra-gtk-play", "-i", event]
    else:
        path = Path("/usr/share/sounds/freedesktop/stereo") / (event + ".oga")
        if not path.is_file() or not shutil.which("pw-play"):
            return
        command = ["pw-play", str(path)]
    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=PROVIDERS, default="claude")
    parser.add_argument("--event", choices=("finished", "blocked", "80", "100", "preview"), required=True)
    parser.add_argument("--sound", choices=SOUNDS)
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()
    try:
        if args.notify and args.event != "preview" and shutil.which("notify-send"):
            body = {"finished": "Agent finished working.", "blocked": "Agent needs permission or input.",
                    "80": "80% of the current usage window has been used.",
                    "100": "The current usage limit has been reached."}[args.event]
            subprocess.run(["notify-send", "--app-name=Omarchy AI Usage", "--expire-time=5000",
                            "--", PROVIDERS[args.provider], body],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3, check=False)
        if args.sound:
            play(args.sound)
    except (OSError, subprocess.SubprocessError):
        pass  # Missing audio/notification services must not affect the notch.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

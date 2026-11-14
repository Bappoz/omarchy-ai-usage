"""Optional native QML smoke check (requires Quickshell and Qt 6)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    executable = shutil.which("quickshell")
    if executable is None:
        print("Quickshell is required for the native smoke check.")
        return 1
    with tempfile.TemporaryDirectory(prefix="ai-usage-qml-") as directory:
        root = Path(__file__).resolve().parents[1]
        shutil.copytree(root / "src", Path(directory) / "src")
        config = Path(directory) / "shell.qml"
        source = (root / "tests/qml/smoke.qml").read_text().replace("../../src/", "./src/")
        config.write_text(source)
        env = {**os.environ, "XDG_RUNTIME_DIR": directory, "QT_QPA_PLATFORM": "offscreen",
               "QT_QPA_PLATFORMTHEME": "basic", "QT_QUICK_CONTROLS_STYLE": "Basic",
               "QT_QUICK_BACKEND": "software"}
        env.pop("WAYLAND_DISPLAY", None)
        result = subprocess.run([executable, "-p", str(config), "--no-color"],
                                env=env, capture_output=True, text=True, timeout=15, check=False)
        output = result.stdout + result.stderr
        if result.returncode or "SMOKE_OK:" not in output or "SMOKE_FAIL:" in output or "TypeError:" in output or "ReferenceError:" in output:
            print(output)
            return 1
        print("Native QML smoke check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

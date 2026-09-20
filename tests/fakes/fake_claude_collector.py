#!/usr/bin/env python3
import json
import os
import sys
import time

scenario = os.environ.get("FAKE_CLAUDE_SCENARIO", "active")
if scenario == "timeout":
    time.sleep(2)
elif scenario == "malformed":
    sys.stdout.write("not-json")
elif scenario == "failure":
    raise SystemExit(1)
elif scenario == "auth":
    print(json.dumps({"id": "claude", "ready": False, "usageStatusText": "Waiting for auth", "limits": []}))
elif scenario == "stale":
    print(json.dumps({"id": "claude", "ready": True, "tierLabel": "Pro", "usageStatusText": "Claude limits unavailable", "retryAdvised": True, "limits": [{"label": "Session (5-hour)", "percent": 0.20, "resetsAt": "2030-01-01T17:00:00Z"}]}))
else:
    print(json.dumps({"schemaVersion": 1, "id": "claude", "name": "Claude Code", "ready": True, "tierLabel": "Pro", "usageStatusText": "", "limits": [{"label": "Session (5-hour)", "percent": 0.25, "resetsAt": "2030-01-01T17:00:00Z"}, {"label": "Weekly (7-day)", "percent": 0.40, "resetsAt": "2030-01-08T12:00:00Z"}]}))

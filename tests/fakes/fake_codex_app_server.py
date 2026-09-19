#!/usr/bin/env python3
"""Synthetic JSON-lines app-server used by provider tests."""

from __future__ import annotations

import json
import os
import sys
import time

SCENARIO = os.environ.get("FAKE_CODEX_SCENARIO", "success_multi")


def respond(request_id: int, result: dict) -> None:
    print(json.dumps({"id": request_id, "result": result}), flush=True)


for raw in sys.stdin:
    request = json.loads(raw)
    if "id" not in request:
        continue
    request_id = request["id"]
    method = request.get("method")

    if SCENARIO == "malformed":
        print("not-json", flush=True)
        raise SystemExit(0)
    if SCENARIO == "oversized":
        sys.stdout.write("x" * 2048)
        sys.stdout.flush()
        continue
    if SCENARIO == "launcher_noise":
        print("synthetic launcher status", flush=True)
    if SCENARIO == "timeout":
        time.sleep(10)
        continue
    if method == "initialize":
        respond(request_id, {"serverInfo": {"name": "fake", "version": "1"}})
    elif method == "account/read":
        if SCENARIO == "needs_auth":
            respond(request_id, {"account": None, "requiresOpenaiAuth": True})
        else:
            respond(
                request_id,
                {
                    "account": {
                        "type": "chatgpt",
                        "email": "fixture@example.invalid",
                        "planType": "plus",
                    },
                    "requiresOpenaiAuth": True,
                },
            )
    elif method == "account/rateLimits/read":
        if SCENARIO == "rpc_error":
            print(
                json.dumps(
                    {
                        "id": request_id,
                        "error": {
                            "code": -32000,
                            "message": "SENSITIVE_MARKER must never escape",
                        },
                    }
                ),
                flush=True,
            )
        elif SCENARIO == "legacy":
            respond(
                request_id,
                {
                    "rateLimits": {
                        "limitId": "codex",
                        "limitName": None,
                        "planType": "plus",
                        "primary": {
                            "usedPercent": 10,
                            "windowDurationMins": 300,
                            "resetsAt": 1893456000,
                        },
                        "secondary": None,
                        "rateLimitReachedType": None,
                    }
                },
            )
        elif SCENARIO == "invalid_percent":
            respond(
                request_id,
                {
                    "rateLimits": {
                        "limitId": "codex",
                        "primary": {"usedPercent": 140},
                        "secondary": None,
                    }
                },
            )
        else:
            respond(
                request_id,
                {
                    "rateLimits": {
                        "limitId": "legacy",
                        "primary": {"usedPercent": 99},
                        "secondary": None,
                    },
                    "rateLimitsByLimitId": {
                        "codex": {
                            "limitId": "codex",
                            "limitName": None,
                            "planType": "plus",
                            "primary": {
                                "usedPercent": 25,
                                "windowDurationMins": 300,
                                "resetsAt": 1893456000,
                            },
                            "secondary": {
                                "usedPercent": 40,
                                "windowDurationMins": 10080,
                                "resetsAt": None,
                            },
                            "rateLimitReachedType": None,
                        },
                        "codex_other": {
                            "limitId": "codex_other",
                            "limitName": "Other models",
                            "primary": {
                                "usedPercent": 5,
                                "windowDurationMins": 60,
                                "resetsAt": None,
                            },
                            "secondary": None,
                            "rateLimitReachedType": None,
                        },
                    },
                    "ordinaryUsageAllowed": True,
                },
            )

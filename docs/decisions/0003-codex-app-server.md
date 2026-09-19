# ADR 0003: Delegate Codex authentication to app-server

- Status: accepted and implemented
- Date: 2026-09-19

## Context

Quota data requires an authenticated Codex context. Reading local credential files or calling a private ChatGPT endpoint would expand the security boundary and couple the plugin to internal formats.

## Decision

Start the installed Codex app-server for each refresh with read-only sandboxing and approval-on-request. Use the documented account and rate-limit JSON-RPC methods, normalize only approved fields, then terminate the process.

Do not force token refresh, initiate login, read credential files, expose account email or ID, or retain raw protocol output.

## Consequences

- Codex owns authentication storage and renewal.
- Each refresh has process-start overhead but leaves no idle helper process.
- The CLI still labels app-server experimental, so protocol parsing must remain isolated and fixture-tested.
- API-key-only and other accounts without ChatGPT quota windows degrade to `UNAVAILABLE` rather than fabricated data.
- The QML layer can consume one stable provider contract regardless of protocol changes.

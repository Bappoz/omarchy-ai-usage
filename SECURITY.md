# Security policy

## Supported versions

The project is pre-release. Security fixes apply to the latest revision only.

## Reporting a vulnerability

When this project is published, use the repository's private security-advisory feature. Do not include credentials, cookies, authorization headers, or complete provider responses in an issue, screenshot, fixture, or log excerpt.

## Security boundary

Omarchy shell plugins are not sandboxed. QML and any child process run with the desktop user's permissions. This project therefore follows a narrow data-access model:

- delegate collection and authentication entirely to the built-in `omarchy.agents` widget;
- never read, copy, persist, or display credential files or bearer tokens;
- accept only normalized provider data at the UI boundary;
- never read or log raw provider responses;
- sanitize user-visible and diagnostic errors;
- persist only non-secret preferences;
- use the Python standard library to validate bounded, local records;
- keep providers isolated so one failure cannot terminate the other providers or UI.

The runtime does not execute `claude`, `codex`, or `omarchy-agent-usage-update`. It reads only the schema-version-1 records written atomically by `omarchy.agents`:

```text
$XDG_STATE_HOME/omarchy/agents/usage/claude.json
$XDG_STATE_HOME/omarchy/agents/usage/codex.json
```

Each record must be a regular non-symlink file no larger than 1 MiB, use schema version 1, and match the requested provider ID. Only a validated plan label, usage windows, percentages, reset times, status, and update time cross the UI boundary. Raw responses, email addresses, account IDs, credentials, and reset-credit identifiers are never copied into plugin state.

Common bearer-token, API-key, JWT, email, home-path, and control-character patterns have a tested redaction function for any future diagnostics. Current runtime failures use static messages and do not include exception or server text.

## Test data

All committed fixtures must be synthetic. The tests reject token-like values and sensitive key names. Real CLI output must not be committed, even if it appears harmless.

## Runtime behavior

The QML service watches each enabled provider record and runs a short-lived local normalizer after an atomic replacement. The default 15-minute adaptive timer remains only as a fallback for missed file events. Transient failures use bounded exponential backoff; signed-out state waits at least one hour; explicit rate-limited state waits until the normal interval or the earliest reported reset, whichever is longer (capped at six hours). Concurrent requests for the same provider collapse into one follow-up read, and display count does not create extra pollers.

The service does not initiate login, read credential files, make direct HTTP requests, or start provider clients. QML consumes helper stderr without logging it and replaces malformed stdout with a static error message. Preferences contain only non-secret presentation and scheduling values and are persisted through Omarchy's plugin-scoped `shell.json` API.

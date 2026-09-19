# Security policy

## Supported versions

The project is pre-release. Security fixes apply to the latest revision only.

## Reporting a vulnerability

When this project is published, use the repository's private security-advisory feature. Do not include credentials, cookies, authorization headers, or complete provider responses in an issue, screenshot, fixture, or log excerpt.

## Security boundary

Omarchy shell plugins are not sandboxed. QML and any child process run with the desktop user's permissions. This project therefore follows a narrow data-access model:

- delegate Codex authentication and token refresh to the installed Codex process;
- never read, copy, persist, or display credential files or bearer tokens;
- accept only normalized provider data at the UI boundary;
- never log raw JSON-RPC responses;
- sanitize user-visible and diagnostic errors;
- persist only last-known-good normalized snapshots and non-secret preferences;
- use the Python standard library and fixed subprocess argument lists;
- enforce timeouts and bounded output during provider execution;
- keep providers isolated so one failure cannot terminate the other providers or UI.

The Codex helper starts a fixed argument vector without a shell:

```text
codex --sandbox read-only --ask-for-approval on-request app-server --listen stdio://
```

It sends only `initialize`, `initialized`, `account/read` with token refresh disabled, and `account/rateLimits/read`. Standard error is discarded rather than risk logging an unredacted provider diagnostic. Standard output is bounded to 1 MiB for the entire refresh and the default whole-refresh deadline is 12 seconds.

Successful normalized snapshots are stored in `$XDG_STATE_HOME/omarchy-ai-usage/codex-last-good.json`, or the equivalent path below `~/.local/state` when `XDG_STATE_HOME` is unset. Writes use a same-directory temporary file, `fsync`, atomic replacement, and mode `0600`. Raw RPC messages, email addresses, account IDs, credentials, and reset-credit identifiers are not cached.

Common bearer-token, API-key, JWT, email, home-path, and control-character patterns have a tested redaction function for any future diagnostics. Current runtime failures use static messages and do not include exception or server text.

## Test data

All committed fixtures must be synthetic. The tests reject token-like values and sensitive key names. Real CLI output must not be committed, even if it appears harmless.

## Runtime behavior

The QML service starts the helper at startup and on one global adaptive schedule. The default healthy interval is 15 minutes. Transient failures use bounded exponential backoff; signed-out state waits at least one hour; explicit rate-limited state waits until the normal interval or the earliest reported reset, whichever is longer (capped at six hours). Concurrent requests collapse into one follow-up refresh, and display count does not create extra pollers.

The service does not initiate login, read credential files, make direct HTTP requests, or keep the helper alive after the bounded refresh. QML consumes child stderr without logging it and replaces malformed stdout with a static error message. Preferences contain only non-secret presentation and scheduling values and are persisted through Omarchy's plugin-scoped `shell.json` API.

# Security policy

## Supported versions

The project is pre-release. Security fixes apply to the latest revision only.

## Reporting a vulnerability

When this project is published, use the repository's private security-advisory feature. Do not include credentials, cookies, authorization headers, or complete provider responses in an issue, screenshot, fixture, or log excerpt.

## Security boundary

Omarchy shell plugins are not sandboxed. QML and any child process run with the desktop user's permissions. This project therefore follows a narrow data-access model:

- delegate Claude/Codex collection and authentication to `omarchy.agents`; Antigravity quota comes from Antigravity's own local language server or official `agy` CLI (existing sign-in); Cursor quota uses Orca's local CLI and existing sign-in;
- never read, copy, persist, or display credential files or bearer tokens (the single, narrow exception is Antigravity's loopback CSRF token, described below);
- accept only normalized provider data at the UI boundary;
- never read or log raw provider responses;
- sanitize user-visible and diagnostic errors;
- persist only non-secret preferences;
- use the Python standard library to validate bounded, local records;
- keep providers isolated so one failure cannot terminate the other providers or UI.

For Claude and Codex, the runtime reads only the schema-version-1 records written atomically by `omarchy.agents`:

```text
$XDG_STATE_HOME/omarchy/agents/usage/claude.json
$XDG_STATE_HOME/omarchy/agents/usage/codex.json
```

For Antigravity, `helpers/antigravity_provider.py` does not require Orca. It tries, in order:

1. **Local language server bridge.** It scans `/proc` for same-user `language_server` or `agy --hub` processes, reads the `--csrf_token` value from that process's command line, finds its listening TCP ports through `/proc/<pid>/fd` and `/proc/net/tcp{,6}`, and sends one `RetrieveUserQuotaSummary` request to `https://127.0.0.1:<port>`. Certificate verification is relaxed only for this loopback request because the server uses a self-signed certificate. The CSRF token stays in memory for that request and is never stored, printed, or sent anywhere other than 127.0.0.1.
2. **Official `agy` CLI.** If no server answers, it runs `agy --print /usage` in a bounded pseudo-terminal (15-second timeout, 64 KiB output cap, `AGY_CLI_DISABLE_AUTO_UPDATE=true`, process group killed on timeout). The CLI uses its own sign-in; the plugin passes no credentials.
3. **Orca fallback.** If Orca happens to be available, its `account list --json` result is used. Orca is optional.
4. **Last known reading.** A private (`0600`, directory `0700`) sanitized snapshot under `$XDG_CACHE_HOME/omarchy-ai-usage/` is reused for 5 minutes to avoid spawning the CLI repeatedly, and is shown as `STALE` (up to 7 days) after transient failures.

Only quota percentages, reset times and window labels reach the UI. Raw responses and CLI output are never printed or stored.

For Cursor, the helper runs Orca's app-scoped `account list --json` command. It does not read Cursor's credential store, pass credentials or prompts, stores only a short-lived sanitized quota snapshot in the user's cache, and does not print the raw CLI response. Gemini is not displayed as a separate provider.

To hide sessions of paused Orca bots, the session helper also runs Orca's `bot list --json` (only when a session lives under `~/.orca/bots/`) and reads each bot home's `bot.json` id. Only bot ids and their paused flag are used; the output is not stored or printed, and an unavailable Orca hides nothing.

**Insights panel exception.** The activity panel beside the card (opt out with `showInsights: false`) reads beyond the `omarchy.agents` records. While it is visible, `helpers/insights_provider.py` streams, read-only, the local session logs `~/.claude/projects/**/*.jsonl` and `~/.codex/sessions/**/*.jsonl` (honoring `CLAUDE_CONFIG_DIR` and `CODEX_HOME`). These logs contain conversations, so the helper keeps only a timestamp, a model name, an effort label, and token counts per request, and prints aggregates (24 hourly totals, per-model totals). Prompts, tool output, file paths, and session identifiers never leave that helper, and a test asserts that conversation text does not appear in its output. It considers only regular non-symlink files modified in the last seven days (at most 500 files, 256 MiB each) and runs single-flight with a 15-second cooldown.

**Live-session exception.** `helpers/session_provider.py` is one shared, read-only process with a two-second cadence. It reads at most 128 small Claude registry candidates (32 KiB each), emits at most 64 Claude sessions, and verifies same-user live/non-stopped processes. Registry status is authoritative. Without a known status it reads a cached 64 KiB transcript tail at the cwd-derived path. Codex reads the latest 1 MiB and first 32 KiB of at most 64 rollouts, caching by inode, size and nanosecond mtime; discovery uses same-user Codex open descriptors and recent files in today's/yesterday's partitions. Only turn lifecycle or an unanswered input-request marker determines state; a tool/item finishing does not finish a task. Known helper rollouts are excluded. No hooks or configuration are installed into agent clients.

The session UI receives a hashed handle, sanitized name/title, workspace basename, generic surface label/state, generic permission/input request, pid and process birth ticks. No prompt, answer, reasoning, tool argument/output, raw session id, full cwd or credential is emitted or persisted. Explicit/generated session titles can contain user text, so they are displayed locally after control-character, common credential/email and home-path redaction. Turning off `showSessions` stops this watcher; turning off `showInsights` separately stops token aggregation requests.

Session focus is click-only: the helper validates pid plus birth ticks, walks same-user live ancestors, reads `hyprctl clients -j` and focuses a matching, validated hexadecimal client address. It does not read process command lines, environments, terminal text or scripts. Desktop notifications use fixed provider names and static event text; sound selection is an allowlist of freedesktop event names. Neither passes a user-supplied command or sound path to a shell. Notification/audio subprocesses have short timeouts and a bounded UI queue. These effects run once globally, not once per monitor.

Clicking a provider logo launches the matching desktop app when available or opens the provider web app. Neither command receives user-controlled arguments.

When a live card is visible, the plugin may invoke the fixed command
`omarchy-shell omarchy.agents refresh`. This is an IPC request to the built-in
owner; it does not pass user-controlled arguments, access credentials, or
create a second collector. Requests are single-flight and rate-limited.

Each record must be a regular non-symlink file no larger than 1 MiB, use schema version 1, and match the requested provider ID. Only a validated plan label, usage windows, percentages, reset times, status, and update time cross the UI boundary. Raw responses, email addresses, account IDs, credentials, and reset-credit identifiers are never copied into plugin state.

Common bearer-token, API-key, JWT, email, home-path, and control-character patterns have a tested redaction function for any future diagnostics. Current runtime failures use static messages and do not include exception or server text.

## Test data

All committed fixtures must be synthetic. The tests reject token-like values and sensitive key names. Real CLI output must not be committed, even if it appears harmless.

## Runtime behavior

The QML service watches each enabled provider record and runs a short-lived local normalizer after an atomic replacement. The default 15-minute adaptive timer remains only as a fallback for missed file events. A visible card requests official collection every 30 seconds through IPC, with a 15-second cooldown and single-flight collapse. Transient failures use bounded exponential backoff; signed-out state waits at least one hour; explicit rate-limited state waits until the normal interval or the earliest reported reset, whichever is longer (capped at six hours). Concurrent requests for the same provider collapse into one follow-up read, and display count does not create extra provider readers.

The service does not initiate login or read credential files. Its only direct HTTP request is the Antigravity loopback call above, and the only provider client it starts is the official `agy` CLI for a quota report. QML consumes helper stderr without logging it and replaces malformed stdout with a static error message. Preferences contain only non-secret presentation and scheduling values and are persisted through Omarchy's plugin-scoped `shell.json` API.

**Desktop reactions.** With `autoHideMode` set to `onFullscreen` or `onOverlap`, `DesktopMonitor` listens to Hyprland events and runs the fixed command `hyprctl activewindow -j` (debounced, single-flight). Only the active window's fullscreen flag, position and size are used, in memory. Window titles, classes and contents are ignored. `never` stops this entirely.

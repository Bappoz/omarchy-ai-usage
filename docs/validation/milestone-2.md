# Milestone 2 validation — Codex provider

Date: 2026-09-19
Codex CLI exercised: 0.154.0
Result: passed

## Automated checks

- 29 unit and contract tests passed with resource warnings promoted to errors.
- Ruff reported no Python lint errors.
- Omarchy accepted the plugin manifest.
- `qmllint` accepted the intentionally inert service entry point.
- Every repository JSON file parsed successfully.
- No symlinks are present in the distributable tree.

Covered behavior includes:

- multi-bucket preference and legacy fallback;
- explicit headline-window selection;
- auth-required, active, rate-limited, unavailable, error, and stale behavior;
- rejection of malformed percentages rather than clamping;
- RPC errors without server-message disclosure;
- whole-refresh timeout and total-output limits;
- bounded launcher-noise tolerance;
- descriptor cleanup after every child process;
- synthetic redaction of bearer, API-key, JWT, email, and home-path patterns;
- atomic cache mode `0600`;
- rejection of corrupt, malformed, expired, future-dated, and symlinked cache input;
- contract validity for all emitted states.

## Live probe

A single live probe used the installed Codex app-server and a temporary cache directory. Only a privacy-safe projection was retained:

- process exit: 0;
- provider status: `ACTIVE`;
- normalized window count: 1;
- explicit headline: present;
- contract: valid;
- identity pattern: absent;
- token pattern: absent;
- cache mode: `0600`;
- elapsed time: 1.36 seconds.

No percentages, account plan, email, account ID, raw RPC response, credential file, or token was printed or saved in the repository.

## Degradation probe

After a successful live refresh, the Codex executable was deliberately made unavailable for a second refresh using the same temporary cache. The helper:

- exited normally;
- returned `STALE`;
- preserved the normalized window;
- preserved the original successful timestamp;
- did not expose the process error.

## Defect found and fixed

The first live probe returned `ERROR` during `initialize`. A privacy-safe diagnostic showed that the local executable launcher writes one non-JSON status line before the valid app-server response. No content from that line was displayed.

The client was updated to discard at most 16 non-JSON lines while retaining the 1 MiB total-output cap and whole-refresh deadline. Discarded content is never logged. A regression test now covers this launcher behavior, and the repeated live probe passed.

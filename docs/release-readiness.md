# Release readiness

Version 0.8.0 completes the repository's pre-marketplace engineering scope.

## Completed gates

- valid schema-version-1 Omarchy service manifest;
- live Claude Code and Codex support through existing authenticated sessions;
- no symlinks, vendored runtimes, or network-fetched UI assets;
- isolated provider schedules with timeouts, output caps, backoff, and private stale fallback;
- plugin-scoped persisted preferences with in-card provider switches;
- reduced-motion override and keyboard accessibility metadata;
- synthetic fixtures only, with secret-like fields rejected in tests;
- MIT license, third-party attribution, root preview, CI, and removal instructions;
- local QML, Python, contract, and official Omarchy validation.

## Before a public tag

1. Run `make check` on the clean tagged tree under the target Omarchy release.
2. Install from the public Git URL on a disposable or secondary profile.
3. Exercise both providers, settings, all four edges, offline, signed-out, and stale-cache states.
4. Confirm screenshots contain no account identity or real provider payload.
5. Tag `v0.8.0` and attach the validation result to the release notes.

The marketplace submission flow is documented in [Marketplace publishing](marketplace-publishing.md). Submission remains an explicit repository-owner action because it creates a public issue for maintainer review.

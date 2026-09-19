# Release readiness

Version 0.7.0 completes the pre-marketplace engineering scope. It is suitable for daily testing and publication as an open-source repository.

## Completed gates

- official schema-version-1 Omarchy service manifest;
- no symlinks, vendored runtimes, or network-fetched UI assets;
- one global provider store and poll scheduler across all displays;
- timeout, output cap, retry backoff, rate-limit delay, and last-good fallback;
- plugin-scoped persisted preferences with bounded normalization;
- reduced-motion override and keyboard accessibility metadata;
- synthetic fixtures only, with secret-like fields rejected in tests;
- MIT license plus pinned third-party attribution;
- portable CI and local QML/platform validation;
- documentation for configuration, architecture, security, contribution, and release changes.

## Before a public tag

1. Run `make check` on the clean tagged tree under the target Omarchy release.
2. Install from the public Git URL on a disposable or secondary profile.
3. Exercise hover, click, always-open, all four edges, reconnect, scale, offline, signed-out, and stale-cache scenarios.
4. Confirm the screenshot still contains only synthetic preview data.
5. Tag `v0.7.0` and attach the validation output to the release notes.

Marketplace packaging, listing metadata, submission, and review are intentionally not performed or prepared here; they begin only after the owner accepts the daily-use test.

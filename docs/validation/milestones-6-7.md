# Milestones 6–7 validation — preferences and release hardening

Validated on the installed Omarchy/Quickshell environment before any marketplace work.

## Automated gate

- 53 unit and contract tests pass.
- Ruff reports no Python issues.
- Every QML source passes `qmllint`.
- `omarchy plugin validate .` accepts manifest schema 1 at version 0.7.0.
- The repository contains no symlinks or real provider fixtures.

## Runtime gate

- Synthetic three-provider preview loaded in Quickshell with the expanded CodeNotch surface on the right edge.
- Live QML mode loaded successfully and the Codex helper returned `ACTIVE`, non-stale data.
- The provider helper reported one normalized live window without exposing account data in validation output.
- No QML binding, component, or provider errors remained after the preference-store scope fix.
- Standalone Quickshell emitted only compositor/host diagnostics: the known proxy-window size deprecation and duplicate desktop-portal registration. Neither diagnostic came from provider parsing or plugin state.
- All temporary plugin preview processes were stopped after inspection; the installed Omarchy shell remained untouched.

## Scope boundary

No plugin installation, user configuration edit, repository publication, marketplace metadata, marketplace submission, or marketplace integration was performed.

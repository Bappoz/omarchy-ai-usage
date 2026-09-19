# Architecture

## Goals

- Look and behave like a native Omarchy surface.
- Keep provider acquisition separate from presentation.
- Continue rendering other providers when one fails.
- Preserve a last-known-good snapshot and communicate staleness honestly.
- Poll once globally, regardless of the number of displays.
- Avoid direct credential access and unnecessary dependencies.

## Runtime boundaries

```text
Codex process
    │ documented JSON-RPC
    ▼
Codex provider adapter
    │ validated provider snapshot
    ▼
Provider store and last-good cache
    │ provider-neutral state
    ├───────────────┬───────────────┐
    ▼               ▼               ▼
screen surface  screen surface  screen surface
```

The UI consumes only snapshots conforming to `contracts/provider-snapshot.schema.json`. It does not parse Claude or Codex responses or infer missing provider fields.

## Provider snapshot invariants

- `schemaVersion` makes persisted records migratable.
- `providerId` and window IDs are stable machine identifiers; labels are presentation strings.
- `headlineWindowId` is explicit and must reference a present window.
- Percentages are nullable. When both used and remaining are present, they must total 100 within rounding tolerance.
- Reset time and window duration are independently nullable.
- `fidelity` records whether a value is official, derived, or manually supplied.
- `STALE` is explicit, retains last-known-good windows, and requires `stale: true`.
- Provider messages are short, sanitized, user-safe summaries—not raw diagnostics.

## Current process model

The Omarchy service owns one full-screen, input-masked layer surface for each selected display. The surface creates no exclusive zone, requests no keyboard focus, and accepts pointer input only over the visible notch or expanded card. A single `ProviderStore` owns one bounded runner per enabled provider, validates provider-neutral snapshots, and shares them with every display delegate.

The store is a singleton. Each provider refreshes at startup, on manual request, and through its own one-shot adaptive timer; display delegates never start provider processes. A request that arrives during the same provider's refresh becomes one pending follow-up rather than a second process. Healthy state uses the configured interval, transient failures back off exponentially, authentication waits at least an hour, and explicit rate limiting honors the earliest reported reset within a bounded six-hour delay.

Placement is represented as an edge, normalized offset, and screen selector. `Variants` tracks the selected live `Quickshell.screens`. Focused scope follows Hyprland focus, named scope restores the requested connector after reconnect, and all scope creates one view per output. A fixed-size screen surface prevents stale-buffer scaling during notch expansion; a union input region keeps the transparent remainder click-through.

The Codex adapter exchanges bounded JSON-RPC messages with `codex app-server`. The Claude adapter invokes Omarchy's authenticated `omarchy-agent-usage-claude --limits-only` collector. Both are short-lived standard-library helpers with deadlines, output caps, fixed process arguments, static failure messages, private caches, and deterministic cleanup.

QML consumes only helper stdout and never logs provider output or stderr. A malformed snapshot becomes a static `ERROR` state without disrupting other providers. Synthetic multi-provider data can be selected only through `OMARCHY_AI_USAGE_PREVIEW=1`, and its expanded card visibly labels that mode. Normal operation renders only provider snapshots backed by real adapters.

## Persistence

- Configuration: the plugin's inline entry in `~/.config/omarchy/shell.json`, written by Omarchy's scoped plugin facade.
- Last-good state: `$XDG_STATE_HOME/omarchy-ai-usage/`, falling back to `~/.local/state/omarchy-ai-usage/`.

The service watches `shell.json`, extracts only its own entry, validates every field, and applies safe defaults when the file is missing or malformed. It never writes the file directly: changes from the in-card settings surface go through `shell.updateEntryInline`, which is scoped by the host to this plugin ID.

## Dependencies

The intended runtime is QML/Quickshell plus a Python standard-library provider helper. No third-party Python or JavaScript packages are planned.

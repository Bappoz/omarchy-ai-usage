# Configuration

Preferences are stored as fields on the `ai-usage.notch` entry inside Omarchy's `~/.config/omarchy/shell.json`. The plugin reads that file reactively and writes through the scoped `shell.updateEntryInline` API; it does not create a competing configuration store.

The in-card settings control covers the common choices. The normalized configuration shape is:

```json
{
  "id": "ai-usage.notch",
  "settingsVersion": 1,
  "edge": "right",
  "offset": 0.5,
  "monitor": "focused",
  "size": "medium",
  "autoHide": true,
  "expandBehavior": "hover",
  "pollingInterval": 900,
  "showProviderLabel": false,
  "showPercentage": true,
  "showResetTimer": true,
  "animations": true,
  "enabledProviders": { "claude": true, "codex": true }
}
```

## Values

- `edge`: `top`, `right`, `bottom`, or `left`.
- `offset`: any number from `0.0` to `1.0` along the selected edge.
- `monitor`: `focused`, `all`, or an exact live connector name. A missing connector temporarily falls back to the focused display and is restored when it reconnects.
- `size`: `small`, `medium`, or `large`.
- `autoHide`: when true, the full rail collapses back to its edge pill.
- `expandBehavior`: `hover` or `click`. With `autoHide: false`, the provider rail remains open.
- `pollingInterval`: seconds, clamped to 60–3600; the UI offers 5, 15, 30, and 60 minutes.
- `showProviderLabel`, `showPercentage`, `showResetTimer`, `animations`: boolean presentation choices.
- `enabledProviders.claude` and `enabledProviders.codex`: provider switches also exposed in the card. The UI keeps at least one enabled.

Malformed, missing, and out-of-range values fall back to safe defaults. Unknown fields are discarded when the plugin next writes its normalized preferences. `settingsVersion` reserves an explicit migration point for future releases.

## Test-only overrides

Environment variables override placement for the current shell process without changing persisted preferences:

- `OMARCHY_AI_USAGE_EDGE`
- `OMARCHY_AI_USAGE_OFFSET`
- `OMARCHY_AI_USAGE_SCREEN`
- `OMARCHY_AI_USAGE_PREVIEW=1`
- `OMARCHY_AI_USAGE_EXPANDED=1`
- `OMARCHY_REDUCED_MOTION=1`

These are intended for development, screenshots, and accessibility testing rather than daily configuration.

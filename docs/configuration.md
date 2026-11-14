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
  "accentColor": "auto",
  "showInsights": true,
  "showSessions": true,
  "busyIndicator": "arc",
  "peekOnEvent": true,
  "peekDuration": 5,
  "sessionSounds": true,
  "sessionNotifications": false,
  "finishedSound": "complete",
  "waitingSound": "bell",
  "quotaAlerts": true,
  "mutedAlerts": {},
  "resetTimeStyle": "remaining",
  "providerOrder": ["claude", "codex", "antigravity", "cursor"],
  "edgeOffsets": { "top": 0.5, "right": 0.5, "bottom": 0.5, "left": 0.5 },
  "enabledProviders": { "claude": true, "codex": true, "antigravity": true, "cursor": true },
  "providerColors": { "claude": "auto", "codex": "auto", "antigravity": "auto", "cursor": "auto" }
}
```

## Values

- `edge`: `top`, `right`, `bottom`, or `left`.
- `offset`: any number from `0.0` to `1.0` along the selected edge.
- `monitor`: `focused`, `all`, or an exact live connector name. A missing connector temporarily falls back to the focused display and is restored when it reconnects.
- `size`: `small`, `medium`, or `large`.
- `autoHide`: when true, the full rail collapses back to its edge pill.
- `expandBehavior`: `hover` or `click`. With `autoHide: false`, the provider rail remains open.
- `pollingInterval`: seconds, clamped to 60–3600; the UI offers 5, 15, 30, and 60 minutes. This is the hidden fallback reread. A visible card asks `omarchy.agents` for fresh records when opened and every 30 seconds, with a 15-second request cooldown.
- `showProviderLabel`, `showPercentage`, `showResetTimer`, `animations`: boolean presentation choices. New configurations show percentages below the rings. Explicit existing label/color choices are preserved.
- `accentColor`: `auto` (green/yellow/orange by usage) or any `#RRGGBB` hex, used when a provider has no specific color. Provider colors override it. General settings offers presets and a validated hex input. Invalid values fall back to `auto`.
- `showInsights`: show the activity panel beside an open provider card. It reads aggregates of local session logs only while visible; see `SECURITY.md`.
- `enabledProviders.claude`, `codex`, `antigravity`, and `cursor`: provider switches also exposed in the card. The UI keeps at least one enabled.
- `providerColors`: optional `#RRGGBB` colors for each provider. These color the ring, quota bars, and activity accent. Use `"auto"` to inherit the global accent. The settings card cycles through presets; any hex can be entered in `shell.json`.
- `showSessions`: enables the one global two-second local lifecycle watcher. Turning it off stops that process and clears the session display. Independent of the token insights panel.
- `busyIndicator`: `arc` or `breath`. Working is white for the arc, brand-colored for the breathing disc; waiting remains amber. Reduced motion stops continuous animation.
- `peekOnEvent`: automatically unfold for an observed busy → finished/waiting transition. `peekDuration`: exactly `3`, `5` or `10` seconds. Pointer hover and Keep open can keep the surface visible afterward.
- `sessionSounds`: sound on observed completion or waiting. `finishedSound` / `waitingSound`: `complete`, `bell` or `message`. Preview buttons deliberately play the selected sound even if automatic sounds are off. Uses installed freedesktop events via canberra or PipeWire; missing players/events produce no error popup.
- `sessionNotifications`: optional desktop messages for those transitions; off by default. `quotaAlerts`: desktop alerts at 80% and 100%, on by default. `mutedAlerts`: provider-to-boolean map for quota alerts only. Each crossing latches until the source publishes a later reset boundary after the old one elapsed. Startup readings never alert.
- `resetTimeStyle`: `remaining` or `date`. The countdown uses a one-second visible clock. A reset with no date can only retain the source's fallback text.
- `providerOrder`: a deduplicated list of the four provider IDs. Missing IDs are appended. Accounts settings offers up/down controls; switching a disabled provider back on moves it to the end.
- `edgeOffsets`: saved position per edge. Changing `edge` saves the old `offset` and restores the new edge's remembered position. Alt-drag and the General slider apply continuously.

Malformed, missing, and out-of-range values fall back to safe defaults. Unknown fields are discarded when the plugin next writes its normalized preferences. `settingsVersion` reserves an explicit migration point for future releases.

The visible cadence is intentionally bounded. Thirty-second refreshes make the
card feel current without a permanent sub-second loop; they can wake provider
clients and use network/battery while the card is open. Hidden surfaces keep
the slower configured fallback and still react immediately to record changes.
An observed busy session also requests fresh quota every 30 seconds, even when
the card is hidden. Session completion/waiting requests one refresh. All use the
same shared collector, single-flight logic and cooldown; monitors do not multiply
collection. See [CodeNotch comparison](codenotch-parity.md) for source limitations.

On the maintainer's Omarchy workstation on 2026-09-22, one native Claude
limits-only collection took 0.79 seconds of wall time (0.40 seconds user CPU,
0.09 seconds system CPU), while a full IPC request replaced the watched Claude
record in about 5.1 seconds. These are point measurements, not guarantees; the
network and provider can dominate latency. A 30-second visible cadence therefore
prioritizes responsiveness without keeping a sub-second process loop alive.

## Test-only overrides

Environment variables override placement for the current shell process without changing persisted preferences:

- `OMARCHY_AI_USAGE_EDGE`
- `OMARCHY_AI_USAGE_OFFSET`
- `OMARCHY_AI_USAGE_SCREEN`
- `OMARCHY_AI_USAGE_PREVIEW=1`
- `OMARCHY_AI_USAGE_EXPANDED=1`
- `OMARCHY_REDUCED_MOTION=1`

These are intended for development, screenshots, and accessibility testing rather than daily configuration.

# Placement and screen scope

## Model

Placement has three independent values:

```json
{
  "edge": "right",
  "offset": 0.5,
  "screen": "focused"
}
```

- `edge` controls which physical screen edge the notch joins.
- `offset` is clamped to `0.0`–`1.0` along that edge and accounts for the notch's own extent, so both endpoints remain visible.
- `screen` is `focused`, `all`, or an exact connector name.

The expanded card is clamped to the display while its pointer follows the compact notch. Moving to either end therefore never pushes details off-screen or disconnects the visual relationship between both surfaces.

## Screen behavior

- `focused` reacts to Hyprland's focused monitor and moves the view without starting another provider process.
- A connector name targets that display while it exists.
- If a named display disappears, the focused display is used as a safe fallback.
- Because selection is derived from the live screen list, reconnecting the requested connector restores it automatically.
- `all` creates one presentation delegate per live screen. Every delegate reads the same provider store.

The layer windows cover their output to make arbitrary normalized positioning stable and avoid resize artifacts. Their input masks contain only the notch and open detail card, leaving the rest of the desktop click-through.

The right edge is the default because it is the reference CodeNotch composition. Top, bottom, and left preserve the same one-dimensional layout: side edges stack providers vertically, while horizontal edges place them side by side.

## Temporary runtime controls

Version 0.7.0 persists this model on the plugin's own `shell.json` entry. `OMARCHY_AI_USAGE_EDGE`, `OMARCHY_AI_USAGE_OFFSET`, and `OMARCHY_AI_USAGE_SCREEN` remain temporary development overrides and do not mutate stored preferences.

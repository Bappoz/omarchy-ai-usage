# Compact surface

## Geometry

The medium layout is derived from CodeNotch's design frame, anchored by its 44 px ring diameter.

- Default edge: right
- Side-body depth: 70 px
- Ring diameter: 44 px
- Resting handle: approximately 10 × 79 px
- Side-edge layout: vertical provider stack
- Top/bottom layout: horizontal provider row
- Exclusive zone: none
- Layer: overlay
- Keyboard focus: none
- Namespace: `ai-usage-notch`

The body uses one canonical right-edge path and transforms it onto left, top, or bottom. This keeps the inverse flares and inner corners consistent on every orientation.

## Interaction

At rest the surface is a small black handle attached to the selected edge. Reaching its enlarged input target unfolds the full provider rail. Hovering a provider opens its details; a 250 ms grace window allows the pointer to cross the small gap into the tooltip without closing it.

Clicking a real provider ring requests a refresh for that provider. Clicking unused notch space holds or releases the open state. The full-screen layer remains click-through outside the dynamic notch, tooltip, and narrow pointer bridge.

## Usage semantics

The ring, compact label, detailed bars, and detailed labels all show percent used. The UI consumes explicit `usedPercent` when available and only derives it as `100 - remainingPercent` when the normalized provider window supplies the complementary value.

Unknown values render as an em dash and a neutral track. Stale data remains visible but dimmed. Errors never invent a percentage.

## Preview

Normal startup shows enabled live providers—Claude and Codex by default. `OMARCHY_AI_USAGE_PREVIEW=1` is an explicit visual test mode that renders the reference trio—Claude 73%, Codex 21%, and Perplexity 52%—and marks the expanded card `PREVIEW`.

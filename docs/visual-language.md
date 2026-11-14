# Visual language

## Reference fidelity

Milestone 5 now treats CodeNotch revision `ec1a7e3fc0634f668741cb0357029420bdd4281c` as the visual source of truth. The QML implementation preserves the reference's proportions and behavior while retaining the Omarchy-specific layer-shell, display, and provider architecture.

- pure-black notch and tooltip with no border;
- a 70 px side body around 44 px provider rings at medium scale;
- inverse rounded ends that weld the surface to the physical screen edge;
- white primary text, `#808080` secondary text, `#303030` ring tracks, and `#2D2D2D` bar tracks;
- green `#00FF88` below 50% used, yellow `#F2FF00` from 50%, and orange `#FF3F00` from 70% by default; `accentColor` replaces this scale with one chosen `#RRGGBB`;
- Claude, OpenAI/Codex, and Perplexity provider marks;
- one black tooltip with a curved, welded pointer and linear quota rows;
- compact and detailed readings consistently expressed as percent used.

The latest product direction intentionally replaces the earlier adaptive-glass experiment. Omarchy still owns placement, output lifecycle, scaling, and input behavior; the surface itself stays visually faithful to CodeNotch instead of recoloring with the active theme.

## Motion

The motion vocabulary follows the reference rather than using unrelated fades:

- the resting handle unfolds and folds with a lightly damped spring, following the current reference's fluid shape movement;
- cells enter toward the desktop with a 45 ms stagger;
- the tooltip has a 250 ms hover grace period so the pointer can cross the gap;
- the same tooltip travels between provider cells with a damped spring;
- ring and bar readings settle to new measurements with a lightly overshooting spring (Sileo-inspired) instead of a fixed-duration ease;
- the card enters with a spring scale and its quota rows rise in a 60 ms stagger.

Version 0.12 adds the current reference's white working arc, optional brand-color breathing disc, amber waiting pulse, settings orb and event peek. Percentages and the usage threshold palette are the default for new configurations; explicitly saved provider colors are retained. See [the reference comparison](codenotch-parity.md) for exact scope.

At rest, the expanded geometry folds into a small black handle. The provider cells remain laid out at their final positions and are revealed by the opening silhouette, avoiding reflow during animation.

## Data honesty

The normal service renders live Claude and Codex snapshots. Perplexity appears only when `OMARCHY_AI_USAGE_PREVIEW=1` is explicitly enabled; the tooltip labels that state `PREVIEW`. Reference percentages are never used as a live fallback.

The provider contract continues to keep both `usedPercent` and `remainingPercent` explicit. Presentation now uses `usedPercent` everywhere to match CodeNotch without changing or weakening the normalized data boundary.

## License boundary

The shape measurements, thresholds, motion timing, and interaction model are adapted from CodeNotch under its MIT license. Provider marks are redistributed under their upstream licenses. See [Acknowledgements](acknowledgements.md) and the repository's `THIRD_PARTY_NOTICES.md`.

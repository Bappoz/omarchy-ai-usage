# Live provider surface

## Milestone 4 scope

This slice connects the already validated Codex helper to the Omarchy QML service and adds the first detail view. It does not add periodic polling, multi-monitor placement, user configuration, installation automation, or another provider.

## Refresh lifecycle

1. `ProviderStore` starts in `LOADING` and launches `helpers/codex_provider.py` without a shell.
2. The helper owns Codex JSON-RPC, cache policy, deadlines, output bounds, and normalization.
3. QML parses and defensively checks the normalized version-1 snapshot.
4. Valid data replaces the loading state. Invalid output becomes a static `ERROR` snapshot without logging the child output.
5. The user may request another refresh from the expanded card. A refresh already in flight is not duplicated.

There is deliberately no `Timer` in the service yet. Refresh scheduling, retry cadence, and freshness policy belong to a later milestone and should be introduced only once the live interaction is approved.

## Interaction

Clicking the compact notch expands a card attached beneath it. Clicking the notch again collapses the card. The surface remains on the overlay layer, reserves no screen space, and requests no keyboard focus.

The expanded card shows:

- provider and plan labels when available;
- explicit provider status;
- every quota window returned by the provider, with bounded scrolling for long lists;
- remaining percentage and reset time without inventing missing values;
- last-updated time and an explicit stale marker;
- a manual refresh action.

The compact view remains present for every state. When no usage window exists, it shows loading, sign-in, error, or unavailable copy instead of hiding or displaying a fabricated percentage.

## Preview mode

`OMARCHY_AI_USAGE_PREVIEW=1` selects synthetic Claude, Codex, and Perplexity readings matching the visual reference. The expanded card displays `PREVIEW`. The flag is off by default and is not a fallback for provider failures. Normal startup shows only the real Codex provider; no unavailable provider percentage is fabricated.

# Changelog

## Unreleased

- Hide live sessions that belong to a paused Orca bot (an agent running in `~/.orca/bots/<name>`, matched through the id in its `bot.json`); they return once the bot is resumed. Orca's `bot list --json` is queried lazily, cached for 10 seconds, and any failure hides nothing.
- Remove settings controls from individual provider cards; use one general settings orb outside the trailing flare. Morph the black arc into the black gear disc on hover and reverse on leave, with click rotation and a dedicated input region.
- Always show percentages on compact cells, overriding legacy name/hidden-percent preferences, and restore CodeNotch cap-height proportions.
- Share a curvature-ramped flare between the notch silhouette and its parallel settings arc; reserve room for the external orb on all four edges.

## 0.12.0

- Port CodeNotch session interaction: a white working arc (or optional breathing disc), amber waiting ring, completion state, per-session details and a configurable 3/5/10-second peek. Claude uses its process registry with a cached transcript fallback; Codex uses cached bounded rollout tails and live process descriptors.
- Focus the owning Hyprland application from a session row or event peek, validating process identity before following its ancestors. A regular ring click refreshes usage; the card's provider mark still opens its app.
- Add independent session sounds, sound selection and previews, optional desktop session notifications and per-provider quota alerts at 80% and 100%. Initial readings, disappearing sessions, malformed records and answered questions do not announce completion; quota alerts latch until an observed window rollover.
- Refresh quota every 30 seconds while an observed session is busy, with the existing shared-owner IPC cooldown and single-flight protection.
- Add the settings orb, right-click Keep open / Refresh now menu, live Alt-drag positioning, per-edge remembered offsets, provider order and re-enable-at-end behavior.
- Split settings into General, Accounts, Activity and Alerts. Add a continuous position slider, actual monitor choices, custom hex input, reset-date/countdown modes and independent live-session monitoring.
- Use a true one-second reset countdown, percent labels and threshold colors for new configurations, fluid spring unfolding/gliding and scale-correct edge geometry. Existing explicit colors remain intact.
- Render the Claude brand tint directly in SVG, avoiding a shader pass and keeping the mark visible with Qt's software renderer.
- Add behavioral transition, liveness, privacy, focus, rollover and native QML smoke checks. Record remaining upstream gaps in `docs/codenotch-parity.md`; this is not a claim of complete CodeNotch parity.

## 0.11.0

- Fix provider rings appearing before the edge handle finished unfolding: they now fade in only once the silhouette is fully open, and each ring sweeps in from empty on every open.
- Add an activity panel that opens beside a provider card: current model (with a live indicator), a 24-hour token sparkline with hover readout, 24h/7d totals, and per-model share. Data comes from aggregates of local Claude Code and Codex session logs (see `SECURITY.md`); toggle with `showInsights`.
- Clicking a provider logo (rail or card header) opens the app: Claude Desktop or ChatGPT, falling back to the web app. Clicking no longer triggers a refresh; opening the card already does.
- Give the opt-in preview synthetic activity data.
- Rewrite the README with a feature overview, gallery (screenshots and an animation), data-source table, and corrected privacy notes; refresh `preview.png`.

## 0.10.0

- Add `accentColor` (`auto` or any `#RRGGBB`) to recolor rings and bars, with an in-card preset selector.
- Show a pace marker on every quota bar and a burn-rate verdict per window, derived only from the reset time and window length already in the provider contract.
- Add a status badge to the card header for stale, rate-limited, sign-in, and error states.
- Replace the eased ring/bar sweep and card entrance with Sileo-inspired springs and a staggered row entrance; reduced-motion and the Motion toggle still disable them.
- Give the opt-in preview data relative reset times so the new readings can be exercised.

## 0.9.0

- Make compact Claude usage follow the shortest recognized window instead of whichever window has the highest percentage.
- Request fresh records through the built-in `omarchy.agents` IPC on card open and every 30 seconds while visible, with single-flight and cooldown protection.
- Document the current safe-source feasibility results for Copilot, Gemini CLI, and Perplexity rather than exposing fabricated live percentages.
- Keep weekly and other longer quota windows available in the expanded card.

## 0.8.1

- Use the schema-version-1 records maintained by `omarchy.agents` as the only live source for Claude and Codex.
- Watch shared record changes so the notch follows official updates immediately.
- Remove provider CLI and usage-updater execution from the notch runtime.
- Keep OmaPkDex and the notch as independent read-only consumers of the same official records.

## 0.8.0

- Add live Claude Code usage through Omarchy's authenticated collector.
- Auto-enable Claude and Codex, with no-code provider switches in the in-card settings.
- Isolate polling, retries, and stale fallback per provider so one failure does not hide the other.
- Replace the settings emoji with a local animated vector control.
- Add marketplace-ready preview and installation, update, removal, and submission guidance.

## 0.7.0

- Add native persisted preferences for placement, displays, size, behavior, polling, labels, reset times, and motion.
- Add in-card settings while preserving the CodeNotch visual surface.
- Add one global adaptive poll scheduler with single-flight refresh, exponential failure backoff, authentication delay, and reset-aware rate-limit delay.
- Add small, medium, and large size tokens plus hover, click, and always-open modes.
- Add reduced-motion support and expanded accessibility metadata.
- Complete release, security, configuration, and pre-publication documentation.

## 0.5.0

- Match the pinned CodeNotch visual reference and add all-edge, offset, and multi-display placement.

## 0.4.0

- Connect the expanded surface to live normalized Codex data.

## 0.3.0

- Add the compact layer-shell surface and synthetic preview fixtures.

## 0.2.0

- Add the bounded Codex provider, normalized contract, and private last-good cache.

## 0.1.0

- Establish the Omarchy service plugin structure and architecture contracts.

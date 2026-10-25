# Changelog

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

# Changelog

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

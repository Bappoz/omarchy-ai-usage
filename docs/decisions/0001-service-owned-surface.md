# ADR 0001: Use a service-owned edge surface

- Status: accepted for implementation planning
- Date: 2026-09-19

## Context

Omarchy's bar-widget host supplies settings and placement inside the bar. The requested product must attach independently to any screen edge and must not consume bar space. A panel or overlay is normally summoned rather than continuously present.

## Decision

Declare a third-party `service` entry point. In the visual milestone, that service will own reactive per-screen layer-shell windows and a single shared provider store.

The service will not set `keepLoaded` initially. Normal plugin hot reload is more valuable during development, and no authentication or lock-screen invariant requires it to survive reload.

## Consequences

- Independent edge placement is possible.
- Multi-monitor windows can share one poller.
- Official bar-widget settings injection is unavailable.
- Preferences require a small plugin-owned persistence adapter until Omarchy exposes service settings.
- The third-party QML executes with user permissions and must be treated as trusted local code.

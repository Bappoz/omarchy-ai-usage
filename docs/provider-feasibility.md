# Provider feasibility

Last reviewed: 2026-10-29.

Live providers must expose a stable, authenticated and machine-readable quota
window with both consumption and a ceiling/reset. Omarchy AI Usage does not
read credential files, browser storage or private web endpoints, and it does
not turn token counts into invented quota percentages. Claude and Codex come
from `omarchy.agents`; Antigravity and Cursor quota windows are read from Orca's
local `account list --json` interface. Gemini is not shown as a separate
provider card.

The installed Omarchy release currently ships official usage collectors for
Claude, Codex and Fireworks. The plugin also uses Orca's local quota interface
for Antigravity and Cursor.
The following candidates remain unavailable.

## GitHub Copilot

GitHub documents billing endpoints for personal, organization and enterprise
Copilot usage. The personal premium-request report returns consumed request
quantities, but its documented response does not include the plan allowance,
remaining quota or reset timestamp needed for an honest percentage. It also
does not cover seats billed through an organization or enterprise. The Copilot
CLI has no documented quota-report command, and `omarchy.agents` does not ship
a Copilot collector.

Source: [GitHub billing usage REST API](https://docs.github.com/en/rest/billing/usage).

Decision: do not add a partial percentage or depend on undocumented Copilot
endpoints. Revisit when GitHub or `omarchy.agents` exposes entitlement plus
usage and reset semantics.

## Gemini CLI and Antigravity

Google's consumer Gemini CLI sign-in has been retired for individual accounts;
the CLI now directs users to Antigravity. The old browser authorization page
may list Gemini CLI as an authorized product, but that does not restore access
through the retired client. This plugin does not reuse Gemini CLI credentials.
The plugin intentionally does not show a separate Gemini card. The Antigravity
card remains the only Google quota surface in this plugin.

Source: [Google's transition announcement](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/).

Decision: do not show a separate Gemini provider. The Antigravity card uses
the quota windows Orca reports for the Antigravity account. The legacy Gemini
CLI may continue to offer API-key or Vertex AI modes, but those do not provide
this subscription quota view.

## Cursor

Cursor quota windows are read from Orca's local account listing. The plugin
does not read Cursor credentials or call undocumented Cursor endpoints.
Per-request token totals are not shown because there is no supported local
session-log source in this integration.

Source: [Orca usage tracking](https://www.onorca.dev/docs/agents/usage-tracking).

## Perplexity

Perplexity documents separate consumer subscriptions and API billing. Consumer
plans use daily, weekly and monthly feature limits, while API access requires
separately purchased credits. No official machine-readable API for the signed-
in consumer quota and resets is documented. API balance is therefore not an
honest substitute for Pro/Max application usage, and the browser's private
rate-limit endpoint is outside the supported contract. `omarchy.agents` does
not ship a Perplexity collector.

Sources: [Perplexity plan comparison](https://www.perplexity.ai/help-center/en/articles/11187416-which-perplexity-subscription-plan-is-right-for-you)
and [Enterprise pricing and API separation](https://www.perplexity.ai/help-center/en/articles/10352986-enterprise-pricing-and-billing-frequently-asked-questions).

Decision: keep Perplexity only in the clearly labeled synthetic preview. Do
not scrape browser sessions or present API credits as consumer quota.

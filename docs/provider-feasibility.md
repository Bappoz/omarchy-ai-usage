# Provider feasibility

Last reviewed: 2026-09-22.

Live providers must expose a stable, authenticated and machine-readable quota
window with both consumption and a ceiling/reset. Omarchy AI Usage does not
read credential files, browser storage or private web endpoints, and it does
not turn token counts into invented quota percentages. Collection remains
owned by `omarchy.agents`; this plugin consumes its schema-version-1 records.

The installed Omarchy release currently ships official usage collectors for
Claude, Codex and Fireworks. This plugin displays Claude and Codex. The
following candidates were investigated and deliberately remain unavailable.

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

## Gemini CLI

Gemini CLI documents `/stats model` as an interactive view containing session
token counts and quota information. Its documented headless JSON output reports
statistics for the new command being executed; it is not a read-only account
quota query. Starting a prompt merely to obtain stats would itself consume
quota. Google also explicitly prohibits third-party software from reusing the
Gemini CLI OAuth backend. `omarchy.agents` does not ship a Gemini collector.

Sources: [Gemini CLI commands](https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/commands.md),
[headless mode](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/headless.md), and
[terms and privacy](https://github.com/google-gemini/gemini-cli/blob/main/docs/resources/tos-privacy.md).

Decision: do not automate the interactive terminal or access the private OAuth
backend. Revisit when Gemini CLI publishes a non-consuming structured quota
command or Omarchy adds a collector.

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

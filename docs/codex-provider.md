# Codex provider

## Protocol choice

The provider uses the documented [Codex app-server](https://learn.chatgpt.com/docs/app-server) over JSON lines on standard input/output. It relies on the installed Codex process to own authentication and token refresh.

The helper performs this sequence within one deadline:

1. `initialize` with a minimal client identity and no experimental API opt-in;
2. `initialized` notification;
3. `account/read` with `refreshToken: false`;
4. `account/rateLimits/read` when authentication is usable;
5. normalize, optionally cache, emit one JSON object, and terminate.

It intentionally does not call `account/usage/read` yet. The version-1 UI contract models quota windows, not lifetime token analytics. Adding unrelated fields before the expanded-view requirements are approved would weaken the provider boundary.

Some executable launchers emit a status line before handing control to Codex. The client silently discards at most 16 non-JSON lines while still enforcing the 1 MiB total-output cap and whole-refresh deadline. Discarded text is never logged or included in provider output.

## Mapping rules

- Prefer `rateLimitsByLimitId` when it is a non-empty object.
- Fall back to the backward-compatible `rateLimits` object.
- Convert every available primary and secondary window independently.
- Keep `usedPercent` as the official value and derive its arithmetic complement for `remainingPercent`.
- Convert positive Unix `resetsAt` seconds to UTC ISO 8601.
- Keep missing reset times and durations as `null`.
- Select `codex` primary as the headline; otherwise use the first primary, then the first available window.
- Report `RATE_LIMITED` only from explicit backend state: `rateLimitReachedType`, `spendControlReached`, or `ordinaryUsageAllowed: false`.
- Never infer a blocked account merely because a percentage is 100.
- Reject malformed percentages instead of clamping or fabricating them.
- Preserve plan type when available, but discard email, account ID, credits, reset-credit identifiers, and raw messages.

## Failure and cache policy

- A missing account that requires OpenAI authentication becomes `NEEDS_AUTH` and does not revive an old cache entry.
- A valid response without ChatGPT quota windows becomes `UNAVAILABLE`.
- RPC, timeout, protocol, and invalid-data failures become `ERROR`.
- `ERROR` and `UNAVAILABLE` may fall back to a valid last-good snapshot no older than seven days; the returned state becomes `STALE` and retains the original update time.
- Corrupt, oversized, future-dated, expired, symlinked, wrong-provider, wrong-version, or non-success cache records are ignored.
- Cache write failure never hides fresh provider data.

The app-server CLI remains marked experimental even though these account methods are officially documented. All protocol knowledge is isolated in `helpers/codex_provider.py` and exercised with a synthetic server, so a future protocol change does not require provider parsing inside QML.

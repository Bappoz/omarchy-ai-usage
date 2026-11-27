# CodeNotch comparison

Reference: [CodeNotch 1.25.0, 835550a](https://github.com/vinzdg/codenotch/tree/835550a342871779135b6484d6899161c5222f7c). The geometry already originated in the earlier `ec1a7e3` revision. This implementation targets **Omarchy/Quickshell on Hyprland**, not the MATE desktop. A numerical fidelity percentage would require a defined acceptance suite and comparison on actual desktops; none is claimed here.

## Interaction and appearance

| Reference behavior | Linux implementation | Boundary |
| --- | --- | --- |
| Pure black, curved edge attachment, four edges, usage rings and welded tooltip | Implemented | Geometry is native Qt Quick Shapes; scaling now includes edge corners |
| Smooth unfold, staggered cells, reading sweeps, tooltip glide | Implemented with QML springs | SwiftUI and Qt use different spring solvers; timings are perceptual equivalents |
| Busy arc and optional breathing disc | Implemented | Only actual observed session state drives it; recent token use alone does not imply busy |
| Amber waiting ring | Implemented | Claude registry blocked/waiting; Codex unanswered `request_user_input` only |
| Per-session state, name and application context | Implemented for Claude/Codex | Claude registry/custom title; Codex workspace name, not full conversation title; no raw prompts or answers |
| Peek on completion/waiting | Implemented, 3/5/10 seconds | Only busy → idle/success/waiting announces; no first-reading or disappearance announcements |
| Click peek or session to raise its application | Implemented via Hyprland process ancestry | Requires a live published/discovered pid; no arbitrary terminal-tab scripting |
| Separate sounds and peek controls, sound previews | Implemented | Uses installed freedesktop sound events and canberra or PipeWire; missing services fail quietly |
| 80% and 100% quota notifications, provider mute | Implemented | Headline window only; no startup alert, no duplicate on fluctuations; rearmed on observed reset rollover |
| Ring click refresh; app mark in tooltip opens app | Implemented | Existing single-flight/cooldown remains in force |
| Keep open, context menu, settings orb | Implemented | Orb uses the existing settings vector |
| Move along edge and remember each edge | Implemented | Alt-drag, continuous slider; monitor selection includes actual live connectors |
| Reorder providers, re-enabled provider joins end | Implemented | Four existing quota providers; ordering controls use up/down buttons |
| Countdown/date reset formats | Implemented | Clock updates once a second while visible; fallback reset text only when no date exists |
| Configurable colors, size, open behavior, reduced motion | Implemented | New configurations use usage thresholds; existing explicit colors are preserved |
| Token sparkline, totals, per-model distribution | Existing, retained | Claude/Codex local aggregates; a busy light now reflects session state rather than a 15-minute age heuristic |

## Differences that remain

| Reference capability | Current status and reason |
| --- | --- |
| Financial credits, reset grants and account balances | Not available from the supported `omarchy.agents` quota record. Token counts are not a price or credit balance. No fabricated amount or redemption action is shown. |
| Cursor/Antigravity live session state | Antigravity quota is read directly (language server or `agy` CLI); Cursor quota remains through Orca. Live session metadata is not implemented for either. The card explicitly says so. |
| Additional cloud providers, custom endpoints, Ollama, LM Studio, oMLX | Not implemented in this port. These require separate normalized adapters and verified source contracts. The four existing providers are not substitutes for those integrations. |
| Multiple profiles/accounts per provider | Not implemented. Respects `CLAUDE_CONFIG_DIR` / `CODEX_HOME` for the selected profile; does not discover or open other account credentials. |
| Codex conversation grouping and desktop database activity | Root CLI rollouts supported; known helper rollouts are excluded to avoid false completion. No desktop SQLite reader or parent-conversation aggregation yet. |
| Claude moved-worktree transcript fallback | Direct cwd-derived transcript path supported. Does not scan unrelated project folders to recover moved transcripts. Registry states remain authoritative. |
| Phone pairing, remote-host monitoring | Not implemented; no local server, pairing keys or exposed network port are introduced. |
| macOS hardware notch, Dock/menu bar, AppKit focus, Sparkle | Platform-specific. Omarchy layer shell, Hyprland focus and Omarchy plugin updates serve the native Linux roles. |
| Completely hidden visibility mode, custom native settings window | Not implemented; hover/click/always-open modes and bounded in-card settings remain. Full-screen and overlap folding are implemented through Hyprland events (`autoHideMode`). |

## Verification

- `make check`: Python behavioral/contract tests, lint and Omarchy plugin validation.
- `make smoke`: optional native offscreen Quickshell check covering real QML preference updates, re-enable ordering, remembered edge positions, session transitions, invalid documents, settings categories and card height.
- Synthetic offscreen renders check the card, ring indicators and settings. They do not prove live Hyprland pointer routing, compositor focus, notification delivery, audio hardware or real signed-in provider behavior. Those require an installed desktop session.

## Source mapping

The reference README and these upstream files informed the port: `Sources/Sessions/AgentSession.swift`, `ActivitySummary.swift`, `ClaudeSessionRecord.swift`, `ClaudeTranscript.swift`, `CodexActivityMonitor.swift`, `SessionCompletionWatcher.swift`, `Sources/Notch/NotchMotion.swift`, and `Sources/Settings/{BusyIndicatorStyle,PeekDuration}.swift`. MIT attribution is retained in `THIRD_PARTY_NOTICES.md`.

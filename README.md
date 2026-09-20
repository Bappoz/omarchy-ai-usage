# Omarchy AI Usage

A native, edge-attached AI quota surface for Omarchy, inspired by the compact interaction model and visual language of CodeNotch.

> Release status: version 0.8.0 is ready for daily use and Omarchy Marketplace submission.

![CodeNotch-faithful notch and usage card](docs/assets/codenotch-faithful-surface.png)

## What it does

Omarchy already includes an Agents bar widget. This project explores a different form: a small surface attached directly to a screen edge that expands into provider details without occupying the bar.

Live mode supports Claude Code and Codex using their existing signed-in sessions. Perplexity remains available only in the explicitly labeled visual preview and is never presented as live data.

## Highlights

- faithful black CodeNotch silhouette, provider rings, pointer-connected card, palette, and motion vocabulary;
- top, right, bottom, and left placement with a normalized continuous offset;
- focused, named, and all-display scopes with reconnect fallback;
- small, medium, and large semantic sizes;
- hover, click, and always-open rail behavior;
- optional provider label, percentage, reset timer, and motion;
- native in-card preferences persisted in Omarchy's own `shell.json` plugin entry;
- one independent 15-minute poller per enabled provider, regardless of display count;
- bounded retries with exponential backoff, auth-aware delay, and reset-aware rate-limit delay;
- explicit active, loading, stale, authentication, rate-limited, error, and unavailable states;
- click-on-ring manual refresh with concurrent requests collapsed into one follow-up;
- bounded Claude and Codex collection using their existing authenticated sessions;
- independent refresh of Omarchy's shared Claude usage record, even when `omarchy.agents` is disabled;
- atomic private last-known-good cache and safe stale-data fallback;
- no raw provider output, account identity, or credentials in logs or screenshots;
- local validation, portable contract tests, QML linting, and CI.

## Requirements

- Omarchy 4.0 or newer with the Quickshell-based shell;
- Claude Code and/or Codex, already signed in for live usage;
- Python 3.11 or newer;
- `omarchy plugin validate` for platform validation.

No third-party Python or JavaScript runtime dependency is required.

## Preferences

Hover over the notch, open a provider, and select the sliders icon in the card. Each row cycles through its supported values. Changes are applied live and written through Omarchy's scoped plugin API.

Claude and Codex are enabled automatically. Toggle either one directly in the card—no code, API key, or manual JSON edit is required. At least one provider stays enabled. Other preferences include edge, position, display scope, size, open behavior, refresh interval, provider label, percentage, reset time, and motion. Exact connector names and arbitrary offsets can also be supplied in the plugin's inline `shell.json` entry. See [Configuration](docs/configuration.md).

### Claude does not appear

1. Confirm Claude Code is installed with `claude --version`.
2. Sign in through Claude Code with `claude auth login`.
3. Open the card settings and make sure **Claude** is **On**.
4. Restart the Omarchy shell or update/re-enable the plugin if it was already running an older release.

The plugin delegates authentication to Claude Code through Omarchy's official collector. It does not ask for or store a Claude token.

Claude refreshes also run Omarchy's official `omarchy-agent-usage-update --limits-only claude` path. This keeps `~/.local/state/omarchy/agents/usage/claude.json` current for compatible companion surfaces—such as themed or Pokémon usage widgets—even when the native `omarchy.agents` bar widget is disabled. The notch's existing startup, polling, and manual-refresh cadence owns this update, so no extra background daemon is installed.

The environment variables `OMARCHY_AI_USAGE_EDGE`, `OMARCHY_AI_USAGE_OFFSET`, and `OMARCHY_AI_USAGE_SCREEN` remain temporary, non-persistent overrides for visual testing. `OMARCHY_AI_USAGE_PREVIEW=1` enables the labeled synthetic reference composition. `OMARCHY_REDUCED_MOTION=1` disables surface animation for the session.

## Validation

Run the complete local gate:

```sh
make check
```

The gate runs unit and contract tests, Python linting, QML linting, and the official Omarchy plugin validator. CI runs the portable subset on every push and pull request.

To probe only the normalized provider output:

```sh
python helpers/claude_provider.py --no-cache
python helpers/codex_provider.py --no-cache
```

Provider problems are represented as safe status objects and still exit successfully. Invalid command-line arguments exit with code 2.

## Installation

Install directly from the public repository:

```sh
omarchy plugin add https://github.com/Bappoz/omarchy-ai-usage.git --enable
```

Update or remove it with the normal Omarchy lifecycle:

```sh
omarchy plugin update ai-usage.notch
omarchy plugin remove ai-usage.notch
```

Marketplace maintainers validate the current public commit before approval. The repository includes a root `preview.png`, license, safe lifecycle instructions, and the official validator gate. See [Marketplace publishing](docs/marketplace-publishing.md).

See [Release readiness](docs/release-readiness.md) for the checks to complete before tagging a public release.

## Repository layout

```text
.
├── manifest.json
├── contracts/provider-snapshot.schema.json
├── helpers/{claude,codex}_provider.py
├── src/
│   ├── model/
│   ├── ui/
│   └── Main.qml
├── tests/
└── docs/
```

## Privacy and security

The repository contains no real provider output or account data. Authentication stays inside Claude Code and Codex; the plugin reads only normalized quota responses and never opens credential files. Cached snapshots contain usage windows, percentages, reset times, and an optional plan label—never tokens or account identifiers. See [Security policy](SECURITY.md).

## License and attribution

MIT. CodeNotch-derived visual geometry and bundled provider marks retain their respective attribution in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

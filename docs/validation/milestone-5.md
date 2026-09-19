# Milestone 5 validation — placement, multi-monitor, and CodeNotch fidelity

Date: 2026-09-19
Result: passed

## Automated checks

- 47 unit, contract, packaging, placement, license-boundary, and UI-structure tests passed.
- `qmllint` accepted every project QML file against the installed Omarchy and Quickshell modules.
- `omarchy plugin validate .` accepted the schema-version-1 service manifest at version 0.5.0.
- Tests cover four edges, normalized offsets, focused/named/all display scopes, one shared provider store, bounded input regions, local vector glyphs, fixed usage bands, used-percent presentation, reference motion timings, and the honest preview/live split.

## Placement checks

The isolated service was exercised without installation or shell configuration changes.

- Right-center rendered the three-provider reference column and Claude tooltip.
- Top at `0.20` and bottom at `0.80` rendered horizontal provider rows with the card pointer aligned to Claude.
- Left at `0.65` rendered the mirrored vertical silhouette and outward tooltip.
- The resting right-edge state collapsed to the small black handle.
- Every run produced exactly one product layer on the selected display.
- Every layer remained non-exclusive, transparent outside its dynamic mask, and keyboard-focus-free.
- The isolated processes were terminated; Hyprland reported no remaining `ai-usage` surfaces.

## Visual checks

- Side-body depth, 44 px rings, inverse flares, tooltip width, corner radius, spacing, and pointer geometry match the fixed CodeNotch design ratios.
- Surface and card are pure black with no theme tint or decorative border.
- Claude 73% is orange, Codex 21% is green, and Perplexity 52% is yellow.
- The Claude, OpenAI/Codex, and Perplexity marks render as local monochrome SVGs.
- Both compact labels and detail bars use percent used.
- The preview tooltip is visibly marked `PREVIEW`; live mode creates only the real Codex cell.
- The 250 ms pointer bridge is included in the input mask so crossing from ring to tooltip does not drop interaction.

Live Codex mode was also started against an isolated state directory. It rendered one provider surface without QML/provider warnings, wrote only the normalized last-known-good cache with mode `0600`, and did not expose provider output in logs or screenshots.

## Motion checks

- Unfold/fold targets are 420/220 ms.
- Provider cells enter with a 45 ms stagger.
- Tooltip position changes use the 500 ms glide vocabulary.
- Ring and bar changes use 900 ms measurement sweeps.
- Closing retains a 250 ms hover grace period.

## Defects found and fixed

1. The first Milestone 5 treatment used adaptive glass, theme tinting, hairline borders, nested status chrome, and a single letter instead of the provider mark. It was recognizably a generic dashboard card rather than CodeNotch. The treatment was removed.
2. The previous compact component could display only one provider. The new rail is data-driven and changes orientation by edge while live mode still exposes only implemented providers.
3. The previous card displayed remaining quota while the requested reference displays consumed quota. All presentation now uses explicit `usedPercent`, with a guarded complement only when the normalized window supplies remaining data.
4. Separate triangular pointer chrome created a pasted-on appearance. The new curved pointer overlaps the black card by one pixel and shares the same unbordered fill.
5. Third-party visual reuse was previously documented only as inspiration. The repository now carries the relevant MIT and CC0 notices and identifies the exact fixed reference revision.

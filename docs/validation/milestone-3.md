# Milestone 3 validation — compact surface

Date: 2026-09-19
Result: passed

## Automated checks

- 33 unit and contract tests passed with resource warnings promoted to errors.
- The bundled visual fixture satisfies the provider snapshot contract.
- Tests assert that QML does not invoke the Codex helper, app-server, a process, or a timer.
- Tests assert one startup-selected monitor rather than multi-monitor variants.
- Tests assert no exclusive zone and no keyboard focus.
- Ruff reported no Python lint errors.
- `qmllint` accepted every project QML file against the installed Omarchy modules.
- Omarchy accepted the schema-version-1 plugin manifest at version 0.3.0.

## Isolated compositor test

The visual was launched in a separate Quickshell instance with temporary imports pointing at the installed Omarchy `Commons` and `Ui` modules. The plugin was not copied into `~/.config/omarchy/plugins`, enabled, or added to `shell.json`.

Hyprland reported exactly one `ai-usage-notch` layer surface:

- top coordinate: 0;
- one display only;
- centered horizontally to the pixel;
- rendered size: 191 × 58 px after the active Omarchy typography/spacing scale;
- exclusive zone: ignored by design.

The surface was captured, inspected visually, and the isolated process was terminated. Hyprland then reported zero remaining `ai-usage-notch` surfaces.

## Visual inspection

- The surface meets the top edge without a visible gap.
- Lower corners are rounded and the border remains visible.
- Ring progress, center number, provider name, and `% left` caption are legible.
- The `DEMO` marker is visible but subordinate.
- Popup colors and Omarchy typography are applied.
- No clipping or overlap was observed inside the 191 × 58 px surface.

## Defects found and fixed

1. `DemoSnapshot` initially declared `FileView` as an implicit child of `QtObject`, which has no default child property. It was changed to an explicit `property FileView`, matching Omarchy singleton patterns.
2. The installed Qt accessibility attachment does not expose `Accessible.value`. The ring now supplies an accessible name plus percentage description.

Both defects were found before installation and are covered by QML loading or static tests.

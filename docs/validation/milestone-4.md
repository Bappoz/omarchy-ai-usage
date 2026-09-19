# Milestone 4 validation — live provider and expanded card

Date: 2026-09-19
Result: passed

## Automated checks

- 36 unit, contract, packaging, and UI-structure tests passed.
- Ruff reported no Python lint errors.
- `qmllint` accepted every project QML file against the installed Omarchy modules.
- Omarchy accepted the schema-version-1 service manifest at version 0.4.0.
- Tests assert a live provider process, no periodic timer, single-flight refresh, explicit preview labeling, all seven provider states, passive layer behavior, and one startup-selected screen.

## Live-path test

The complete QML service was launched in an isolated Quickshell process with a temporary `XDG_STATE_HOME`. The real provider completed without QML warnings or raw provider output in the console. Its normalized cache passed a shape check, used mode `0600`, and remained outside the user's normal state directory. No real percentages or provider payloads were captured or committed.

## Expanded visual test

The expanded card was launched with the explicit synthetic preview flag. Hyprland reported one `ai-usage-notch` surface on one display:

- top coordinate: 0;
- centered horizontally;
- expanded rendered size: 355 × 213 px after the active Omarchy scale;
- exclusive zone: ignored;
- keyboard focus: none.

The compact header remained attached to the top edge. The detail card showed the provider, state, quota window, reset time, update time, and refresh action without clipping. `PREVIEW` appeared in both compact and expanded contexts. The isolated process was terminated and Hyprland reported zero remaining product surfaces.

## Security observations

- QML invokes the helper as an argument vector, not through a shell.
- Child stderr is consumed but never logged.
- Provider stdout is never printed; malformed data maps to a static message.
- The visual fixture is opt-in and cannot silently replace failed live data.
- No plugin was installed or enabled in the user's Omarchy configuration.

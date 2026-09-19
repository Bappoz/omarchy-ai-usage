from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preferences = (ROOT / "src" / "model" / "Preferences.qml").read_text()
        self.main = (ROOT / "src" / "Main.qml").read_text()
        self.settings = (ROOT / "src" / "ui" / "SettingsPane.qml").read_text()
        self.window = (ROOT / "src" / "ui" / "EdgeWindow.qml").read_text()

    def test_preferences_use_omarchy_inline_plugin_settings(self) -> None:
        self.assertIn('/.config/omarchy/shell.json', self.preferences)
        self.assertIn("root.shell.updateEntryInline(root.pluginId, next)", self.preferences)
        self.assertNotIn("omarchy-ai-usage/config.json", self.preferences)

    def test_persisted_values_are_bounded_and_versioned(self) -> None:
        for key in (
            "settingsVersion",
            "edge",
            "offset",
            "monitor",
            "size",
            "autoHide",
            "expandBehavior",
            "pollingInterval",
            "showProviderLabel",
            "showPercentage",
            "showResetTimer",
            "animations",
            "enabledProviders",
        ):
            with self.subTest(key=key):
                self.assertIn(f'"{key}"', self.preferences)
        self.assertIn("clamp(raw.pollingInterval, 60, 3600", self.preferences)
        self.assertIn("clamp(raw.offset, 0, 1", self.preferences)

    def test_environment_overrides_remain_preview_only_escape_hatches(self) -> None:
        self.assertIn('environmentOr(\n    "OMARCHY_AI_USAGE_EDGE"', self.main)
        self.assertIn('"OMARCHY_AI_USAGE_OFFSET"', self.main)
        self.assertIn('"OMARCHY_AI_USAGE_SCREEN"', self.main)

    def test_settings_cover_release_behavior_without_provider_credentials(self) -> None:
        for label in (
            "Claude",
            "Codex",
            "Screen edge",
            "Position",
            "Display",
            "Size",
            "Open",
            "Refresh",
            "Provider label",
            "Percentage",
            "Reset time",
            "Motion",
        ):
            with self.subTest(label=label):
                self.assertIn(label, self.settings)
        for forbidden in ("token", "password", "secret", "apiKey"):
            self.assertNotIn(forbidden, self.settings)
        self.assertIn('"claude": true, "codex": true', self.preferences)
        self.assertIn('preferenceChanged("enabledProviders", next)', self.settings)

    def test_reduced_motion_override_disables_all_surface_motion(self) -> None:
        self.assertIn('Quickshell.env("OMARCHY_REDUCED_MOTION") !== "1"', self.window)
        self.assertIn("animationsEnabled: root.motionEnabled", self.window)
        self.assertIn("duration: root.motionEnabled ? 500 : 0", self.window)
        ring = (ROOT / "src" / "ui" / "UsageRing.qml").read_text()
        self.assertIn("duration: root.animationsEnabled ? 900 : 0", ring)

    def test_semantic_size_scales_geometry_typography_and_rings(self) -> None:
        compact = (ROOT / "src" / "ui" / "CompactNotch.qml").read_text()
        expanded = (ROOT / "src" / "ui" / "ExpandedCard.qml").read_text()
        ring = (ROOT / "src" / "ui" / "UsageRing.qml").read_text()
        self.assertIn('preferences.size === "small" ? 0.85', self.window)
        self.assertIn('preferences.size === "large" ? 1.2', self.window)
        self.assertIn("font.pixelSize: 14 * root.uiScale", compact)
        self.assertIn("font.pixelSize: 14 * root.uiScale", expanded)
        self.assertIn("(44 / 117) * uiScale", ring)


if __name__ == "__main__":
    unittest.main()

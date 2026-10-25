from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

from test_contract import validate_snapshot

ROOT = Path(__file__).resolve().parents[1]


class CompactUiTests(unittest.TestCase):
    def test_demo_fixture_satisfies_provider_contract(self) -> None:
        fixture = json.loads((ROOT / "src" / "fixtures" / "compact-active.json").read_text())
        validate_snapshot(fixture)

    def test_service_uses_one_bounded_runner_per_live_provider(self) -> None:
        source = "\n".join(path.read_text() for path in sorted((ROOT / "src").rglob("*.qml")))
        provider = (ROOT / "src" / "model" / "ProviderRunner.qml").read_text()
        self.assertIn("omarchy_agent_provider.py", source)
        self.assertIn('helperArguments: ["--provider", "claude"]', source)
        self.assertIn('helperArguments: ["--provider", "codex"]', source)
        self.assertIn('watchedFilePath: root.agentUsageDir + "/claude.json"', source)
        self.assertIn('watchedFilePath: root.agentUsageDir + "/codex.json"', source)
        self.assertNotIn("account/rateLimits/read", source)
        self.assertIn("Process {", source)
        self.assertEqual(provider.count("property Timer pollTimer: Timer {"), 1)
        self.assertIn("pollingIntervalSeconds: root.preferenceValues.pollingInterval", source)
        self.assertIn("Math.pow(2, root.consecutiveFailures - 1)", provider)
        self.assertIn('status === "RATE_LIMITED"', provider)
        self.assertIn('status === "NEEDS_AUTH"', provider)

    def test_synthetic_preview_is_explicit_and_opt_in(self) -> None:
        source = (ROOT / "src" / "model" / "ProviderStore.qml").read_text()
        card = (ROOT / "src" / "ui" / "ExpandedCard.qml").read_text()
        self.assertIn('Quickshell.env("OMARCHY_AI_USAGE_PREVIEW") === "1"', source)
        self.assertIn('text: "PREVIEW"', card)

    def test_expanded_card_handles_every_provider_state(self) -> None:
        source = (ROOT / "src" / "ui" / "ExpandedCard.qml").read_text()
        for status in (
            "ACTIVE",
            "LOADING",
            "STALE",
            "NEEDS_AUTH",
            "RATE_LIMITED",
            "ERROR",
            "UNAVAILABLE",
        ):
            with self.subTest(status=status):
                self.assertIn(f'root.status === "{status}"', source)

    def test_refresh_is_scheduled_and_single_flight(self) -> None:
        source = (ROOT / "src" / "model" / "ProviderRunner.qml").read_text()
        self.assertIn("if (providerProcess.running) {", source)
        self.assertIn("root.refreshPending = true", source)
        self.assertIn('providerProcess.command = ["python3", root.helperPath].concat', source)
        self.assertIn("property FileView providerRecordWatcher: FileView {", source)
        self.assertNotIn("console.log", source)
        self.assertNotIn("console.warn", source)

    def test_opening_or_switching_provider_requests_fresh_limits(self) -> None:
        window = (ROOT / "src" / "ui" / "EdgeWindow.qml").read_text()
        store = (ROOT / "src" / "model" / "ProviderStore.qml").read_text()
        self.assertIn("var shouldRefresh = root.hoveredIndex !== index || !root.showCard", window)
        self.assertIn("if (shouldRefresh && !root.previewMode", window)
        self.assertIn('root.refreshRequested(String(root.providers[index].id || ""))', window)
        self.assertIn("interval: 30000", window)
        self.assertIn("running: root.showCard && !root.previewMode", window)
        self.assertIn('["omarchy-shell", "omarchy.agents", "refresh"]', store)
        self.assertIn("officialRefreshCooldownMs: 15000", store)
        self.assertIn("if (officialRefreshProcess.running)", store)
        self.assertIn("root.officialRefreshPending = true", store)

    def test_surface_is_passive_and_non_exclusive(self) -> None:
        source = (ROOT / "src" / "ui" / "EdgeWindow.qml").read_text()
        self.assertIn("exclusionMode: ExclusionMode.Ignore", source)
        self.assertIn("WlrKeyboardFocus.None", source)
        self.assertIn('WlrLayershell.namespace: "ai-usage-notch"', source)
        self.assertIn("top: true", source)

    def test_one_shared_store_feeds_dynamic_screen_variants(self) -> None:
        source = (ROOT / "src" / "Main.qml").read_text()
        self.assertEqual(source.count("ProviderStore {"), 1)
        self.assertIn("Variants {", source)
        self.assertIn("model: root.selectedScreens", source)

    def test_codenotch_palette_and_used_thresholds_are_exact(self) -> None:
        source = "\n".join(
            (ROOT / "src" / "ui" / name).read_text()
            for name in ("EdgeNotchSurface.qml", "ExpandedCard.qml", "UsageRing.qml", "Usage.js")
        )
        for color in ("#000000", "#303030", "#2d2d2d", "#00ff88", "#f2ff00", "#ff3f00"):
            with self.subTest(color=color):
                self.assertIn(color, source)
        self.assertIn("used < 50", source)
        self.assertIn("used < 70", source)
        self.assertNotIn("Color.background", source)

    def test_expanded_view_uses_codenotch_inspired_linear_windows(self) -> None:
        source = (ROOT / "src" / "ui" / "ExpandedCard.qml").read_text()
        self.assertIn('root.providerName + " Usage"', source)
        self.assertIn('Math.round(limitRow.used) + "% Used"', source)
        self.assertIn("parent.width * limitRow.used / 100", source)
        self.assertNotIn("UsageRing {", source)

    def test_preview_rail_matches_reference_providers_without_faking_live_data(self) -> None:
        window = (ROOT / "src" / "ui" / "EdgeWindow.qml").read_text()
        self.assertIn('return [\n      { "id": "claude"', window)
        self.assertIn('{ "id": "codex", "displayName": "Codex", "usedPercent": 21', window)
        self.assertIn('{ "id": "perplexity", "displayName": "Perplexity", "usedPercent": 52', window)
        self.assertIn('"usedPercent": 73', window)
        self.assertIn("var currentSnapshots = Array.isArray(root.snapshots)", window)
        self.assertIn('"id": String(current.providerId || "")', window)

    def test_settings_icon_is_a_local_vector_not_an_emoji(self) -> None:
        card = (ROOT / "src" / "ui" / "ExpandedCard.qml").read_text()
        icon = ROOT / "src" / "assets" / "icons" / "settings.svg"
        self.assertTrue(icon.is_file())
        self.assertIn('source: "../assets/icons/settings.svg"', card)
        self.assertNotIn('"⚙"', card)

    def test_reference_glyphs_are_local_vector_assets(self) -> None:
        glyph = (ROOT / "src" / "ui" / "ProviderGlyph.qml").read_text()
        for provider in ("claude", "codex", "perplexity"):
            asset = ROOT / "src" / "assets" / "glyphs" / f"{provider}.svg"
            with self.subTest(provider=provider):
                self.assertTrue(asset.is_file())
                self.assertIn(f'{provider}.svg', glyph)
                self.assertIn('<path fill="#fff"', asset.read_text())
        self.assertNotIn("https://", glyph)

    def test_claude_glyph_uses_official_brand_orange(self) -> None:
        glyph = (ROOT / "src" / "ui" / "ProviderGlyph.qml").read_text()
        self.assertIn('colorizationColor: "#D97757"', glyph)
        self.assertIn('visible: root.providerId === "claude"', glyph)

    def test_reference_motion_vocabulary_is_present(self) -> None:
        compact = (ROOT / "src" / "ui" / "CompactNotch.qml").read_text()
        window = (ROOT / "src" / "ui" / "EdgeWindow.qml").read_text()
        ring = (ROOT / "src" / "ui" / "UsageRing.qml").read_text()
        self.assertIn("root.animationsEnabled ? (root.unfolded ? 420 : 220) : 0", compact)
        self.assertIn("cell.index * 45", compact)
        self.assertIn("interval: 250", window)
        self.assertIn("duration: root.motionEnabled ? 500 : 0", window)
        self.assertIn("enabled: root.animationsEnabled", ring)
        self.assertIn("SpringAnimation", ring)

    def test_settings_follow_auto_hide_after_pointer_leaves(self) -> None:
        window = (ROOT / "src" / "ui" / "EdgeWindow.qml").read_text()
        self.assertIn("if (!root.autoHide || root.forcedOpen) return", window)
        self.assertIn("if (!root.settingsOpen && (!root.hoverExpansion || root.heldOpen)) return", window)
        self.assertIn("root.settingsOpen = false", window)
        self.assertIn("root.heldOpen = false", window)
        self.assertNotIn("root.heldOpen = true\n        if (root.hoveredIndex", window)


class UsageHelpersTests(unittest.TestCase):
    """Runs the pure helpers in Usage.js under node; skipped when node is absent."""

    def run_js(self, expression: str) -> object:
        node = shutil.which("node")
        if node is None:
            self.skipTest("node not available")
        source = (ROOT / "src" / "ui" / "Usage.js").read_text().replace(".pragma library", "")
        script = f"{source}\nconsole.log(JSON.stringify({expression}))"
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
        return json.loads(result.stdout)

    def test_accent_accepts_only_six_digit_hex(self) -> None:
        self.assertEqual(self.run_js('validAccent("#7C9CFF")'), "#7c9cff")
        for bad in ("red", "#fff", "#gggggg", "", "javascript:1"):
            with self.subTest(bad=bad):
                self.assertEqual(self.run_js(f"validAccent({json.dumps(bad)})"), "auto")

    def test_custom_accent_replaces_threshold_scale(self) -> None:
        self.assertEqual(self.run_js('usageColor(10, "auto")'), "#00ff88")
        self.assertEqual(self.run_js('usageColor(90, "auto")'), "#ff3f00")
        self.assertEqual(self.run_js('usageColor(90, "#7c9cff")'), "#7c9cff")
        self.assertEqual(self.run_js('usageColor(null, "#7c9cff")'), "#808080")

    def test_pace_projects_limit_before_reset(self) -> None:
        window = '{usedPercent: 60, resetAt: "2026-01-01T05:00:00Z", durationMinutes: 300}'
        now = 'Date.parse("2026-01-01T03:00:00Z")'  # 60% elapsed
        self.assertEqual(self.run_js(f"pace({window}, {now})")["tone"], "ok")
        fast = '{usedPercent: 60, resetAt: "2026-01-01T05:00:00Z", durationMinutes: 300}'
        early = 'Date.parse("2026-01-01T00:30:00Z")'  # 10% elapsed, 60% used
        result = self.run_js(f"pace({fast}, {early})")
        self.assertEqual(result["tone"], "over")
        self.assertIn("~", result["text"])

    def test_pace_is_null_without_reset_metadata(self) -> None:
        self.assertIsNone(self.run_js("pace({usedPercent: 50, resetAt: null, durationMinutes: null}, 0)"))


class InsightsHelpersTests(unittest.TestCase):
    """Chart, formatting and validation helpers (same node harness)."""

    run_js = UsageHelpersTests.run_js

    def test_compact_numbers_and_model_labels(self) -> None:
        self.assertEqual(self.run_js("compactNumber(5859345)"), "5.9M")
        self.assertEqual(self.run_js("compactNumber(999600)"), "1M")
        self.assertEqual(self.run_js("compactNumber(340)"), "340")
        self.assertEqual(self.run_js("compactNumber(-1)"), "\u2014")
        for raw, label in (
            ("claude-sonnet-5-5", "Sonnet 5.5"),
            ("gpt-6-luna", "GPT-6 Luna"),
            ("claude-3-5-sonnet-20241022", "3.5 Sonnet"),
            ("", "Unknown"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(self.run_js(f"modelLabel({json.dumps(raw)})"), label)

    def test_smooth_path_never_leaves_the_plot(self) -> None:
        segments = self.run_js(
            '(function(){var p=smoothPath([0,9,0,9,0],100,40);'
            'return p.line.split(" C ").slice(1).map(function(s){var a=s.split(" ").map(Number);return [a[1],a[3],a[5]]})})()'
        )
        self.assertEqual(len(segments), 4)
        for control_ys in segments:
            for y in control_ys:
                self.assertTrue(3 <= y <= 38.5, y)
        self.assertEqual(self.run_js("smoothPath([1],100,40).line"), "")

    def test_insights_document_is_validated_before_use(self) -> None:
        hourly = ", ".join('{tokens: 1}' for _ in range(24))
        good = f'{{schemaVersion: 1, providerId: "claude", hourly: [{hourly}], models: [], totals: {{}}}}'
        self.assertTrue(self.run_js(f'isInsights({good}, "claude")'))
        self.assertFalse(self.run_js(f'isInsights({good}, "codex")'))
        self.assertFalse(self.run_js('isInsights({schemaVersion: 1, providerId: "claude", hourly: [], models: [], totals: {}}, "claude")'))
        self.assertFalse(self.run_js('isInsights(null, "claude")'))

    def test_long_model_lists_collapse_into_other(self) -> None:
        merged = self.run_js(
            '(function(){var m=[1,2,3,4,5,6].map(function(i){return {name:"m"+i,tokens:i,share:0.1*i}});'
            'return collapseModels(m,4)})()'
        )
        self.assertEqual([m["name"] for m in merged], ["m1", "m2", "m3", "other"])
        self.assertEqual(merged[-1]["tokens"], 15)
        self.assertAlmostEqual(merged[-1]["share"], 1.5)


class InsightsWiringTests(unittest.TestCase):
    def read(self, *parts: str) -> str:
        return (ROOT.joinpath("src", *parts)).read_text()

    def test_rings_wait_for_the_silhouette_to_finish_unfolding(self) -> None:
        compact = self.read("ui", "CompactNotch.qml")
        ring = self.read("ui", "UsageRing.qml")
        self.assertIn("root.unfolded && root.openProgress >= 0.995 ? 1 : 0", compact)
        self.assertIn("active: cell.reveal > 0.01", compact)
        self.assertIn("active ? safeUsed / 100 : 0", ring)

    def test_clicking_a_logo_opens_the_app_instead_of_refreshing(self) -> None:
        window = self.read("ui", "EdgeWindow.qml")
        block = window.split("onProviderActivated: function(index) {")[1].split("\n    }")[0]
        self.assertIn("root.appRequested(", block)
        self.assertNotIn("refreshRequested", block)
        self.assertIn("onAppRequested: function(providerId) { appLauncher.open(providerId) }", self.read("Main.qml"))
        self.assertIn("onClicked: root.appRequested()", self.read("ui", "ExpandedCard.qml"))

    def test_app_launcher_uses_a_fixed_table_with_a_web_fallback(self) -> None:
        launcher = self.read("model", "AppLauncher.qml")
        self.assertIn('"desktop": "com.anthropic.Claude"', launcher)
        self.assertIn('["gtk-launch", app.desktop]', launcher)
        self.assertIn('["omarchy-launch-webapp", root.pendingUrl]', launcher)
        self.assertNotIn("preferences", launcher)
        self.assertIn("primary.running || fallback.running", launcher)

    def test_insights_panel_is_optional_and_keeps_the_card_open_while_hovered(self) -> None:
        window = self.read("ui", "EdgeWindow.qml")
        self.assertIn("preferences.showInsights !== false", window)
        self.assertIn("root.hoveringCard || root.hoveringPanel) return", window)
        self.assertIn("insightsPanel.opacity > 0", window)
        self.assertIn('"showInsights"', self.read("model", "Preferences.qml"))
        self.assertIn("Insights panel", self.read("ui", "SettingsPane.qml"))

    def test_insights_runner_is_single_flight_cooldown_bounded_and_validates_output(self) -> None:
        runner = self.read("model", "InsightsRunner.qml")
        self.assertIn("root.refreshPending = true", runner)
        self.assertIn("cooldownMs: 15000", runner)
        self.assertIn("Usage.isInsights(parsed, root.providerId)", runner)
        self.assertIn('"--provider", root.providerId', runner)
        self.assertNotIn("console.log", runner)
        window = self.read("ui", "EdgeWindow.qml")
        self.assertIn("interval: 60000", window)
        self.assertIn("running: root.showInsights && !root.previewMode", window)


if __name__ == "__main__":
    unittest.main()

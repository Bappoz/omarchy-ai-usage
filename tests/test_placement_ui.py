from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PlacementUiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.main = (ROOT / "src" / "Main.qml").read_text()
        self.window = (ROOT / "src" / "ui" / "EdgeWindow.qml").read_text()

    def test_all_four_edges_are_accepted(self) -> None:
        self.assertIn('["top", "right", "bottom", "left"]', self.main)
        for edge in ("top", "right", "bottom", "left"):
            with self.subTest(edge=edge):
                self.assertIn(f'root.edge === "{edge}"', self.window)

    def test_offset_is_normalized_and_defaults_to_center(self) -> None:
        self.assertIn('return 0.5', self.main)
        self.assertIn("Math.max(0, Math.min(1, candidate))", self.main)
        self.assertIn("root.edgeOffset * Math.max", self.window)

    def test_focused_specific_and_all_screen_scopes_exist(self) -> None:
        self.assertIn('root.screenSelection === "all"', self.main)
        self.assertIn('root.screenSelection !== "focused"', self.main)
        self.assertIn("Hyprland.focusedMonitor", self.main)
        self.assertIn("String(screens[j].name", self.main)
        self.assertIn("return focused ? [focused] : []", self.main)

    def test_surface_tracks_screen_changes_and_limits_input_region(self) -> None:
        self.assertIn("model: root.selectedScreens", self.main)
        self.assertIn("mask: Region {", self.window)
        self.assertIn("width: root.showCard || expandedCard.opacity > 0 ? expandedCard.width : 0", self.window)
        self.assertIn("notch.inputWidth", self.window)
        self.assertIn("root.bridgeRect().width", self.window)
        for anchor in ("top", "bottom", "left", "right"):
            self.assertIn(f"{anchor}: true", self.window)

    def test_right_edge_is_the_codenotch_faithful_default(self) -> None:
        self.assertIn(': "right"', self.main)
        self.assertIn('property string edge: "right"', self.window)


if __name__ == "__main__":
    unittest.main()

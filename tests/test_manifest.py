from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads((ROOT / "manifest.json").read_text())

    def test_required_fields_and_identity(self) -> None:
        required = {"schemaVersion", "id", "name", "version", "kinds", "entryPoints"}
        self.assertLessEqual(required, set(self.manifest))
        self.assertEqual(self.manifest["schemaVersion"], 1)
        self.assertRegex(self.manifest["id"], r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
        self.assertNotIn("..", self.manifest["id"])
        self.assertFalse(self.manifest["id"].startswith("omarchy."))
        self.assertRegex(self.manifest["version"], r"^\d+\.\d+\.\d+$")

    def test_service_entry_point_is_safe_and_exists(self) -> None:
        self.assertEqual(self.manifest["kinds"], ["service"])
        entry_point = self.manifest["entryPoints"]["service"]
        self.assertFalse(Path(entry_point).is_absolute())
        self.assertNotIn("..", entry_point)
        self.assertTrue((ROOT / entry_point).is_file())

    def test_repository_contains_no_symlinks(self) -> None:
        symlinks = [path for path in ROOT.rglob("*") if path.is_symlink()]
        self.assertEqual(symlinks, [])

    def test_direct_visual_reuse_carries_third_party_notices(self) -> None:
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text()
        self.assertIn("Copyright (c) 2026 Vinz", notice)
        self.assertIn("Copyright (c) LobeHub", notice)
        self.assertIn("CC0 1.0 Universal", notice)
        self.assertIn("ec1a7e3fc0634f668741cb0357029420bdd4281c", notice)


if __name__ == "__main__":
    unittest.main()

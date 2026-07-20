#!/usr/bin/env python3
"""Release packaging hygiene verification tests."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _load_script_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseHygieneTests(unittest.TestCase):

    def test_preferences_example_has_no_developer_paths(self) -> None:

        example = REPO_ROOT / "src" / "config" / "preferences.json.example"
        text = example.read_text(encoding="utf-8")

        self.assertNotIn("/home/zoli", text)
        self.assertIn('"data_directory": null', text)

    def test_verify_release_hygiene_passes_on_clean_tree(self) -> None:

        module = _load_script_module(
            "verify_release_hygiene_test",
            "verify_release_hygiene.py",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            hajok = data_dir / "Hajók"
            photos = data_dir / "vessel_photos"
            hajok.mkdir(parents=True)
            photos.mkdir(parents=True)
            (hajok / ".gitkeep").write_text("", encoding="utf-8")
            (photos / ".gitkeep").write_text("", encoding="utf-8")

            original_root = module.ROOT
            original_data = module._import_verify_data_tree().DATA_DIR
            module.ROOT = Path(temp_dir)
            module.SRC_CONFIG = REPO_ROOT / "src" / "config"
            verify_module = module._import_verify_data_tree()
            verify_module.ROOT = REPO_ROOT
            verify_module.DATA_DIR = data_dir

            try:
                self.assertEqual(module.verify_data_tree(), [])
                self.assertEqual(module.verify_runtime_config_artifacts(), [])
                self.assertEqual(module.verify_bundled_config_paths(), [])
            finally:
                module.ROOT = original_root
                verify_module.DATA_DIR = original_data

    def test_clean_data_tree_removes_runtime_artifacts(self) -> None:

        module = _load_script_module("clean_data_tree_test", "clean_data_tree.py")

        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data"
            hajok = data_dir / "Hajók"
            hajok.mkdir(parents=True)
            (hajok / ".gitkeep").write_text("", encoding="utf-8")
            (hajok / "DEV SHIP" / "notes.txt").parent.mkdir(parents=True)
            (hajok / "DEV SHIP" / "notes.txt").write_text("dev", encoding="utf-8")
            (data_dir / "vessels.db").write_text("db", encoding="utf-8")

            removed = module.clean_data_tree(data_dir)

            self.assertTrue((hajok / ".gitkeep").is_file())
            self.assertFalse((hajok / "DEV SHIP").exists())
            self.assertFalse((data_dir / "vessels.db").exists())
            self.assertGreater(len(removed), 0)


if __name__ == "__main__":
    unittest.main()

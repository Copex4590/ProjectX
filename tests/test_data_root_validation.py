#!/usr/bin/env python3
"""Unit tests for the data root validation service (SAVE-107-C2)."""

from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from isolated_paths import isolated_temp_dir
from storage import DATA_ROOT_MARKER_NAME, default_data_directory, ensure_data_layout
from storage.data_root_validation import DataRootValidationService, ValidationSeverity


class DataRootValidationServiceTests(unittest.TestCase):

    def setUp(self) -> None:

        self.service = DataRootValidationService()

    def test_recommended_location_is_valid(self) -> None:

        with isolated_temp_dir() as temp_dir:
            recommended = Path(temp_dir) / "Project X"
            result = self.service.validate(recommended)

            self.assertTrue(result.valid, result.message)
            self.assertEqual(result.severity, ValidationSeverity.NONE)
            self.assertTrue(recommended.is_dir())

    def test_custom_writable_location_is_valid(self) -> None:

        with isolated_temp_dir() as temp_dir:
            custom = Path(temp_dir) / "Custom Data"
            result = self.service.validate(custom)

            self.assertTrue(result.valid, result.message)
            self.assertEqual(result.severity, ValidationSeverity.NONE)
            self.assertEqual(result.path, custom.resolve())

    def test_empty_path_is_invalid(self) -> None:

        result = self.service.validate(Path("   "))

        self.assertFalse(result.valid)
        self.assertEqual(result.severity, ValidationSeverity.ERROR)
        self.assertIn("folder", result.message.lower())

    def test_temporary_directory_is_invalid(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "Project X"
            result = self.service.validate(candidate)

            self.assertFalse(result.valid)
            self.assertEqual(result.severity, ValidationSeverity.ERROR)
            self.assertIn("temporary", result.message.lower())

    def test_existing_marker_is_accepted(self) -> None:

        with isolated_temp_dir() as temp_dir:
            existing = Path(temp_dir) / "Project X"
            ensure_data_layout(existing)

            result = self.service.validate(existing)

            self.assertTrue(result.valid)
            self.assertEqual(result.severity, ValidationSeverity.NONE)
            self.assertFalse(result.blocks_completion)
            self.assertEqual(result.message, "")

    def test_nested_marker_is_rejected(self) -> None:

        with isolated_temp_dir() as temp_dir:
            parent = Path(temp_dir) / "Parent"
            parent.mkdir()
            nested = parent / "Nested"
            ensure_data_layout(nested)

            result = self.service.validate(parent)

            self.assertFalse(result.valid)
            self.assertIn("contains", result.message.lower())

    def test_path_inside_existing_data_root_is_rejected(self) -> None:

        with isolated_temp_dir() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)
            nested_choice = root / "Exports"

            result = self.service.validate(nested_choice)

            self.assertFalse(result.valid)
            self.assertIn("inside", result.message.lower())

    def test_non_writable_directory_is_rejected(self) -> None:

        if os.name == "nt":
            self.skipTest("Read-only directory semantics differ on Windows.")

        with isolated_temp_dir() as temp_dir:
            read_only = Path(temp_dir) / "ReadOnly"
            read_only.mkdir()
            read_only.chmod(stat.S_IRUSR | stat.S_IXUSR)

            try:
                result = self.service.validate(read_only)
            finally:
                read_only.chmod(stat.S_IRWXU)

            self.assertFalse(result.valid)
            self.assertIn("writable", result.message.lower())

    def test_default_data_directory_under_home_is_valid(self) -> None:

        with isolated_temp_dir() as temp_dir:
            fake_home = Path(temp_dir) / "home"
            fake_home.mkdir()

            with patch("storage.manager.Path.home", return_value=fake_home):
                recommended = default_data_directory()

            result = self.service.validate(recommended)

        self.assertTrue(result.valid, result.message)

    def test_marker_file_without_valid_payload_does_not_reject(self) -> None:

        with isolated_temp_dir() as temp_dir:
            candidate = Path(temp_dir) / "Project X"
            candidate.mkdir()
            (candidate / DATA_ROOT_MARKER_NAME).write_text("not-json", encoding="utf-8")

            result = self.service.validate(candidate)

            self.assertTrue(result.valid, result.message)

    def test_non_empty_directory_returns_warning(self) -> None:

        with isolated_temp_dir() as temp_dir:
            candidate = Path(temp_dir) / "Project X"
            candidate.mkdir()
            (candidate / "notes.txt").write_text("existing", encoding="utf-8")

            result = self.service.validate(candidate)

            self.assertTrue(result.valid)
            self.assertEqual(result.severity, ValidationSeverity.WARNING)
            self.assertFalse(result.blocks_completion)
            self.assertIn("not empty", result.message.lower())
            self.assertIn("unrelated", result.message.lower())

    def test_long_path_returns_warning(self) -> None:

        with isolated_temp_dir() as temp_dir:
            long_name = "a" * 240
            candidate = Path(temp_dir) / long_name

            result = self.service.validate(candidate)

            self.assertTrue(result.valid)
            self.assertEqual(result.severity, ValidationSeverity.WARNING)
            self.assertIn("very long", result.message.lower())


if __name__ == "__main__":
    unittest.main()

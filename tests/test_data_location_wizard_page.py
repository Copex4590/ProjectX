#!/usr/bin/env python3
"""Unit tests for the first-run data location wizard page (SAVE-107-C1)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

from PySide6.QtWidgets import QApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gui.data_location_wizard_page import DataLocationWizardPage, format_display_path
from storage import default_data_directory


class DataLocationWizardPageTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

        cls._app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:

        self.page = DataLocationWizardPage()

    def test_recommended_selected_by_default(self) -> None:

        self.assertTrue(self.page.uses_recommended())
        self.assertTrue(self.page._recommended_option.isChecked())
        self.assertFalse(self.page._custom_option.isChecked())

    def test_selected_directory_returns_default_when_recommended(self) -> None:

        self.assertEqual(
            self.page.selected_directory(),
            default_data_directory(),
        )

    def test_custom_selection_disables_until_path_chosen(self) -> None:

        self.page._custom_option.setChecked(True)
        self.page._sync_custom_controls()

        self.assertFalse(self.page.uses_recommended())
        self.assertTrue(self.page._browse_button.isEnabled())
        self.assertTrue(self.page._custom_path_input.isEnabled())

    def test_set_custom_directory_updates_display(self) -> None:

        custom_path = Path("/tmp/projectx-custom-data")
        self.page.set_custom_directory(custom_path)
        self.page._custom_option.setChecked(True)

        self.assertEqual(self.page.custom_directory(), custom_path)
        self.assertEqual(
            self.page.selected_directory(),
            custom_path,
        )
        self.assertIn(
            "projectx-custom-data",
            self.page._custom_path_input.text(),
        )

    def test_validation_error_visibility(self) -> None:

        self.page.show()
        QApplication.processEvents()

        self.assertFalse(self.page._error_label.isVisible())

        self.page.set_validation_error("Directory is not writable.")
        self.assertTrue(self.page._error_label.isVisible())
        self.assertEqual(
            self.page._error_label.text(),
            "Directory is not writable.",
        )

        self.page.clear_validation_error()
        self.assertFalse(self.page._error_label.isVisible())
        self.assertEqual(self.page._error_label.text(), "")

    def test_validation_warning_visibility(self) -> None:

        self.page.show()
        QApplication.processEvents()

        self.assertFalse(self.page._warning_label.isVisible())

        self.page.set_validation_warning("The selected folder is not empty.")
        self.assertTrue(self.page._warning_label.isVisible())
        self.assertIn(
            "The selected folder is not empty.",
            self.page._warning_label.text(),
        )
        self.assertFalse(self.page._error_label.isVisible())

        self.page.clear_validation_warning()
        self.assertFalse(self.page._warning_label.isVisible())

    def test_validation_warning_clears_error(self) -> None:

        self.page.show()
        QApplication.processEvents()

        self.page.set_validation_error("Directory is not writable.")
        self.page.set_validation_warning("The selected folder is not empty.")

        self.assertTrue(self.page._warning_label.isVisible())
        self.assertFalse(self.page._error_label.isVisible())

    def test_format_display_path_uses_home_prefix(self) -> None:

        home_child = Path.home() / "Project X"
        self.assertEqual(format_display_path(home_child), "~/Project X")


if __name__ == "__main__":
    unittest.main()

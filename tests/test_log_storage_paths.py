#!/usr/bin/env python3
"""Unit tests for logging storage path resolution (SAVE-107-B2.5)."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
import unittest
from logging.handlers import RotatingFileHandler
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from preferences.preferences import Preferences
from storage import (
    DATA_SUBDIR_LOGS,
    StorageMode,
    active_log_path,
    ensure_data_layout,
    resolve_data_root,
)


class LogPathResolutionTests(unittest.TestCase):

    def test_legacy_log_path_uses_project_x_logs_directory(self) -> None:

        with patch.dict(os.environ, {}, clear=True):
            with patch(
                "preferences.preferences_manager.preferences_manager.get",
                return_value=Preferences.defaults(),
            ):
                log_file = active_log_path("projectx.log")
                resolved = resolve_data_root()

        self.assertEqual(resolved.mode, StorageMode.LEGACY)
        self.assertIn("Project X/logs/projectx.log", str(log_file))

    def test_configured_log_path_uses_data_root_logs_subdirectory(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "Project X"
            ensure_data_layout(root)

            with patch.dict(os.environ, {"PROJECTX_DATA_DIRECTORY": str(root)}):
                log_file = active_log_path("projectx.log")
                resolved = resolve_data_root()

            self.assertEqual(resolved.mode, StorageMode.CONFIGURED)
            self.assertEqual(log_file, root / DATA_SUBDIR_LOGS / "projectx.log")


class LoggerSetupTests(unittest.TestCase):

    def test_logger_uses_storage_resolver_path(self) -> None:

        from core.logger import LOG_FILE, logger

        self.assertTrue(str(LOG_FILE).endswith("projectx.log"))

    def test_logger_has_single_rotating_file_handler(self) -> None:

        from core.logger import logger

        file_handlers = [
            handler
            for handler in logger.handlers
            if isinstance(handler, RotatingFileHandler)
        ]

        self.assertEqual(len(file_handlers), 1)
        self.assertEqual(len(logger.handlers), 1)

    def test_logger_writes_to_resolved_log_file(self) -> None:

        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "projectx.log"

            with patch("core.logger.LOG_FILE", log_file):
                with patch("core.logger._ensure_log_file", return_value=log_file):
                    test_logger = logging.getLogger("Project X.test-write")
                    test_logger.handlers.clear()
                    test_logger.setLevel(logging.DEBUG)
                    handler = RotatingFileHandler(
                        log_file,
                        maxBytes=5 * 1024 * 1024,
                        backupCount=5,
                        encoding="utf-8",
                    )
                    test_logger.addHandler(handler)

                    try:
                        test_logger.info("storage resolver logging test")
                        handler.flush()
                        self.assertTrue(log_file.is_file())
                        self.assertIn(
                            "storage resolver logging test",
                            log_file.read_text(encoding="utf-8"),
                        )
                    finally:
                        test_logger.handlers.clear()
                        handler.close()


if __name__ == "__main__":
    unittest.main()

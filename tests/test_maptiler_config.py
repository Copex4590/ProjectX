#!/usr/bin/env python3
"""Tests for bundled MapTiler configuration."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import maptiler as maptiler_config


class MapTilerConfigTests(unittest.TestCase):

    def test_maptiler_api_key_reads_env_override(self) -> None:

        with patch.dict(os.environ, {"PROJECTX_MAPTILER_API_KEY": "test-key"}, clear=False):
            self.assertEqual(maptiler_config.maptiler_api_key(), "test-key")

    def test_maptiler_api_key_reads_developer_file(self) -> None:

        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / "maptiler_api_key.txt"
            key_path.write_text("file-key\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                with patch.object(maptiler_config, "_developer_key_file", return_value=key_path):
                    with patch.object(maptiler_config, "is_frozen", return_value=False):
                        with patch.object(maptiler_config, "bundled_config_dir", return_value=Path(tmpdir)):
                            self.assertEqual(maptiler_config.maptiler_api_key(), "file-key")


if __name__ == "__main__":
    unittest.main()

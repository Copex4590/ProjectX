#!/usr/bin/env python3
"""Regression tests for AISStream startup configuration and status display."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ais.providers import AISProviderType
from ais.user_provider_service import (
    get_enabled_provider_ids,
    is_provider_configured,
    provider_display_status,
)
from preferences.preferences import Preferences


class AISStreamStartupTests(unittest.TestCase):

    def test_preferences_preserve_unset_enabled_providers(self) -> None:

        preferences = Preferences.defaults()

        payload = preferences.to_dict()

        self.assertIsNone(payload["ais_enabled_providers"])

    def test_get_enabled_provider_ids_uses_legacy_when_unset(self) -> None:

        with patch("ais.user_provider_service.preferences_manager") as manager:
            manager.get.return_value = Preferences(
                ais_provider="aisstream",
                ais_enabled_providers=None,
                aisstream_api_key="test-key",
                ais_configured=True,
            )

            self.assertEqual(get_enabled_provider_ids(), ["aisstream"])

    def test_get_enabled_provider_ids_honors_explicit_empty_list(self) -> None:

        with patch("ais.user_provider_service.preferences_manager") as manager:
            manager.get.return_value = Preferences(
                ais_provider="aisstream",
                ais_enabled_providers=[],
            )

            self.assertEqual(get_enabled_provider_ids(), [])

    def test_is_provider_configured_reads_api_key_file_fallback(self) -> None:

        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / "ais_api_key.txt"
            key_path.write_text("file-only-key\n", encoding="utf-8")

            with patch("ais.user_provider_service.preferences_manager") as manager:
                manager.get.return_value = Preferences(aisstream_api_key="")

                with patch(
                    "ais.user_provider_service.ais_api_key_file",
                    return_value=key_path,
                ):
                    self.assertTrue(
                        is_provider_configured(AISProviderType.AISSTREAM)
                    )

    def test_provider_display_status_shows_waiting_state(self) -> None:

        with patch(
            "ais.user_provider_service.is_provider_configured",
            return_value=True,
        ), patch(
            "ais.user_provider_service.provider_connection_status",
            return_value="waiting",
        ):
            status = provider_display_status(AISProviderType.AISSTREAM.value)

        self.assertEqual(status.icon, "🟡")
        self.assertIn("vár", status.text.lower())


if __name__ == "__main__":
    unittest.main()

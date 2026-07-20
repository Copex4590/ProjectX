#!/usr/bin/env python3
"""Regression tests for non-blocking AISStream resync from the GUI thread."""

from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ais.providers import AISProviderType
from engines.rtl.hybrid_engine import HybridEngine


class HybridEngineAisstreamResyncTests(unittest.TestCase):

    def test_sync_enabled_providers_does_not_block_on_ws_lock(self) -> None:

        engine = HybridEngine()
        engine._ws_lock.acquire()

        try:
            with patch(
                "ais.user_provider_service.is_provider_configured",
                return_value=True,
            ), patch.object(
                engine,
                "_log_aisstream_runtime_context",
            ):
                started = time.monotonic()
                engine.sync_enabled_providers(
                    enabled_ids=[AISProviderType.AISSTREAM.value]
                )
                elapsed = time.monotonic() - started

            self.assertLess(elapsed, 0.5)
            self.assertTrue(engine._aisstream_active)
            self.assertTrue(engine._resubscribe_requested)
        finally:
            engine._ws_lock.release()

    def test_on_observation_changed_requests_resubscribe_without_closing_ws(self) -> None:

        engine = HybridEngine()
        engine._aisstream_active = True
        engine._ws_lock.acquire()

        try:
            with patch.object(engine, "_close_ws") as close_ws:
                engine.on_observation_changed()

            close_ws.assert_not_called()
            self.assertTrue(engine._resubscribe_requested)
        finally:
            engine._ws_lock.release()


if __name__ == "__main__":
    unittest.main()

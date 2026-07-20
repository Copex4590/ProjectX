#!/usr/bin/env python3
"""Tests for AISStream connection diagnostics helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engines.ais.ais_protocol import AISSTREAM_WS_URL
from engines.rtl.hybrid_engine import HybridEngine


class HybridEngineAisstreamDiagnosticsTests(unittest.TestCase):

    def test_aisstream_ws_url_has_no_query_api_key(self) -> None:

        self.assertEqual(AISSTREAM_WS_URL, "wss://stream.aisstream.io/v0/stream")
        self.assertNotIn("apiKey", AISSTREAM_WS_URL)

    def test_message_metadata_accepts_both_casings(self) -> None:

        engine = HybridEngine()

        self.assertEqual(
            engine._aisstream_message_metadata({"MetaData": {"MMSI": "123"}}),
            {"MMSI": "123"},
        )
        self.assertEqual(
            engine._aisstream_message_metadata({"Metadata": {"MMSI": "456"}}),
            {"MMSI": "456"},
        )
        self.assertEqual(engine._aisstream_message_metadata({}), {})

    def test_interruptible_sleep_returns_early_on_resubscribe(self) -> None:

        engine = HybridEngine()
        engine._resubscribe_requested = True

        with patch("engines.rtl.hybrid_engine.time.sleep") as sleep:
            interrupted = engine._interruptible_sleep(5)

        self.assertTrue(interrupted)
        sleep.assert_not_called()

    def test_interruptible_sleep_waits_while_provider_inactive(self) -> None:

        engine = HybridEngine()
        engine.running = True

        with patch("engines.rtl.hybrid_engine.time.sleep") as sleep:
            interrupted = engine._interruptible_sleep(1)

        self.assertFalse(interrupted)
        self.assertGreaterEqual(sleep.call_count, 1)

    def test_publish_ais_status_deduplicates_eventbus(self) -> None:

        engine = HybridEngine()

        with patch("engines.rtl.hybrid_engine.eventbus.publish") as publish:
            engine._publish_ais_status("offline", reason="provider inactive")
            engine._publish_ais_status("offline", reason="provider inactive")

        publish.assert_called_once_with("ais.status", status="offline")

    def test_log_aisstream_step_emits_structured_message(self) -> None:

        engine = HybridEngine()

        with patch("engines.rtl.hybrid_engine.logger") as logger:
            engine._log_aisstream_step(
                2,
                "WebSocket URL selected",
                url=AISSTREAM_WS_URL,
            )

        logger.info.assert_called_once()
        message = " ".join(str(part) for part in logger.info.call_args[0])
        self.assertIn("2", message)
        self.assertIn("WebSocket URL selected", message)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""Regression tests for AISStream worker idle behavior."""

from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engines.rtl.hybrid_engine import HybridEngine


class HybridEngineAisstreamWorkerIdleTests(unittest.TestCase):

    def test_inactive_provider_loop_does_not_flood_status_events(self) -> None:

        engine = HybridEngine()
        engine.running = True
        publish_count = 0
        original_publish = engine._publish_ais_status

        def counting_publish(status: str, *, reason: str = "") -> None:
            nonlocal publish_count
            publish_count += 1
            original_publish(status, reason=reason)
            engine.running = False

        engine._publish_ais_status = counting_publish  # type: ignore[method-assign]

        with patch.object(engine, "_close_ws"), patch.object(
            engine,
            "_log_aisstream_runtime_context",
        ), patch("engines.rtl.hybrid_engine.eventbus.publish"), patch.object(
            engine,
            "_interruptible_sleep",
            return_value=False,
        ) as sleep:
            engine.aisstream_worker()

        self.assertEqual(publish_count, 1)
        sleep.assert_called_once()
        sleep.assert_called_with(1, wake_when=engine._aisstream_enabled)


if __name__ == "__main__":
    unittest.main()

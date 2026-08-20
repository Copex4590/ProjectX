"""Human-test diagnostics for the HLS playback chain. Logging only — no behavior change."""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

_LOG_PATH = Path(__file__).resolve().parents[2] / "output" / "hls_diag.log"
_session_written = False


def diag(step: str, **fields: object) -> None:
    global _session_written
    from camera_hunter.engine.providers.earthcam import mask_log_value

    stamp = datetime.now(timezone.utc).strftime("%H:%M:%S.%f")[:-3]
    bits = [f"[HLS-DIAG] {stamp} {step}"]
    for key, value in fields.items():
        bits.append(f"{key}={mask_log_value(key, value)!r}")
    line = " ".join(bits)
    print(line, file=sys.stderr, flush=True)
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            if not _session_written:
                fh.write(f"[HLS-DIAG] {stamp} session_start pid={os.getpid()}\n")
                _session_written = True
            fh.write(line + "\n")
    except OSError:
        pass


def diag_exc(step: str, **fields: object) -> None:
    diag(step, **fields)
    traceback.print_exc(file=sys.stderr)

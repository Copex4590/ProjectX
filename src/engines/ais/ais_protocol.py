# ============================================================================
# Project X
# AIS Protocol
# ============================================================================

from __future__ import annotations

from debug.obs_freeze_trace import trace_block, trace_enter, trace_exit
from observation.geo_context import geo_context

AISSTREAM_WS_URL = "wss://stream.aisstream.io/v0/stream"


def reference_observation_bounding_boxes() -> list[list[list[float]]] | None:

    trace_enter("AISProtocol.reference_observation_bounding_boxes")

    try:
        trace_enter("AISProtocol.reference_observation_bounding_boxes.geo_context")
        result = geo_context.ais_bounding_boxes()
        trace_exit("AISProtocol.reference_observation_bounding_boxes.geo_context")
        return result
    finally:
        trace_exit("AISProtocol.reference_observation_bounding_boxes")


def active_observation_bounding_boxes() -> list[list[list[float]]] | None:
    """Deprecated alias for reference_observation_bounding_boxes()."""

    return reference_observation_bounding_boxes()


class AISProtocol:

    @staticmethod
    def subscribe_message(
        api_key: str,
        *,
        bounding_boxes: list[list[list[float]]] | None = None,
    ):

        with trace_block("AISProtocol.subscribe_message"):
            boxes = bounding_boxes
            if boxes is None:
                boxes = reference_observation_bounding_boxes()

            if not boxes:
                raise ValueError(
                    "Cannot subscribe to AISStream without an observation "
                    "reference point"
                )

            return {
                "APIKey": api_key,
                "BoundingBoxes": boxes,
                "FilterMessageTypes": [
                    "PositionReport",
                    "ShipStaticData",
                    "StaticDataReport",
                ],
            }

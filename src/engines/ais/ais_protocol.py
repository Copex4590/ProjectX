# ============================================================================
# Project X
# AIS Protocol
# ============================================================================

from __future__ import annotations

from debug.obs_freeze_trace import trace_block, trace_enter, trace_exit
from observation import observation_manager

_DEFAULT_BOUNDING_BOXES = [
    [
        [45.00, 17.50],
        [48.50, 22.50],
    ]
]


def active_observation_bounding_boxes() -> list[list[list[float]]]:

    trace_enter("AISProtocol.active_observation_bounding_boxes")

    try:
        trace_enter("AISProtocol.active_observation_bounding_boxes.reference")
        point = observation_manager.reference()
        trace_exit("AISProtocol.active_observation_bounding_boxes.reference")

        if point is None:
            trace_enter("AISProtocol.active_observation_bounding_boxes.active")
            point = observation_manager.active()
            trace_exit("AISProtocol.active_observation_bounding_boxes.active")

        if point is None:
            trace_enter(
                "AISProtocol.active_observation_bounding_boxes.return_default"
            )
            result = _DEFAULT_BOUNDING_BOXES
            trace_exit(
                "AISProtocol.active_observation_bounding_boxes.return_default"
            )
            return result

        trace_enter("AISProtocol.active_observation_bounding_boxes.ais_bounding_box")
        result = [point.ais_bounding_box()]
        trace_exit("AISProtocol.active_observation_bounding_boxes.ais_bounding_box")
        return result
    finally:
        trace_exit("AISProtocol.active_observation_bounding_boxes")


class AISProtocol:

    @staticmethod
    def subscribe_message(
        api_key: str,
        *,
        bounding_boxes: list[list[list[float]]] | None = None,
    ):

        with trace_block("AISProtocol.subscribe_message"):
            return {
                "APIKey": api_key,
                "BoundingBoxes": bounding_boxes or active_observation_bounding_boxes(),
                "FilterMessageTypes": [
                    "PositionReport",
                    "ShipStaticData",
                    "StaticDataReport",
                ],
            }

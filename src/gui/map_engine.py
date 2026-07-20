"""SAVE-108 map engine selection and render capability model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


BRIDGE_VERSION = 1


class BridgeVersionError(RuntimeError):
    """Raised when the JavaScript bridge reports an incompatible version."""


class MapEngineKind(StrEnum):
    CESIUM = "cesium"


@dataclass(frozen=True, slots=True)
class RenderCapabilities:
    supports_globe: bool = True
    supports_pitch: bool = True
    supports_heading: bool = True
    supports_geodesic: bool = True
    supports_terrain: bool = False
    engine_id: str = MapEngineKind.CESIUM


BRIDGE_ENTRY_POINTS: frozenset[str] = frozenset({
    "updateShips",
    "removeShip",
    "clearShips",
    "updateObservationPoints",
    "clearObservationPoints",
    "beginLocationPick",
    "endLocationPick",
    "refreshLocationPickView",
    "enablePickMode",
    "setPickMode",
    "setPickOverlay",
    "setPickMarker",
    "clearPickMarker",
    "resetMapToWorldView",
    "focusShip",
    "clearObservationPoint",
    "setObservationPoint",
    "updateCameras",
    "clearCameras",
    "beginHeadingPick",
    "endHeadingPick",
    "setCameraPreview",
})


def resolve_map_engine_kind() -> MapEngineKind:
    return MapEngineKind.CESIUM


def default_capabilities(
    kind: MapEngineKind | None = None,
) -> RenderCapabilities:
    _ = kind
    return RenderCapabilities(engine_id=MapEngineKind.CESIUM)


SUPPORTED_BRIDGE_VERSION = BRIDGE_VERSION


REQUIRED_CAPABILITY_KEYS: frozenset[str] = frozenset({
    "supports_globe",
    "supports_pitch",
    "supports_heading",
    "supports_geodesic",
    "supports_terrain",
    "engine_id",
})


def parse_render_capabilities(payload: dict[str, Any]) -> RenderCapabilities:
    return RenderCapabilities(
        supports_globe=bool(payload.get("supports_globe", False)),
        supports_pitch=bool(payload.get("supports_pitch", False)),
        supports_heading=bool(payload.get("supports_heading", False)),
        supports_geodesic=bool(payload.get("supports_geodesic", False)),
        supports_terrain=bool(payload.get("supports_terrain", False)),
        engine_id=str(payload.get("engine_id", MapEngineKind.CESIUM)),
    )


def validate_render_capabilities(payload: dict[str, Any]) -> RenderCapabilities:
    missing = REQUIRED_CAPABILITY_KEYS.difference(payload.keys())

    if missing:
        raise BridgeVersionError(
            "Map bridge capabilities object is missing required keys: "
            + ", ".join(sorted(missing))
        )

    engine_id = str(payload.get("engine_id", "")).strip()

    if not engine_id:
        raise BridgeVersionError(
            "Map bridge capabilities object has an empty engine_id."
        )

    return parse_render_capabilities(payload)


@dataclass(frozen=True, slots=True)
class RendererDiagnostics:
    fps: float = 0.0
    frame_time_ms: float = 0.0
    bridge_latency_ms: float = 0.0
    entity_counts: dict[str, int] = field(default_factory=dict)
    memory_estimate: int | None = None
    camera_state: dict[str, float] = field(default_factory=dict)
    transaction_queue_depth: int = 0


def parse_renderer_diagnostics(payload: dict[str, Any]) -> RendererDiagnostics:
    entity_counts = payload.get("entity_counts", {})
    camera_state = payload.get("camera_state", {})

    if not isinstance(entity_counts, dict):
        entity_counts = {}

    if not isinstance(camera_state, dict):
        camera_state = {}

    memory = payload.get("memory_estimate")

    return RendererDiagnostics(
        fps=float(payload.get("fps", 0.0)),
        frame_time_ms=float(payload.get("frame_time_ms", 0.0)),
        bridge_latency_ms=float(payload.get("bridge_latency_ms", 0.0)),
        entity_counts={
            str(key): int(value)
            for key, value in entity_counts.items()
            if isinstance(value, (int, float))
        },
        memory_estimate=int(memory) if isinstance(memory, (int, float)) else None,
        camera_state={
            str(key): float(value)
            for key, value in camera_state.items()
            if isinstance(value, (int, float))
        },
        transaction_queue_depth=int(payload.get("transaction_queue_depth", 0)),
    )


@dataclass(frozen=True, slots=True)
class RendererLifecycleState:
    state: str = "created"


def parse_renderer_lifecycle(payload: dict[str, Any]) -> RendererLifecycleState:
    return RendererLifecycleState(state=str(payload.get("state", "created")))


@dataclass(frozen=True, slots=True)
class BridgeInfo:
    version: int
    engine: str
    capabilities: RenderCapabilities
    entry_points: frozenset[str]


def parse_bridge_info(payload: dict[str, Any]) -> BridgeInfo:
    capabilities_payload = payload.get("capabilities", {})

    if not isinstance(capabilities_payload, dict):
        raise BridgeVersionError(
            "Map bridge capabilities payload is not an object."
        )

    entry_points_payload = payload.get("entry_points", [])

    if not isinstance(entry_points_payload, list):
        raise BridgeVersionError(
            "Map bridge entry_points payload is not a list."
        )

    return BridgeInfo(
        version=int(payload.get("version", 0)),
        engine=str(payload.get("engine", "")).strip(),
        capabilities=validate_render_capabilities(capabilities_payload),
        entry_points=frozenset(str(name) for name in entry_points_payload),
    )


def verify_bridge_info(
    info: BridgeInfo,
    *,
    expected_engine: MapEngineKind | None = None,
) -> None:
    if info.version != SUPPORTED_BRIDGE_VERSION:
        raise BridgeVersionError(
            "Incompatible map bridge version "
            f"{info.version} (expected {SUPPORTED_BRIDGE_VERSION}). "
            "The application and bundled map resources may be from "
            "different releases."
        )

    engine = expected_engine or resolve_map_engine_kind()

    if info.engine != engine.value:
        raise BridgeVersionError(
            "Map bridge engine mismatch: JavaScript reported "
            f"'{info.engine}' but the application selected "
            f"'{engine.value}'."
        )

    missing_entry_points = BRIDGE_ENTRY_POINTS.difference(info.entry_points)

    if missing_entry_points:
        raise BridgeVersionError(
            "Map bridge is missing required entry points: "
            + ", ".join(sorted(missing_entry_points))
        )

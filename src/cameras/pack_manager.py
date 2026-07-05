# ============================================================================
# Project X
# Camera Pack Manager
# ============================================================================

import json
import os
from dataclasses import dataclass
from pathlib import Path

from database.camera_registry import CameraRegistry, camera_registry

from app.paths import bundled_config_dir, is_frozen, runtime_config_path

CAMERA_PACKS_DIR = Path(
    os.environ.get(
        "PROJECTX_CAMERA_PACKS_DIR",
        str(bundled_config_dir() / "camera_packs"),
    )
)

_default_state = (
    runtime_config_path("camera_packs_state.json")
    if is_frozen()
    else bundled_config_dir() / "camera_packs" / "state.json"
)

CAMERA_PACKS_STATE_FILE = Path(
    os.environ.get(
        "PROJECTX_CAMERA_PACKS_STATE_FILE",
        str(_default_state),
    )
)

_REQUIRED_MANIFEST_FIELDS = (
    "id",
    "name",
    "version",
    "author",
    "description",
    "country",
    "camera_count",
)


@dataclass(frozen=True)
class CameraPack:

    id: str
    name: str
    version: str
    author: str
    description: str
    country: str
    camera_count: int
    enabled: bool


class CameraPackManager:

    def __init__(
        self,
        packs_dir: Path | None = None,
        state_file: Path | None = None,
        registry: CameraRegistry | None = None,
    ):

        self._packs_dir = Path(packs_dir or CAMERA_PACKS_DIR)
        self._state_file = Path(state_file or CAMERA_PACKS_STATE_FILE)
        self._registry = registry or camera_registry
        self._packs: dict[str, CameraPack] = {}
        self._enabled_ids: set[str] = set()

        self.reload()

    def discover_packs(self) -> list[CameraPack]:

        self._packs = self._scan_installed_packs()
        return self.installed_packs()

    def installed_packs(self) -> list[CameraPack]:

        return sorted(self._packs.values(), key=lambda pack: pack.id)

    def enabled_packs(self) -> list[CameraPack]:

        return [
            pack
            for pack in self.installed_packs()
            if pack.enabled
        ]

    def enable_pack(self, pack_id: str) -> bool:

        normalized_id = self._normalize_pack_id(pack_id)

        if normalized_id not in self._packs:
            return False

        self._enabled_ids.add(normalized_id)
        self._sync_pack_enabled_flags()
        self._save_state()
        return True

    def disable_pack(self, pack_id: str) -> bool:

        normalized_id = self._normalize_pack_id(pack_id)

        if normalized_id not in self._packs:
            return False

        self._enabled_ids.discard(normalized_id)
        self._sync_pack_enabled_flags()
        self._save_state()
        return True

    def reload(self) -> list[CameraPack]:

        self._enabled_ids = self._load_state()
        self._packs = self._scan_installed_packs()
        self._prune_unknown_pack_ids()
        self._sync_pack_enabled_flags()
        return self.installed_packs()

    def registry_camera_count(self, country: str | None = None) -> int:

        if country:
            return self._registry.count_by_country(country)

        return self._registry.count()

    def _scan_installed_packs(self) -> dict[str, CameraPack]:

        packs: dict[str, CameraPack] = {}

        if not self._packs_dir.is_dir():
            return packs

        for pack_dir in sorted(self._packs_dir.iterdir()):

            if not pack_dir.is_dir():
                continue

            if pack_dir.name.startswith("."):
                continue

            manifest_path = pack_dir / "manifest.json"

            if not manifest_path.is_file():
                continue

            pack = self._parse_manifest(manifest_path, pack_dir)

            if pack is None:
                continue

            if pack.id in packs:
                continue

            packs[pack.id] = pack

        return packs

    def _parse_manifest(
        self,
        manifest_path: Path,
        pack_dir: Path,
    ) -> CameraPack | None:

        try:
            with manifest_path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        if not self._has_required_manifest_fields(data):
            return None

        pack_id = str(data.get("id", "")).strip()

        if not pack_id:
            return None

        name = str(data.get("name", "")).strip()
        version = str(data.get("version", "")).strip()
        author = str(data.get("author", "")).strip()
        description = str(data.get("description", "")).strip()
        country = str(data.get("country", "")).strip().upper()

        if not all((name, version, author, description, country)):
            return None

        camera_count = self._resolve_camera_count(data)

        if camera_count is None:
            return None

        enabled = pack_id in self._enabled_ids

        return CameraPack(
            id=pack_id,
            name=name,
            version=version,
            author=author,
            description=description,
            country=country,
            camera_count=camera_count,
            enabled=enabled,
        )

    def _has_required_manifest_fields(self, data: dict) -> bool:

        for field_name in _REQUIRED_MANIFEST_FIELDS:
            if field_name not in data or data.get(field_name) in (None, ""):
                return False

        return True

    def _resolve_camera_count(self, data: dict) -> int | None:

        try:
            declared_count = int(data.get("camera_count"))
        except (TypeError, ValueError):
            return None

        if declared_count < 0:
            return None

        return declared_count

    def _load_state(self) -> set[str]:

        if not self._state_file.is_file():
            return set()

        try:
            with self._state_file.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return set()

        if not isinstance(data, dict):
            return set()

        enabled_ids: set[str] = set()

        for key in ("enabled_packs", "enabled"):
            values = data.get(key)

            if not isinstance(values, list):
                continue

            for item in values:
                normalized = self._normalize_pack_id(item)

                if normalized:
                    enabled_ids.add(normalized)

        return enabled_ids

    def _save_state(self) -> None:

        payload = {
            "enabled_packs": sorted(self._enabled_ids),
        }

        self._state_file.parent.mkdir(parents=True, exist_ok=True)

        with self._state_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")

    def _prune_unknown_pack_ids(self) -> None:

        known_ids = set(self._packs.keys())
        pruned = self._enabled_ids & known_ids

        if pruned != self._enabled_ids:
            self._enabled_ids = pruned
            self._save_state()

    def _sync_pack_enabled_flags(self) -> None:

        updated: dict[str, CameraPack] = {}

        for pack_id, pack in self._packs.items():
            enabled = pack_id in self._enabled_ids
            updated[pack_id] = CameraPack(
                id=pack.id,
                name=pack.name,
                version=pack.version,
                author=pack.author,
                description=pack.description,
                country=pack.country,
                camera_count=pack.camera_count,
                enabled=enabled,
            )

        self._packs = updated

    @staticmethod
    def _normalize_pack_id(pack_id: str | None) -> str:

        if pack_id is None:
            return ""

        return str(pack_id).strip()


camera_pack_manager = CameraPackManager()

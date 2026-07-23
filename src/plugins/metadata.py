# ============================================================================
# Project X
# Plugin Framework — metadata (SAVE-212)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


PLUGIN_API_VERSION = "1.0.0"


@dataclass(frozen=True)
class PluginMetadata:
    """Declarative plugin identity and packaging metadata."""

    id: str
    name: str
    version: str
    author: str = ""
    description: str = ""
    api_version: str = PLUGIN_API_VERSION
    entry: str = ""
    dependencies: dict[str, str] = field(default_factory=dict)
    homepage: str = ""
    license: str = ""
    path: Path | None = None

    @classmethod
    def from_dict(cls, data: dict, *, path: Path | None = None) -> "PluginMetadata":

        if not isinstance(data, dict):
            data = {}

        raw_deps = data.get("dependencies") or {}
        dependencies: dict[str, str] = {}

        if isinstance(raw_deps, dict):
            for key, value in raw_deps.items():
                dep_id = str(key).strip()
                if dep_id:
                    dependencies[dep_id] = str(value).strip() or ">=0"
        elif isinstance(raw_deps, list):
            for item in raw_deps:
                dep_id = str(item).strip()
                if dep_id:
                    dependencies[dep_id] = ">=0"

        plugin_id = str(data.get("id") or data.get("plugin_id") or "").strip()
        name = str(data.get("name") or plugin_id or "Unnamed Plugin").strip()

        return cls(
            id=plugin_id,
            name=name,
            version=str(data.get("version") or "0.0.0").strip() or "0.0.0",
            author=str(data.get("author") or "").strip(),
            description=str(data.get("description") or "").strip(),
            api_version=str(
                data.get("api_version") or PLUGIN_API_VERSION
            ).strip()
            or PLUGIN_API_VERSION,
            entry=str(data.get("entry") or data.get("entrypoint") or "").strip(),
            dependencies=dependencies,
            homepage=str(data.get("homepage") or "").strip(),
            license=str(data.get("license") or "").strip(),
            path=path,
        )

    def to_dict(self) -> dict:

        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "api_version": self.api_version,
            "entry": self.entry,
            "dependencies": dict(self.dependencies),
            "homepage": self.homepage,
            "license": self.license,
        }

# ============================================================================
# Project X
# Data Root Validation Service (SAVE-107-C2)
# ============================================================================

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.paths import bundle_dir, is_frozen
from storage.layout import DATA_ROOT_MARKER_NAME, STANDARD_DATA_SUBDIRS
from storage.marker import find_marked_data_root, is_valid_data_root

_FORBIDDEN_PREFIXES = (
    Path("/opt/projectx"),
)
_LONG_PATH_WARNING_LENGTH = 240


class ValidationSeverity(str, Enum):
    """Validation outcome severity for wizard and settings flows."""

    NONE = "none"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class DataRootValidationResult:
    """Outcome of validating a candidate Project X data root location."""

    path: Path
    valid: bool
    severity: ValidationSeverity
    message: str = ""

    @property
    def blocks_completion(self) -> bool:
        return self.severity == ValidationSeverity.ERROR

    @classmethod
    def error(cls, path: Path, message: str) -> DataRootValidationResult:
        return cls(
            path=path,
            valid=False,
            severity=ValidationSeverity.ERROR,
            message=message,
        )

    @classmethod
    def warning(cls, path: Path, message: str) -> DataRootValidationResult:
        return cls(
            path=path,
            valid=True,
            severity=ValidationSeverity.WARNING,
            message=message,
        )

    @classmethod
    def ok(cls, path: Path) -> DataRootValidationResult:
        return cls(
            path=path,
            valid=True,
            severity=ValidationSeverity.NONE,
            message="",
        )


class DataRootValidationService:
    """Validate candidate user data directories for first-run setup."""

    def validate(
        self,
        path: Path,
        *,
        allow_existing_root: bool = False,
    ) -> DataRootValidationResult:
        """Return whether a path can be used as a new Project X data root."""

        candidate = Path(path).expanduser()

        if not str(candidate).strip():
            return DataRootValidationResult.error(
                candidate,
                "A folder must be selected.",
            )

        if _is_forbidden_install_path(candidate):
            return DataRootValidationResult.error(
                candidate,
                "Project X cannot store data inside the application install folder.",
            )

        if _is_temporary_or_system_path(candidate):
            return DataRootValidationResult.error(
                candidate,
                "Project X cannot store data in a temporary or system folder.",
            )

        if not allow_existing_root:
            marker_issue = _marker_conflict_message(candidate)
            if marker_issue is not None:
                return DataRootValidationResult.error(candidate, marker_issue)

        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return DataRootValidationResult.error(
                candidate,
                f"Could not create the selected folder: {exc}",
            )

        resolved = candidate.resolve()

        if not allow_existing_root:
            marker_issue = _marker_conflict_message(resolved)
            if marker_issue is not None:
                return DataRootValidationResult.error(resolved, marker_issue)

        try:
            with tempfile.NamedTemporaryFile(
                dir=resolved,
                prefix=".projectx-write-test-",
                delete=True,
            ):
                pass
        except OSError as exc:
            return DataRootValidationResult.error(
                resolved,
                f"The selected folder is not writable: {exc}",
            )

        if is_valid_data_root(resolved):
            return DataRootValidationResult.ok(resolved)

        warning_message = _warning_message(resolved)
        if warning_message:
            return DataRootValidationResult.warning(resolved, warning_message)

        return DataRootValidationResult.ok(resolved)


def _warning_message(path: Path) -> str | None:
    warnings = _collect_warnings(path)

    if not warnings:
        return None

    return " ".join(warnings)


def _collect_warnings(path: Path) -> list[str]:
    warnings: list[str] = []

    if path.is_dir():
        entries = [
            entry
            for entry in path.iterdir()
            if entry.name != DATA_ROOT_MARKER_NAME
        ]

        if entries:
            warnings.append("The selected folder is not empty.")

        if _has_unrelated_entries(entries):
            warnings.append(
                "The selected folder already contains unrelated files."
            )

    if len(str(path)) >= _LONG_PATH_WARNING_LENGTH:
        warnings.append(
            f"The selected path is very long ({len(str(path))} characters)."
        )

    return warnings


def _has_unrelated_entries(entries: list[Path]) -> bool:
    standard_names = set(STANDARD_DATA_SUBDIRS)

    for entry in entries:
        if entry.is_file():
            return True

        if entry.is_dir() and entry.name not in standard_names:
            return True

    return False


def _marker_conflict_message(path: Path) -> str | None:
    if is_valid_data_root(path):
        return None

    marked_root = find_marked_data_root(path)
    if marked_root is not None:
        return "The selected folder is inside an existing Project X data location."

    if path.is_dir():
        nested_root = _find_nested_marked_data_root(path)
        if nested_root is not None:
            return "The selected folder already contains a Project X data location."

    return None


def _find_nested_marked_data_root(path: Path) -> Path | None:
    for marker_file in path.rglob(DATA_ROOT_MARKER_NAME):
        if not marker_file.is_file():
            continue

        data_root = marker_file.parent
        if is_valid_data_root(data_root):
            return data_root

    return None


def _is_forbidden_install_path(path: Path) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        resolved = path.expanduser()

    for prefix in _FORBIDDEN_PREFIXES:
        try:
            resolved.relative_to(prefix.resolve())
            return True
        except ValueError:
            continue

    if is_frozen():
        bundle = bundle_dir().resolve()

        try:
            resolved.relative_to(bundle)
            return True
        except ValueError:
            pass

    return False


def _is_temporary_or_system_path(path: Path) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except OSError:
        resolved = path.expanduser()

    for root in _temporary_and_system_roots():
        if _is_same_or_under(resolved, root):
            return True

    return False


def _temporary_and_system_roots() -> tuple[Path, ...]:
    candidates: list[Path] = []

    for env_name in ("TMPDIR", "TEMP", "TMP"):
        value = os.environ.get(env_name, "").strip()
        if value:
            candidates.append(Path(value).expanduser())

    candidates.append(Path(tempfile.gettempdir()))

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
        if local_app_data:
            candidates.append(Path(local_app_data) / "Temp")
        candidates.append(Path("C:/Windows/Temp"))
    else:
        candidates.extend(
            [
                Path("/tmp"),
                Path("/var/tmp"),
                Path("/dev/shm"),
                Path("/proc"),
                Path("/sys"),
                Path("/dev"),
                Path("/run"),
            ]
        )

    roots: list[Path] = []
    seen: set[str] = set()

    for candidate in candidates:
        if not str(candidate).strip():
            continue

        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            resolved = candidate.expanduser()

        key = str(resolved)
        if key in seen:
            continue

        seen.add(key)
        roots.append(resolved)

    return tuple(roots)


def _is_same_or_under(path: Path, root: Path) -> bool:
    try:
        if path == root:
            return True
        path.relative_to(root)
        return True
    except ValueError:
        return False

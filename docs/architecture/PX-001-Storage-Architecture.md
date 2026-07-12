# PX-001 — Storage Architecture

**Status:** Accepted

**Version:** 1.0

**Project:** Project X

---

# 1. Purpose

The Storage subsystem is the single authority responsible for locating,
creating, validating and managing every writable resource used by Project X.

No feature module may calculate writable filesystem paths on its own.

The storage layer abstracts operating system differences and guarantees
consistent behaviour across Windows, Linux, AppImage and future platforms.

---

# 2. Design Principles

- Single source of truth.
- Cross-platform.
- Installer-safe.
- Portable-ready.
- Future-proof.
- Zero duplicated path logic.

---

# 3. Architecture

Project X separates resources into two categories.

## Read Only

The application may read but never write to:

- resources/
- branding/
- translations/
- leaflet/
- camera packs/
- html/
- css/
- javascript/

These locations belong to the application installation.

---

## Read Write

All writable runtime data belongs to the user profile.

Windows:

%APPDATA%/Project X/

Linux:

~/.local/share/projectx/

No writable data may ever exist inside the installation directory.

---

# 4. Storage Manager

A single Storage Manager is responsible for every writable directory.

Example API:

storage.config()

storage.database()

storage.photos()

storage.timeline()

storage.cache()

storage.logbook()

storage.exports()

storage.temp()

Modules must never calculate filesystem paths.

---

# 5. Responsibilities

Storage Manager shall:

- create missing folders
- verify write permissions
- migrate legacy locations
- expose platform specific paths
- log storage locations
- guarantee directory existence

---

# 6. Forbidden

The following patterns are forbidden inside feature modules.

Path(...)

os.path.join(...)

runtime_data_dir() / ...

Any writable filesystem calculation outside Storage Manager.

---

# 7. Migration

Legacy code shall be migrated gradually.

Each subsystem will switch to Storage Manager independently.

Backward compatibility shall be maintained during migration.

---

# 8. Future

Storage Manager is designed to support:

- Portable installations
- External storage
- Cloud synchronization
- Encrypted storage
- User-defined locations

without requiring changes in feature modules.

---

# 9. Status

This document defines the official Project X Storage Architecture.

All future development shall comply with this specification.
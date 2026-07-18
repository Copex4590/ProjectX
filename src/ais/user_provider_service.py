# ============================================================================
# Project X
# User AIS Provider State (shared source of truth)
# ============================================================================

from __future__ import annotations

from dataclasses import dataclass

from ais.ais_manager import ais_manager
from ais.providers import AISProviderType, normalize_provider_type
from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from events import eventbus
from i18n import tr
from preferences import preferences_manager
from rtl import rtl_manager

_PROVIDER_LABEL_KEYS = {
    AISProviderType.AISSTREAM.value: "AISStream",
    AISProviderType.LOCAL.value: "RTL-SDR",
    AISProviderType.MARINE_TRAFFIC.value: "MarineTraffic",
    AISProviderType.AISHUB.value: "AISHub",
}

_PROVIDER_DISPLAY_ORDER = (
    AISProviderType.AISSTREAM,
    AISProviderType.LOCAL,
    AISProviderType.MARINE_TRAFFIC,
    AISProviderType.AISHUB,
)


@dataclass(frozen=True)
class ProviderStatus:
    icon: str
    text: str


@dataclass(frozen=True)
class ProviderSnapshot:
    provider_id: str
    provider: AISProviderType
    label_key: str
    configured: bool
    connection_status: str
    status: ProviderStatus
    api_key: str
    host: str
    port: int
    rtl_configured: bool
    rtl_auto_start: bool


def notify_providers_changed() -> None:

    eventbus.publish("providers.changed")


def provider_label_key(provider_id: str) -> str:

    provider = normalize_provider_type(provider_id)
    return _PROVIDER_LABEL_KEYS.get(provider.value, provider.value)


def derive_enabled_providers(provider: AISProviderType) -> list[str]:

    if provider == AISProviderType.HYBRID:
        return [
            AISProviderType.AISSTREAM.value,
            AISProviderType.LOCAL.value,
        ]

    if provider == AISProviderType.LATER:
        return []

    return [provider.value]


def legacy_provider_from_enabled(enabled: set[AISProviderType]) -> str:

    if not enabled:
        return AISProviderType.LATER.value

    has_stream = AISProviderType.AISSTREAM in enabled
    has_local = AISProviderType.LOCAL in enabled

    if has_stream and has_local:
        return AISProviderType.HYBRID.value

    if has_local:
        return AISProviderType.LOCAL.value

    if has_stream:
        return AISProviderType.AISSTREAM.value

    return AISProviderType.LATER.value


def get_enabled_provider_ids() -> list[str]:

    preferences = preferences_manager.get()
    enabled_values = preferences.ais_enabled_providers

    if enabled_values is not None:
        return [str(value).strip() for value in enabled_values if str(value).strip()]

    provider = normalize_provider_type(preferences.ais_provider)
    return derive_enabled_providers(provider)


def ordered_provider_ids(provider_ids: list[str] | None = None) -> list[str]:

    source = provider_ids if provider_ids is not None else get_enabled_provider_ids()
    normalized = {
        normalize_provider_type(provider_id).value for provider_id in source
    }

    ordered: list[str] = []

    for provider in _PROVIDER_DISPLAY_ORDER:
        if provider.value in normalized:
            ordered.append(provider.value)

    for provider_id in source:
        normalized_id = normalize_provider_type(provider_id).value

        if normalized_id not in ordered:
            ordered.append(normalized_id)

    return ordered


def is_provider_configured(provider: AISProviderType) -> bool:

    preferences = preferences_manager.get()

    if provider == AISProviderType.AISSTREAM:
        return bool(preferences.aisstream_api_key.strip())

    if provider == AISProviderType.LOCAL:
        return bool(preferences.rtl_sdr_configured)

    if provider in (AISProviderType.MARINE_TRAFFIC, AISProviderType.AISHUB):
        return False

    return False


def provider_connection_status(provider_id: str) -> str:

    provider = normalize_provider_type(provider_id)

    if provider == AISProviderType.AISSTREAM:
        return ais_manager.ais_connection_status()

    if provider == AISProviderType.LOCAL:
        return rtl_manager.rtl_connection_status()

    return "offline"


def provider_display_status(provider_id: str) -> ProviderStatus:

    provider = normalize_provider_type(provider_id)

    if not is_provider_configured(provider):
        icon = "⚪" if provider == AISProviderType.LOCAL else "🟡"
        return ProviderStatus(icon, tr("Not configured"))

    if provider_connection_status(provider_id) == "connected":
        return ProviderStatus("🟢", tr("Connected"))

    return ProviderStatus("🔴", tr("Disconnected"))


def get_provider_snapshot(provider_id: str) -> ProviderSnapshot:

    provider = normalize_provider_type(provider_id)
    preferences = preferences_manager.get()

    return ProviderSnapshot(
        provider_id=provider.value,
        provider=provider,
        label_key=provider_label_key(provider_id),
        configured=is_provider_configured(provider),
        connection_status=provider_connection_status(provider_id),
        status=provider_display_status(provider_id),
        api_key=preferences.aisstream_api_key,
        host=preferences.ais_local_host or AIS_CATCHER_HOST,
        port=int(preferences.ais_local_port or AIS_CATCHER_PORT),
        rtl_configured=bool(preferences.rtl_sdr_configured),
        rtl_auto_start=bool(preferences.rtl_auto_start_ais_catcher),
    )


def set_enabled_providers(enabled: set[AISProviderType]) -> None:

    legacy_provider = legacy_provider_from_enabled(enabled)
    preferences_manager.set_ais_enabled_providers(
        [provider.value for provider in enabled],
        legacy_provider=legacy_provider,
    )

    if not enabled:
        ais_manager.save_configuration(
            provider_type=AISProviderType.LATER.value,
            configured=False,
        )

    notify_providers_changed()


def save_aisstream_configuration(api_key: str) -> None:

    preferences = preferences_manager.get()
    legacy_provider = legacy_provider_from_enabled(
        {normalize_provider_type(value) for value in get_enabled_provider_ids()}
    )

    ais_manager.save_configuration(
        provider_type=legacy_provider,
        api_key=str(api_key).strip(),
        host=preferences.ais_local_host,
        port=preferences.ais_local_port,
        configured=bool(str(api_key).strip()),
    )
    notify_providers_changed()


def save_local_configuration(
    *,
    host: str,
    port: int,
    auto_start: bool | None = None,
) -> None:

    preferences = preferences_manager.get()

    if auto_start is not None:
        preferences_manager.set_rtl_configuration(auto_start_ais_catcher=auto_start)

    legacy_provider = legacy_provider_from_enabled(
        {normalize_provider_type(value) for value in get_enabled_provider_ids()}
    )

    ais_manager.save_configuration(
        provider_type=legacy_provider,
        api_key=preferences.aisstream_api_key,
        host=str(host).strip() or AIS_CATCHER_HOST,
        port=int(port or AIS_CATCHER_PORT),
        configured=bool(preferences.rtl_sdr_configured or preferences.ais_configured),
    )
    notify_providers_changed()


def remove_provider(provider_id: str) -> None:

    provider = normalize_provider_type(provider_id)
    remaining = {
        normalize_provider_type(value)
        for value in get_enabled_provider_ids()
        if normalize_provider_type(value) != provider
    }

    set_enabled_providers(remaining)

    preferences = preferences_manager.get()
    legacy_provider = legacy_provider_from_enabled(remaining)

    if provider == AISProviderType.AISSTREAM:
        ais_manager.save_configuration(
            provider_type=legacy_provider,
            api_key="",
            host=preferences.ais_local_host,
            port=preferences.ais_local_port,
            configured=bool(remaining) and preferences.ais_configured,
        )

    if provider == AISProviderType.LOCAL:
        preferences_manager.set_rtl_configuration(
            configured=False,
            setup_completed=False,
        )
        preferences = preferences_manager.get()
        legacy_provider = legacy_provider_from_enabled(remaining)
        ais_manager.save_configuration(
            provider_type=legacy_provider,
            api_key=preferences.aisstream_api_key,
            host=preferences.ais_local_host,
            port=preferences.ais_local_port,
            configured=bool(remaining) and bool(preferences.aisstream_api_key.strip()),
        )

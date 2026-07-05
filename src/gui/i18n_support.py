# ============================================================================
# Project X
# GUI Localization Support
# ============================================================================

from i18n import language_manager


def bind_language_refresh(refresh_method) -> None:

    language_manager.language_changed.connect(
        lambda _code: refresh_method()
    )

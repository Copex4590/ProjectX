# ============================================================================
# Project X
# Translator
# ============================================================================

from i18n.language_manager import language_manager


def tr(key: str) -> str:

    return language_manager.translate(key)

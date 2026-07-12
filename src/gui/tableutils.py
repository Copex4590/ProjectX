# ============================================================================
# Project X
# Table Utilities
# ============================================================================

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from gui.theme import TEXT_MUTED
from i18n import tr

_EMPTY_ROW_HEIGHT = 44


def show_empty_table_message(
    table: QTableWidget,
    message_key: str,
    *,
    column_count: int | None = None,
) -> None:

    columns = column_count or table.columnCount()
    sorting_enabled = table.isSortingEnabled()
    table.setSortingEnabled(False)
    table.setRowCount(1)
    table.setRowHeight(0, _EMPTY_ROW_HEIGHT)

    item = QTableWidgetItem(tr(message_key))
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    item.setTextAlignment(
        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
    )
    item.setForeground(QColor(TEXT_MUTED))
    table.setItem(0, 0, item)

    if columns > 1:
        table.setSpan(0, 0, 1, columns)

    table.setSortingEnabled(sorting_enabled)

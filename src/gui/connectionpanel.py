from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)

from gui.i18n_support import bind_language_refresh
from gui.theme import BG_BASE, BORDER
from i18n import tr


class ConnectionPanel(QFrame):

    _LABEL_KEYS = (
        ("internet", "Internet", "🟢"),
        ("ais", "AISStream", "⚪"),
        ("rtl", "RTL Receiver", "⚪"),
        ("gps", "GPS", "⚪"),
        ("camera", "Camera", "⚪"),
        ("database", "Database", "⚪"),
        ("api", "API", "⚪"),
    )

    def __init__(self):
        super().__init__()

        self._ais_status = "disconnected"
        self._rtl_status = "disconnected"

        self.setFixedWidth(240)

        self.setStyleSheet(f"""
            QFrame{{
                background:{BG_BASE};
                border-left:1px solid {BORDER};
            }}

            QLabel{{
                color:white;
                padding:6px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        self._title_label = QLabel(tr("Connections"))
        self._title_label.setStyleSheet("""
            font-size:14pt;
            font-weight:bold;
        """)

        layout.addWidget(self._title_label)

        self.internet = QLabel()
        self.ais = QLabel()
        self.rtl = QLabel()
        self.gps = QLabel()
        self.camera = QLabel()
        self.database = QLabel()
        self.api = QLabel()

        layout.addWidget(self.internet)
        layout.addWidget(self.ais)
        layout.addWidget(self.rtl)
        layout.addWidget(self.gps)
        layout.addWidget(self.camera)
        layout.addWidget(self.database)
        layout.addWidget(self.api)

        layout.addStretch()

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    @staticmethod
    def _status_icon(status: str) -> str:

        if status == "connected":
            return "🟢"
        if status in {"connecting", "waiting"}:
            return "🟡"
        return "⚪"

    def _set_connection_label(
        self,
        widget: QLabel,
        label_key: str,
        status: str | None = None,
        default_icon: str | None = None,
    ) -> None:

        icon = (
            self._status_icon(status)
            if status is not None
            else default_icon
        )
        widget.setText(f"{icon} {tr(label_key)}")

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Connections"))

        for attr, label_key, default_icon in self._LABEL_KEYS:
            widget = getattr(self, attr)
            if attr == "ais":
                self._set_connection_label(
                    widget, label_key, self._ais_status
                )
            elif attr == "rtl":
                self._set_connection_label(
                    widget, label_key, self._rtl_status
                )
            else:
                self._set_connection_label(
                    widget, label_key, default_icon=default_icon
                )

    def on_ais_status(self, status):

        self._ais_status = status
        self._set_connection_label(self.ais, "AISStream", status)

    def on_rtl_status(self, status):

        self._rtl_status = status
        self._set_connection_label(self.rtl, "RTL Receiver", status)

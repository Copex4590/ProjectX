from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from gui.i18n_support import bind_language_refresh
from i18n import tr
from observation.observation_point import ObservationPoint


class ObservationReferenceDialog(QDialog):

    def __init__(
        self,
        points: list[ObservationPoint],
        parent=None,
    ):
        super().__init__(parent)

        self._points = list(points)
        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def selected_point_id(self) -> str | None:

        index = self._selector.currentIndex()

        if index < 0 or index >= len(self._points):
            return None

        return self._points[index].id

    def _build_ui(self) -> None:

        layout = QVBoxLayout(self)

        self._intro_label = QLabel()
        self._intro_label.setWordWrap(True)
        layout.addWidget(self._intro_label)

        form = QFormLayout()
        self._selector_label = QLabel()
        self._selector = QComboBox()

        for point in self._points:
            self._selector.addItem(point.name, point.id)

        form.addRow(self._selector_label, self._selector)
        layout.addLayout(form)

        self._button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        layout.addWidget(self._button_box)

        self._button_box.accepted.connect(self.accept)
        self._button_box.rejected.connect(self.reject)

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Reference Observation Point"))
        self._intro_label.setText(
            tr(
                "Multiple observation points are active. "
                "Choose which one to use for distance and bearing calculations."
            )
        )
        self._selector_label.setText(tr("Reference point"))
        self._button_box.button(QDialogButtonBox.StandardButton.Ok).setText(
            tr("Confirm")
        )
        self._button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        ).setText(tr("Cancel"))

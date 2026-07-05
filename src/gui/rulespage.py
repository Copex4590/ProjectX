# ============================================================================
# Project X
# Rule Management Page
# ============================================================================

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from alerts.alert_manager import AlertManager, alert_manager
from alerts.alert_rule import (
    RULE_TYPE_ARRIVAL,
    RULE_TYPE_CAMERA_LOST,
    RULE_TYPE_CAMERA_VISIBLE,
    RULE_TYPE_DEPARTURE,
    RULE_TYPE_ENTER_REGION,
    RULE_TYPE_EXIT_REGION,
    RULE_TYPE_SPEED_OVER,
    SUPPORTED_RULE_TYPES,
    AlertRule,
)
from gui.i18n_support import bind_language_refresh
from gui.tableutils import show_empty_table_message
from i18n import tr

_SEVERITY_INFO = "info"
_SEVERITY_WARNING = "warning"
_SEVERITY_CRITICAL = "critical"

_SEVERITY_OPTIONS = (
    _SEVERITY_INFO,
    _SEVERITY_WARNING,
    _SEVERITY_CRITICAL,
)

_SEVERITY_PRIORITY = {
    _SEVERITY_INFO: 25,
    _SEVERITY_WARNING: 60,
    _SEVERITY_CRITICAL: 85,
}


def _display_text(value: str | None) -> str:

    text = str(value or "").strip()

    if text:
        return text

    return "—"


def _format_timestamp(value: datetime | None) -> str:

    if value is None:
        return "—"

    return value.strftime("%Y-%m-%d %H:%M:%S")


def _tr_severity(value: str | None) -> str:

    text = str(value or "").strip()

    if not text:
        return "—"

    if text in _SEVERITY_OPTIONS:
        return tr(text)

    return text


def _tr_event_type(value: str | None) -> str:

    text = str(value or "").strip()

    if not text:
        return "—"

    return tr(text)


def _severity_from_priority(priority: int) -> str:

    if priority >= 80:
        return _SEVERITY_CRITICAL

    if priority >= 50:
        return _SEVERITY_WARNING

    return _SEVERITY_INFO


def _parse_optional_int(value: str) -> int | None:

    text = str(value or "").strip()

    if not text:
        return None

    try:
        parsed = int(text)
    except ValueError:
        return None

    if parsed <= 0:
        return None

    return parsed


class RuleEditorDialog(QDialog):

    def __init__(self, rule: AlertRule | None = None, parent=None):
        super().__init__(parent)

        self._rule = rule
        self._saved_rule: AlertRule | None = None

        self.setWindowTitle(
            tr("Edit Rule") if rule else tr("New Rule")
        )
        self.setModal(True)
        self.resize(520, 420)
        self._build_ui()
        self._load_rule(rule)
        bind_language_refresh(self.refresh_translations)

    def validated_rule(self) -> AlertRule | None:

        return self._saved_rule

    def _build_ui(self) -> None:

        self.setStyleSheet("""
            QDialog, QWidget {
                background: #1d2127;
                color: white;
            }

            QLabel[role="field"] {
                color: #d5dbe3;
                font-weight: 600;
            }

            QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background: #252a31;
                color: white;
                border: 1px solid #40444b;
                border-radius: 6px;
                padding: 6px 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_input = QLineEdit()
        self._name_label = self._field_label(tr("Name"))
        form.addRow(self._name_label, self.name_input)

        self.enabled_checkbox = QCheckBox(tr("Enabled"))
        self._enabled_label = self._field_label(tr("Enabled"))
        form.addRow(self._enabled_label, self.enabled_checkbox)

        self.priority_input = QSpinBox()
        self.priority_input.setRange(0, 100)
        self._priority_label = self._field_label(tr("Priority"))
        form.addRow(self._priority_label, self.priority_input)

        self.severity_combo = QComboBox()
        self._populate_severity_combo()
        self._severity_label = self._field_label(tr("Severity"))
        form.addRow(self._severity_label, self.severity_combo)

        self.event_type_combo = QComboBox()
        self._populate_event_type_combo()
        self._event_type_label = self._field_label(tr("Event Type"))
        form.addRow(self._event_type_label, self.event_type_combo)

        layout.addLayout(form)

        self.conditions_stack = QStackedWidget()
        self._condition_pages: dict[str, QWidget] = {}

        for event_type in SUPPORTED_RULE_TYPES:
            page = self._build_condition_page(event_type)
            self._condition_pages[event_type] = page
            self.conditions_stack.addWidget(page)

        layout.addWidget(self.conditions_stack)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self._save_button = buttons.button(
            QDialogButtonBox.StandardButton.Save
        )
        self._cancel_button = buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self._save_button.setText(tr("Save"))
        self._cancel_button.setText(tr("Cancel"))
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.severity_combo.currentIndexChanged.connect(
            self._on_severity_changed
        )
        self.priority_input.valueChanged.connect(
            self._on_priority_changed
        )
        self.event_type_combo.currentIndexChanged.connect(
            self._on_event_type_changed
        )

        self.enabled_checkbox.setChecked(True)

    def _field_label(self, text: str) -> QLabel:

        label = QLabel(text)
        label.setProperty("role", "field")
        return label

    def _populate_severity_combo(self) -> None:

        current = self.severity_combo.currentData()

        self.severity_combo.blockSignals(True)
        self.severity_combo.clear()

        for value in _SEVERITY_OPTIONS:
            self.severity_combo.addItem(tr(value), value)

        index = self.severity_combo.findData(current or _SEVERITY_INFO)

        if index < 0:
            index = 0

        self.severity_combo.setCurrentIndex(index)
        self.severity_combo.blockSignals(False)

    def _populate_event_type_combo(self) -> None:

        current = self.event_type_combo.currentData()

        self.event_type_combo.blockSignals(True)
        self.event_type_combo.clear()

        for value in SUPPORTED_RULE_TYPES:
            self.event_type_combo.addItem(tr(value), value)

        index = self.event_type_combo.findData(
            current or SUPPORTED_RULE_TYPES[0]
        )

        if index < 0:
            index = 0

        self.event_type_combo.setCurrentIndex(index)
        self.event_type_combo.blockSignals(False)

    def refresh_translations(self) -> None:

        self.setWindowTitle(
            tr("Edit Rule") if self._rule else tr("New Rule")
        )
        self._name_label.setText(tr("Name"))
        self._enabled_label.setText(tr("Enabled"))
        self.enabled_checkbox.setText(tr("Enabled"))
        self._priority_label.setText(tr("Priority"))
        self._severity_label.setText(tr("Severity"))
        self._event_type_label.setText(tr("Event Type"))

        self._save_button.setText(tr("Save"))
        self._cancel_button.setText(tr("Cancel"))

        self._populate_severity_combo()
        self._populate_event_type_combo()

        for event_type, page in self._condition_pages.items():
            self._refresh_condition_page_labels(page)

        current_event_type = self.event_type_combo.currentData()
        self._on_event_type_changed(current_event_type)

    def _build_condition_page(self, event_type: str) -> QWidget:

        page = QWidget()
        form = QFormLayout(page)
        form.setSpacing(8)
        page._field_labels = {}

        message_input = QLineEdit()
        message_input.setPlaceholderText(tr("Optional alert message"))
        message_label = self._field_label(tr("Message"))
        form.addRow(message_label, message_input)
        page._field_labels["Message"] = message_label
        setattr(page, "message_input", message_input)

        if event_type in {
            RULE_TYPE_ARRIVAL,
            RULE_TYPE_DEPARTURE,
            RULE_TYPE_SPEED_OVER,
        }:
            mmsi_input = QLineEdit()
            mmsi_input.setPlaceholderText(tr("Optional MMSI filter"))
            mmsi_label = self._field_label(tr("MMSI"))
            form.addRow(mmsi_label, mmsi_input)
            page._field_labels["MMSI"] = mmsi_label
            setattr(page, "mmsi_input", mmsi_input)

        if event_type == RULE_TYPE_SPEED_OVER:
            speed_input = QDoubleSpinBox()
            speed_input.setRange(0.1, 100.0)
            speed_input.setDecimals(1)
            speed_input.setValue(12.0)
            speed_label = self._field_label(tr("Speed Limit"))
            form.addRow(speed_label, speed_input)
            page._field_labels["Speed Limit"] = speed_label
            setattr(page, "speed_input", speed_input)

        if event_type in {RULE_TYPE_ENTER_REGION, RULE_TYPE_EXIT_REGION}:
            latitude_input = QDoubleSpinBox()
            latitude_input.setRange(-90.0, 90.0)
            latitude_input.setDecimals(5)
            latitude_input.setValue(47.5)
            latitude_label = self._field_label(tr("Latitude"))
            form.addRow(latitude_label, latitude_input)
            page._field_labels["Latitude"] = latitude_label
            setattr(page, "latitude_input", latitude_input)

            longitude_input = QDoubleSpinBox()
            longitude_input.setRange(-180.0, 180.0)
            longitude_input.setDecimals(5)
            longitude_input.setValue(19.0)
            longitude_label = self._field_label(tr("Longitude"))
            form.addRow(longitude_label, longitude_input)
            page._field_labels["Longitude"] = longitude_label
            setattr(page, "longitude_input", longitude_input)

            radius_input = QDoubleSpinBox()
            radius_input.setRange(0.1, 5000.0)
            radius_input.setDecimals(1)
            radius_input.setValue(10.0)
            radius_label = self._field_label(tr("Radius (km)"))
            form.addRow(radius_label, radius_input)
            page._field_labels["Radius (km)"] = radius_label
            setattr(page, "radius_input", radius_input)

        return page

    def _refresh_condition_page_labels(self, page: QWidget) -> None:

        page.message_input.setPlaceholderText(tr("Optional alert message"))

        for key, label in page._field_labels.items():
            label.setText(tr(key))

        if hasattr(page, "mmsi_input"):
            page.mmsi_input.setPlaceholderText(tr("Optional MMSI filter"))

    def _on_severity_changed(self, _index: int) -> None:

        severity = self.severity_combo.currentData() or _SEVERITY_INFO
        priority = _SEVERITY_PRIORITY.get(severity, 25)
        self.priority_input.blockSignals(True)
        self.priority_input.setValue(priority)
        self.priority_input.blockSignals(False)

    def _on_priority_changed(self, priority: int) -> None:

        severity = _severity_from_priority(priority)
        self.severity_combo.blockSignals(True)
        index = self.severity_combo.findData(severity)

        if index >= 0:
            self.severity_combo.setCurrentIndex(index)

        self.severity_combo.blockSignals(False)

    def _on_event_type_changed(self, _index_or_type) -> None:

        if isinstance(_index_or_type, int):
            event_type = self.event_type_combo.currentData()
        else:
            event_type = _index_or_type

        page = self._condition_pages.get(event_type)

        if page is not None:
            self.conditions_stack.setCurrentWidget(page)

    def _load_rule(self, rule: AlertRule | None) -> None:

        if rule is None:
            self._on_event_type_changed(
                self.event_type_combo.currentData()
            )
            self._on_severity_changed(self.severity_combo.currentIndex())
            return

        self.name_input.setText(rule.name)
        self.enabled_checkbox.setChecked(bool(rule.enabled))
        self.priority_input.setValue(int(rule.priority))
        self._on_priority_changed(int(rule.priority))

        index = self.event_type_combo.findData(rule.event_type)

        if index >= 0:
            self.event_type_combo.setCurrentIndex(index)

        self._on_event_type_changed(rule.event_type)
        self._load_conditions(rule.event_type, rule.conditions or {})

    def _load_conditions(self, event_type: str, conditions: dict) -> None:

        page = self._condition_pages.get(event_type)

        if page is None:
            return

        page.message_input.setText(str(conditions.get("message") or ""))

        if hasattr(page, "mmsi_input"):
            mmsi = conditions.get("mmsi")
            page.mmsi_input.setText(str(mmsi) if mmsi is not None else "")

        if hasattr(page, "speed_input"):
            speed_limit = conditions.get(
                "speed_limit",
                conditions.get("min_speed"),
            )
            if speed_limit is not None:
                page.speed_input.setValue(float(speed_limit))

        if hasattr(page, "latitude_input"):
            latitude = conditions.get("latitude", conditions.get("lat"))
            if latitude is not None:
                page.latitude_input.setValue(float(latitude))

        if hasattr(page, "longitude_input"):
            longitude = conditions.get("longitude", conditions.get("lon"))
            if longitude is not None:
                page.longitude_input.setValue(float(longitude))

        if hasattr(page, "radius_input"):
            radius = conditions.get("radius_km", conditions.get("radius"))
            if radius is not None:
                page.radius_input.setValue(float(radius))

    def _collect_conditions(self, event_type: str) -> dict:

        page = self._condition_pages[event_type]
        conditions: dict = {}

        message = page.message_input.text().strip()

        if message:
            conditions["message"] = message

        if hasattr(page, "mmsi_input"):
            mmsi = _parse_optional_int(page.mmsi_input.text())

            if mmsi is not None:
                conditions["mmsi"] = mmsi

        if hasattr(page, "speed_input"):
            conditions["speed_limit"] = float(page.speed_input.value())

        if hasattr(page, "latitude_input"):
            conditions["latitude"] = float(page.latitude_input.value())
            conditions["longitude"] = float(page.longitude_input.value())
            conditions["radius_km"] = float(page.radius_input.value())

        return conditions

    def _validate(self) -> str | None:

        name = self.name_input.text().strip()

        if not name:
            return tr("Rule name is required.")

        event_type = self.event_type_combo.currentData()

        if event_type not in SUPPORTED_RULE_TYPES:
            return tr("Select a supported event type.")

        conditions = self._collect_conditions(event_type)

        if event_type == RULE_TYPE_SPEED_OVER:
            speed_limit = conditions.get("speed_limit")

            if speed_limit is None or float(speed_limit) <= 0:
                return tr("Speed limit must be greater than zero.")

        if event_type in {RULE_TYPE_ENTER_REGION, RULE_TYPE_EXIT_REGION}:
            for key in ("latitude", "longitude", "radius_km"):
                if key not in conditions:
                    return tr(
                        "Region rules require latitude, longitude, and radius."
                    )

            if float(conditions["radius_km"]) <= 0:
                return tr("Region radius must be greater than zero.")

        if hasattr(self._condition_pages[event_type], "mmsi_input"):
            mmsi_text = self._condition_pages[event_type].mmsi_input.text().strip()

            if mmsi_text and _parse_optional_int(mmsi_text) is None:
                return tr("MMSI must be a positive integer.")

        return None

    def _on_save(self) -> None:

        error = self._validate()

        if error:
            QMessageBox.warning(
                self,
                tr("Validation Error"),
                error,
            )
            return

        event_type = self.event_type_combo.currentData()
        conditions = self._collect_conditions(event_type)

        self._saved_rule = AlertRule(
            id=self._rule.id if self._rule else None,
            name=self.name_input.text().strip(),
            enabled=self.enabled_checkbox.isChecked(),
            priority=int(self.priority_input.value()),
            event_type=event_type,
            conditions=conditions,
            created_at=self._rule.created_at if self._rule else datetime.now(),
            updated_at=datetime.now(),
        )
        self.accept()


class RulesPage(QWidget):

    def __init__(
        self,
        manager: AlertManager | None = None,
        parent=None,
    ):
        super().__init__(parent)

        self._manager = manager or alert_manager
        self._rules: list[AlertRule] = []
        self._event_stats: dict[int, dict] = {}

        self._build_ui()
        self._connect_signals()
        bind_language_refresh(self.refresh_translations)
        self.refresh()

    def refresh(self) -> list[AlertRule]:

        self._rules = self._manager.rules()
        self._event_stats = self._build_event_stats()
        self._update_summary()
        self._populate_table()
        return list(self._rules)

    def new_rule(self) -> AlertRule | None:

        dialog = RuleEditorDialog(parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        payload = dialog.validated_rule()

        if payload is None:
            return None

        saved = self._manager.register_rule(payload)
        self.refresh()
        return saved

    def edit_rule(self, rule_id: int) -> AlertRule | None:

        rule = self._rule_by_id(rule_id)

        if rule is None:
            return None

        dialog = RuleEditorDialog(rule, parent=self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        payload = dialog.validated_rule()

        if payload is None:
            return None

        saved = self._manager.register_rule(payload)
        self.refresh()
        return saved

    def delete_rule(self, rule_id: int) -> bool:

        rule = self._rule_by_id(rule_id)

        if rule is None:
            return False

        answer = QMessageBox.question(
            self,
            tr("Delete Rule"),
            tr("Delete rule '{name}'?").replace("{name}", rule.name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return False

        removed = self._manager.remove_rule(rule_id)
        self.refresh()
        return removed

    def duplicate_rule(self, rule_id: int) -> AlertRule | None:

        rule = self._rule_by_id(rule_id)

        if rule is None:
            return None

        duplicate = AlertRule(
            name=f"{rule.name} {tr('(Copy)')}",
            enabled=rule.enabled,
            priority=rule.priority,
            event_type=rule.event_type,
            conditions=dict(rule.conditions or {}),
        )
        saved = self._manager.register_rule(duplicate)
        self.refresh()
        return saved

    def test_rule(self, rule_id: int) -> list:

        rule = self._rule_by_id(rule_id)

        if rule is None:
            return []

        payload = self._build_test_payload(rule)
        matched = self._manager.evaluate(payload)
        rule_matches = [
            event for event in matched if event.rule_id == rule_id
        ]

        if rule_matches:
            matched_line = tr("Rule '{name}' matched.").replace(
                "{name}",
                rule.name,
            )
            message = (
                f"{matched_line}\n"
                f"{tr('Severity')}: {_tr_severity(rule_matches[0].severity)}\n"
                f"{tr('Message')}: {rule_matches[0].message}"
            )
            QMessageBox.information(self, tr("Test Rule"), message)
        else:
            QMessageBox.information(
                self,
                tr("Test Rule"),
                tr("Rule '{name}' did not match the test event.").replace(
                    "{name}",
                    rule.name,
                ),
            )

        self.refresh()
        return rule_matches

    def _build_ui(self) -> None:

        self.setStyleSheet("""
            QLabel[role="title"] {
                color: white;
                font-size: 26pt;
                font-weight: bold;
            }

            QLabel[role="summary-title"] {
                color: #9aa4af;
                font-size: 9pt;
                font-weight: 600;
            }

            QLabel[role="summary-value"] {
                color: white;
                font-size: 16pt;
                font-weight: bold;
            }

            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
            }

            QTableWidget {
                background: #252a31;
                color: white;
                border: 1px solid #40444b;
                gridline-color: #40444b;
            }

            QHeaderView::section {
                background: #2f353d;
                color: #d5dbe3;
                border: 1px solid #40444b;
                padding: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(12)

        self._title_label = QLabel(tr("Rule Management"))
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setProperty("role", "title")
        layout.addWidget(self._title_label)

        summary = QGridLayout()
        self._total_rules_label = self._summary_label(tr("Total Rules"))
        summary.addWidget(self._total_rules_label, 0, 0)
        self.total_rules_value = QLabel("0")
        self.total_rules_value.setProperty("role", "summary-value")
        summary.addWidget(self.total_rules_value, 1, 0)

        self._enabled_rules_label = self._summary_label(tr("Enabled Rules"))
        summary.addWidget(self._enabled_rules_label, 0, 1)
        self.enabled_rules_value = QLabel("0")
        self.enabled_rules_value.setProperty("role", "summary-value")
        summary.addWidget(self.enabled_rules_value, 1, 1)

        self._disabled_rules_label = self._summary_label(tr("Disabled Rules"))
        summary.addWidget(self._disabled_rules_label, 0, 2)
        self.disabled_rules_value = QLabel("0")
        self.disabled_rules_value.setProperty("role", "summary-value")
        summary.addWidget(self.disabled_rules_value, 1, 2)

        self._rule_types_label = self._summary_label(tr("Rule Types"))
        summary.addWidget(self._rule_types_label, 0, 3)
        self.rule_types_value = QLabel("0")
        self.rule_types_value.setProperty("role", "summary-value")
        summary.addWidget(self.rule_types_value, 1, 3)
        layout.addLayout(summary)

        actions = QHBoxLayout()
        actions.setSpacing(8)

        self.new_button = QPushButton(tr("New Rule"))
        self.edit_button = QPushButton(tr("Edit Rule"))
        self.toggle_button = QPushButton(tr("Enable / Disable"))
        self.duplicate_button = QPushButton(tr("Duplicate Rule"))
        self.delete_button = QPushButton(tr("Delete Rule"))
        self.test_button = QPushButton(tr("Test Rule"))
        self.refresh_button = QPushButton(tr("Refresh"))

        for button in (
            self.new_button,
            self.edit_button,
            self.toggle_button,
            self.duplicate_button,
            self.delete_button,
            self.test_button,
            self.refresh_button,
        ):
            actions.addWidget(button)

        actions.addStretch()
        layout.addLayout(actions)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(self._table_header_labels())
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

    def _summary_label(self, text: str) -> QLabel:

        label = QLabel(text)
        label.setProperty("role", "summary-title")
        return label

    @staticmethod
    def _table_header_labels() -> list[str]:

        return [
            tr("Enabled"),
            tr("Name"),
            tr("Type"),
            tr("Priority"),
            tr("Last Triggered"),
            tr("Trigger Count"),
        ]

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Rule Management"))
        self._total_rules_label.setText(tr("Total Rules"))
        self._enabled_rules_label.setText(tr("Enabled Rules"))
        self._disabled_rules_label.setText(tr("Disabled Rules"))
        self._rule_types_label.setText(tr("Rule Types"))

        self.new_button.setText(tr("New Rule"))
        self.edit_button.setText(tr("Edit Rule"))
        self.toggle_button.setText(tr("Enable / Disable"))
        self.duplicate_button.setText(tr("Duplicate Rule"))
        self.delete_button.setText(tr("Delete Rule"))
        self.test_button.setText(tr("Test Rule"))
        self.refresh_button.setText(tr("Refresh"))
        self.new_button.setToolTip(tr("Create a new alert rule"))
        self.edit_button.setToolTip(tr("Edit the selected rule"))
        self.delete_button.setToolTip(tr("Delete the selected rule"))
        self.test_button.setToolTip(tr("Test the selected rule against current data"))
        self.refresh_button.setToolTip(tr("Reload rules and statistics"))

        self.table.setHorizontalHeaderLabels(self._table_header_labels())
        self._populate_table()

    def _connect_signals(self) -> None:

        self.refresh_button.clicked.connect(self.refresh)
        self.new_button.clicked.connect(self.new_rule)
        self.edit_button.clicked.connect(self._on_edit_clicked)
        self.toggle_button.clicked.connect(self._on_toggle_clicked)
        self.duplicate_button.clicked.connect(self._on_duplicate_clicked)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.test_button.clicked.connect(self._on_test_clicked)
        self.table.cellDoubleClicked.connect(
            lambda _row, _column: self._on_edit_clicked()
        )

    def _selected_rule_id(self) -> int | None:

        row = self.table.currentRow()

        if row < 0:
            return None

        item = self.table.item(row, 0)

        if item is None:
            return None

        rule_id = item.data(Qt.ItemDataRole.UserRole)

        if rule_id is None:
            return None

        return int(rule_id)

    def _rule_by_id(self, rule_id: int) -> AlertRule | None:

        for rule in self._rules:
            if rule.id == rule_id:
                return rule

        return None

    def _build_event_stats(self) -> dict[int, dict]:

        stats: dict[int, dict] = {}

        for event in self._manager.events():
            rule_id = int(event.rule_id)

            if rule_id not in stats:
                stats[rule_id] = {
                    "count": 0,
                    "last_triggered": None,
                }

            stats[rule_id]["count"] += 1

            last_triggered = stats[rule_id]["last_triggered"]

            if (
                last_triggered is None
                or event.timestamp > last_triggered
            ):
                stats[rule_id]["last_triggered"] = event.timestamp

        return stats

    def _build_test_payload(self, rule: AlertRule) -> dict:

        conditions = rule.conditions or {}
        mmsi = conditions.get("mmsi", 123456789)

        payload = {
            "mmsi": int(mmsi),
            "event_type": rule.event_type,
            "timestamp": datetime.now(),
            "metadata": {"test": True},
        }

        if rule.event_type == RULE_TYPE_SPEED_OVER:
            speed_limit = float(
                conditions.get("speed_limit", conditions.get("min_speed", 10.0))
            )
            payload["speed"] = speed_limit + 1.0

        if rule.event_type == RULE_TYPE_ENTER_REGION:
            payload["latitude"] = float(conditions.get("latitude", 47.5))
            payload["longitude"] = float(conditions.get("longitude", 19.0))

        if rule.event_type == RULE_TYPE_EXIT_REGION:
            latitude = float(conditions.get("latitude", 47.5))
            longitude = float(conditions.get("longitude", 19.0))
            radius_km = float(conditions.get("radius_km", 10.0))
            payload["latitude"] = latitude + (radius_km / 111.0) + 0.1
            payload["longitude"] = longitude

        if rule.event_type == RULE_TYPE_CAMERA_VISIBLE:
            payload["camera_visible"] = True

        if rule.event_type == RULE_TYPE_CAMERA_LOST:
            payload["camera_visible"] = False

        return payload

    def _update_summary(self) -> None:

        enabled_count = sum(1 for rule in self._rules if rule.enabled)
        disabled_count = len(self._rules) - enabled_count
        rule_types = {
            rule.event_type
            for rule in self._rules
            if _display_text(rule.event_type) != "—"
        }

        self.total_rules_value.setText(str(len(self._rules)))
        self.enabled_rules_value.setText(str(enabled_count))
        self.disabled_rules_value.setText(str(disabled_count))
        self.rule_types_value.setText(str(len(rule_types)))

    def _populate_table(self) -> None:

        if not self._rules:
            show_empty_table_message(
                self.table,
                "No rules found",
            )
            return

        self.table.setRowCount(len(self._rules))

        for row_index, rule in enumerate(self._rules):
            stats = self._event_stats.get(rule.id or -1, {})
            last_triggered = stats.get("last_triggered")
            trigger_count = stats.get("count", 0)

            values = [
                tr("Yes") if rule.enabled else tr("No"),
                _display_text(rule.name),
                _tr_event_type(rule.event_type),
                str(rule.priority),
                _format_timestamp(last_triggered),
                str(trigger_count),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(Qt.ItemDataRole.UserRole, rule.id)
                self.table.setItem(row_index, column_index, item)

        self.table.resizeColumnsToContents()

    def _on_edit_clicked(self) -> None:

        rule_id = self._selected_rule_id()

        if rule_id is None:
            QMessageBox.information(
                self,
                tr("Edit Rule"),
                tr("Select a rule to edit."),
            )
            return

        self.edit_rule(rule_id)

    def _on_toggle_clicked(self) -> None:

        rule_id = self._selected_rule_id()

        if rule_id is None:
            QMessageBox.information(
                self,
                tr("Enable / Disable"),
                tr("Select a rule first."),
            )
            return

        rule = self._rule_by_id(rule_id)

        if rule is None:
            return

        updated = AlertRule(
            id=rule.id,
            name=rule.name,
            enabled=not rule.enabled,
            priority=rule.priority,
            event_type=rule.event_type,
            conditions=dict(rule.conditions or {}),
            created_at=rule.created_at,
            updated_at=datetime.now(),
        )
        self._manager.register_rule(updated)
        self.refresh()

    def _on_duplicate_clicked(self) -> None:

        rule_id = self._selected_rule_id()

        if rule_id is None:
            QMessageBox.information(
                self,
                tr("Duplicate Rule"),
                tr("Select a rule to duplicate."),
            )
            return

        self.duplicate_rule(rule_id)

    def _on_delete_clicked(self) -> None:

        rule_id = self._selected_rule_id()

        if rule_id is None:
            QMessageBox.information(
                self,
                tr("Delete Rule"),
                tr("Select a rule to delete."),
            )
            return

        self.delete_rule(rule_id)

    def _on_test_clicked(self) -> None:

        rule_id = self._selected_rule_id()

        if rule_id is None:
            QMessageBox.information(
                self,
                tr("Test Rule"),
                tr("Select a rule to test."),
            )
            return

        self.test_rule(rule_id)

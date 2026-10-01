from datetime import datetime
from zoneinfo import ZoneInfo

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)


def get_nz_today():
    return datetime.now(ZoneInfo("Pacific/Auckland")).date()


def date_to_qdate(date_obj):
    return QDate(date_obj.year, date_obj.month, date_obj.day)


def qdate_to_string(qdate):
    return qdate.toString("yyyy-MM-dd")


def format_date(date_string):
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return date_string


class BillDialog(QDialog):
    """New Bill dialog. Used when creating a brand-new bill."""

    def __init__(self, properties, tenants_by_property, parent=None, bill=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Bill" if bill else "New Bill")
        self.setMinimumWidth(460)

        self.properties = properties
        self.tenants_by_property = tenants_by_property
        self.bill = bill

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.property_combo = QComboBox()
        for property_id, address in properties:
            self.property_combo.addItem(address, property_id)

        self.tenant_combo = QComboBox()

        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")

        self.note_edit = QLineEdit()

        form.addRow("Property:", self.property_combo)
        form.addRow("Tenant:", self.tenant_combo)
        form.addRow("From:", self.start_date)
        form.addRow("To:", self.end_date)
        form.addRow("Note:", self.note_edit)

        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        self.buttons.accepted.connect(self.validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.property_combo.currentIndexChanged.connect(self.load_tenants)

        today = get_nz_today()
        self.start_date.setDate(date_to_qdate(today))
        self.end_date.setDate(date_to_qdate(today))

        if bill:
            property_id = bill[1]
            tenant_id = bill[3]

            index = self.property_combo.findData(property_id)
            if index >= 0:
                self.property_combo.setCurrentIndex(index)

            self.start_date.setDate(QDate.fromString(bill[5], "yyyy-MM-dd"))
            self.end_date.setDate(QDate.fromString(bill[6], "yyyy-MM-dd"))
            self.note_edit.setText(bill[8] or "")

            self.load_tenants()
            tenant_index = self.tenant_combo.findData(tenant_id)
            if tenant_index >= 0:
                self.tenant_combo.setCurrentIndex(tenant_index)
        else:
            self.load_tenants()

    def load_tenants(self):
        self.tenant_combo.clear()
        property_id = self.property_combo.currentData()

        for tenant_id, tenant_name in self.tenants_by_property.get(property_id, []):
            self.tenant_combo.addItem(tenant_name, tenant_id)

    def validate_and_accept(self):
        if self.property_combo.currentData() is None:
            QMessageBox.warning(self, "Missing Property", "Please select a property.")
            return

        if self.tenant_combo.currentData() is None:
            QMessageBox.warning(
                self,
                "Missing Tenant",
                "Please select a tenant for this bill."
            )
            return

        if self.start_date.date() > self.end_date.date():
            QMessageBox.warning(
                self,
                "Invalid Dates",
                "The From date cannot be later than the To date."
            )
            return

        self.accept()


class ChargeDialog(QDialog):
    def __init__(self, parent=None, charge=None, description=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Charge" if charge else "Add Charge")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.description = QLineEdit()
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0.01, 999999999.99)
        self.amount.setDecimals(2)
        self.amount.setPrefix("$ ")

        form.addRow("Description:", self.description)
        form.addRow("Amount:", self.amount)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if charge:
            self.description.setText(charge[1])
            self.amount.setValue(float(charge[2]))
        elif description:
            self.description.setText(description)

    def validate_and_accept(self):
        if not self.description.text().strip():
            QMessageBox.warning(
                self,
                "Missing Description",
                "Please enter a description."
            )
            return

        if self.amount.value() <= 0:
            QMessageBox.warning(
                self,
                "Invalid Amount",
                "Amount must be greater than zero."
            )
            return

        self.accept()


class BillEditDialog(QDialog):
    """Full Bill editor, including the charges inside the bill."""

    def __init__(self, properties, tenants_by_property, bill, charges, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Bill #{bill[0]}")
        self.setMinimumSize(680, 560)

        self.properties = properties
        self.tenants_by_property = tenants_by_property
        self.bill = bill

        # Work on a local copy so Cancel really cancels charge changes too.
        self.working_charges = [
            (charge[0], charge[1], float(charge[2])) for charge in charges
        ]

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.property_combo = QComboBox()
        for property_id, address in properties:
            self.property_combo.addItem(address, property_id)

        self.tenant_combo = QComboBox()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.note_edit = QLineEdit()

        form.addRow("Property:", self.property_combo)
        form.addRow("Tenant:", self.tenant_combo)
        form.addRow("From:", self.start_date)
        form.addRow("To:", self.end_date)
        form.addRow("Note:", self.note_edit)
        layout.addLayout(form)

        charges_title = QLabel("Charges")
        charges_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(charges_title)

        self.charges_table = QTableWidget(0, 4)
        self.charges_table.setHorizontalHeaderLabels(
            ["Description", "Amount", "Edit", "Delete"]
        )
        self.charges_table.setAlternatingRowColors(True)
        self.charges_table.setColumnWidth(0, 300)
        self.charges_table.setColumnWidth(1, 120)
        self.charges_table.setColumnWidth(2, 80)
        self.charges_table.setColumnWidth(3, 80)
        layout.addWidget(self.charges_table)

        charge_actions = QHBoxLayout()
        self.add_charge_button = QPushButton("+ Add Charge")
        self.add_charge_button.clicked.connect(self.add_charge)
        charge_actions.addWidget(self.add_charge_button)
        charge_actions.addStretch()
        layout.addLayout(charge_actions)

        self.total_label = QLabel("Total: $0.00")
        self.total_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(self.total_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Save
        )
        self.buttons.accepted.connect(self.validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.property_combo.currentIndexChanged.connect(self.load_tenants)

        property_index = self.property_combo.findData(bill[1])
        if property_index >= 0:
            self.property_combo.setCurrentIndex(property_index)

        self.start_date.setDate(QDate.fromString(bill[5], "yyyy-MM-dd"))
        self.end_date.setDate(QDate.fromString(bill[6], "yyyy-MM-dd"))
        self.note_edit.setText(bill[8] or "")

        self.load_tenants()
        tenant_index = self.tenant_combo.findData(bill[3])
        if tenant_index >= 0:
            self.tenant_combo.setCurrentIndex(tenant_index)

        self.refresh_charges()

    def load_tenants(self):
        current_tenant_id = self.tenant_combo.currentData()
        self.tenant_combo.blockSignals(True)
        self.tenant_combo.clear()

        property_id = self.property_combo.currentData()
        for tenant_id, tenant_name in self.tenants_by_property.get(property_id, []):
            self.tenant_combo.addItem(tenant_name, tenant_id)

        if current_tenant_id is not None:
            index = self.tenant_combo.findData(current_tenant_id)
            if index >= 0:
                self.tenant_combo.setCurrentIndex(index)

        self.tenant_combo.blockSignals(False)

    def refresh_charges(self):
        self.charges_table.setRowCount(0)
        total = 0.0

        for index, charge in enumerate(self.working_charges):
            charge_id, description, amount = charge
            row = self.charges_table.rowCount()
            self.charges_table.insertRow(row)
            self.charges_table.setItem(row, 0, QTableWidgetItem(description))
            self.charges_table.setItem(row, 1, QTableWidgetItem(f"${amount:,.2f}"))

            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(
                lambda checked=False, i=index: self.edit_charge(i)
            )
            self.charges_table.setCellWidget(row, 2, edit_button)

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(
                lambda checked=False, i=index: self.delete_charge(i)
            )
            self.charges_table.setCellWidget(row, 3, delete_button)

            total += amount

        self.total_label.setText(f"Total: ${total:,.2f}")

    def add_charge(self):
        dialog = ChargeDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self.working_charges.append(
            (None, dialog.description.text().strip(), dialog.amount.value())
        )
        self.refresh_charges()

    def edit_charge(self, index):
        charge = self.working_charges[index]
        dialog = ChargeDialog(self, charge=charge)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self.working_charges[index] = (
            charge[0],
            dialog.description.text().strip(),
            dialog.amount.value(),
        )
        self.refresh_charges()

    def delete_charge(self, index):
        charge = self.working_charges[index]
        answer = QMessageBox.question(
            self,
            "Delete Charge",
            f"Delete '{charge[1]}'?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.working_charges.pop(index)
        self.refresh_charges()

    def validate_and_accept(self):
        if self.property_combo.currentData() is None:
            QMessageBox.warning(self, "Missing Property", "Please select a property.")
            return

        if self.tenant_combo.currentData() is None:
            QMessageBox.warning(self, "Missing Tenant", "Please select a tenant.")
            return

        if self.start_date.date() > self.end_date.date():
            QMessageBox.warning(
                self,
                "Invalid Dates",
                "The From date cannot be later than the To date."
            )
            return

        self.accept()


class BillViewDialog(QDialog):
    """Read-only bill preview with PDF export."""

    def __init__(self, bill, charges, paid=0.0, parent=None, export_callback=None):
        super().__init__(parent)
        self.setWindowTitle(f"View Bill #{bill[0]}")
        self.setMinimumSize(620, 520)
        self.bill = bill
        self.charges = charges
        self.paid = float(paid or 0)
        self.export_callback = export_callback

        layout = QVBoxLayout(self)

        title = QLabel("RENTTRACK - BILL")
        title.setStyleSheet("font-size: 22px; font-weight: bold;")
        layout.addWidget(title)

        info = QLabel(
            f"<b>Bill #{bill[0]}</b><br>"
            f"Property: {bill[2]}<br>"
            f"Tenant: {bill[4]}<br>"
            f"Period: {format_date(bill[5])} - {format_date(bill[6])}"
            + (f"<br>Note: {bill[8]}" if bill[8] else "")
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Description", "Amount"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setColumnWidth(0, 380)
        table.setColumnWidth(1, 140)
        table.setAlternatingRowColors(True)
        layout.addWidget(table)

        total = 0.0
        for description, amount in [(c[1], float(c[2])) for c in charges]:
            row = table.rowCount()
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(description))
            table.setItem(row, 1, QTableWidgetItem(f"${amount:,.2f}"))
            total += amount

        outstanding = total - self.paid

        summary = QLabel(
            f"<b>Total: ${total:,.2f}</b><br>"
            f"Paid: ${self.paid:,.2f}<br>"
            f"Outstanding: ${outstanding:,.2f}"
        )
        summary.setStyleSheet("font-size: 16px; padding: 8px 0;")
        layout.addWidget(summary)

        buttons = QHBoxLayout()
        self.export_button = QPushButton("Export PDF")
        self.export_button.clicked.connect(self.export_pdf)
        buttons.addWidget(self.export_button)
        buttons.addStretch()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.reject)
        buttons.addWidget(close_button)
        layout.addLayout(buttons)

    def export_pdf(self):
        if self.export_callback:
            self.export_callback(self.bill, self.charges, self.paid)


class BillingUI:
    def __init__(self, page):
        self.page = page

        self.root = QWidget()
        self.layout = QVBoxLayout(self.root)

        title = QLabel("Billing")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(title)

        today = get_nz_today()
        self.today_label = QLabel(
            f"Today: {today.strftime('%d/%m/%Y')} (New Zealand)"
        )
        self.layout.addWidget(self.today_label)

        top = QHBoxLayout()

        property_label = QLabel("Property:")
        property_label.setFixedWidth(55)
        top.addWidget(property_label)

        self.property_combo = QComboBox()
        self.property_combo.setMinimumWidth(220)
        top.addWidget(self.property_combo)

        tenant_label = QLabel("Tenant:")
        tenant_label.setFixedWidth(50)
        top.addWidget(tenant_label)

        self.tenant_combo = QComboBox()
        self.tenant_combo.setMinimumWidth(180)
        top.addWidget(self.tenant_combo)

        self.new_bill_button = QPushButton("+ Create New Bill")
        top.addWidget(self.new_bill_button)

        self.layout.addLayout(top)

        current_title = QLabel("Current Bill")
        current_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(current_title)

        self.bill_info = QLabel("No bill selected.")
        self.bill_info.setWordWrap(True)
        self.layout.addWidget(self.bill_info)

        bill_actions = QHBoxLayout()
        self.edit_bill_button = QPushButton("Edit Bill")
        self.delete_bill_button = QPushButton("Delete Bill")
        self.edit_bill_button.setEnabled(False)
        self.delete_bill_button.setEnabled(False)
        bill_actions.addWidget(self.edit_bill_button)
        bill_actions.addWidget(self.delete_bill_button)
        bill_actions.addStretch()
        self.layout.addLayout(bill_actions)

        charge_buttons = QHBoxLayout()
        self.rent_button = QPushButton("+ Rent")
        self.water_button = QPushButton("+ Water")
        self.electricity_button = QPushButton("+ Electricity")
        self.gas_button = QPushButton("+ Gas")
        self.internet_button = QPushButton("+ Internet")
        self.custom_button = QPushButton("+ Custom")

        for button in (
            self.rent_button,
            self.water_button,
            self.electricity_button,
            self.gas_button,
            self.internet_button,
            self.custom_button,
        ):
            button.setEnabled(False)
            charge_buttons.addWidget(button)
        charge_buttons.addStretch()
        self.layout.addLayout(charge_buttons)

        self.charges_table = QTableWidget(0, 4)
        self.charges_table.setHorizontalHeaderLabels(
            ["Description", "Amount", "Edit", "Delete"]
        )
        self.charges_table.setAlternatingRowColors(True)
        self.charges_table.horizontalHeader().setStretchLastSection(False)
        self.charges_table.setColumnWidth(0, 300)
        self.charges_table.setColumnWidth(1, 120)
        self.charges_table.setColumnWidth(2, 80)
        self.charges_table.setColumnWidth(3, 80)
        self.layout.addWidget(self.charges_table)

        self.total_label = QLabel("Total: $0.00")
        self.total_label.setStyleSheet(
            "font-size: 32px; font-weight: bold; padding: 8px 0;"
        )
        self.layout.addWidget(self.total_label)

        history_title = QLabel("Billing History")
        history_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.layout.addWidget(history_title)

        history_filter = QHBoxLayout()
        history_filter.addWidget(QLabel("Year:"))
        self.year_combo = QComboBox()
        for year in range(today.year - 5, today.year + 6):
            self.year_combo.addItem(str(year), year)
        self.year_combo.setCurrentText(str(today.year))
        history_filter.addWidget(self.year_combo)
        history_filter.addWidget(QLabel("Month:"))
        self.month_combo = QComboBox()
        for month in range(1, 13):
            self.month_combo.addItem(datetime(2000, month, 1).strftime("%B"), month)
        self.month_combo.setCurrentIndex(today.month - 1)
        history_filter.addWidget(self.month_combo)
        history_filter.addStretch()
        self.layout.addLayout(history_filter)

        self.history_table = QTableWidget(0, 10)
        self.history_table.setHorizontalHeaderLabels([
            "Bill #",
            "Tenant",
            "From",
            "To",
            "Total",
            "Paid",
            "Outstanding",
            "View",
            "Edit",
            "Delete",
        ])
        self.history_table.setAlternatingRowColors(True)
        widths = [70, 150, 100, 100, 110, 110, 120, 80, 80, 80]
        for index, width in enumerate(widths):
            self.history_table.setColumnWidth(index, width)
        self.layout.addWidget(self.history_table)

        self.property_combo.currentIndexChanged.connect(self.page.on_property_changed)
        self.tenant_combo.currentIndexChanged.connect(self.page.on_tenant_changed)
        self.new_bill_button.clicked.connect(self.page.create_new_bill)
        self.rent_button.clicked.connect(lambda: self.page.add_standard_charge("Rent"))
        self.water_button.clicked.connect(lambda: self.page.add_standard_charge("Water"))
        self.electricity_button.clicked.connect(lambda: self.page.add_standard_charge("Electricity"))
        self.gas_button.clicked.connect(lambda: self.page.add_standard_charge("Gas"))
        self.internet_button.clicked.connect(lambda: self.page.add_standard_charge("Internet"))
        self.custom_button.clicked.connect(self.page.add_custom_charge)
        self.edit_bill_button.clicked.connect(self.page.edit_current_bill)
        self.delete_bill_button.clicked.connect(self.page.delete_current_bill)
        self.year_combo.currentIndexChanged.connect(self.page.load_history)
        self.month_combo.currentIndexChanged.connect(self.page.load_history)
        self.history_table.cellDoubleClicked.connect(self.page.open_history_bill)

    def make_button(self, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        return button

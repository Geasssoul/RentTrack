from datetime import datetime
from zoneinfo import ZoneInfo

from PyQt6.QtCore import Qt

from PyQt6.QtWidgets import (
    QMessageBox,
    QPushButton,
    QHBoxLayout,
    QTableWidgetItem,
    QWidget,
    QAbstractItemView,
)

from database import (
    create_database,
    get_properties,
    get_tenants,
    add_bill,
    get_bills,
    get_bill,
    update_bill,
    delete_bill,
    add_bill_charge,
    get_bill_charges,
    update_bill_charge,
    delete_bill_charge,
    get_bill_payments,
    set_bill_paid,
)

from ui.billing_ui import (
    BillingUI,
    BillDialog,
    BillEditDialog,
    BillViewDialog,
    ChargeDialog,
    format_date,
)


class BillingPage(QWidget):
    def __init__(self):
        super().__init__()

        create_database()

        self.ui = BillingUI(self)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.ui.root)

        self.current_bill_id = None
        self.properties = []
        self.tenants = []
        self.tenants_by_property = {}
        self._updating_history = False

        self.ui.history_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
        )
        self.ui.history_table.itemChanged.connect(
            self.on_history_item_changed
        )

        self.load_properties()

    # -------------------------
    # Data loading
    # -------------------------

    def load_properties(self):
        self.properties = get_properties()

        self.ui.property_combo.blockSignals(True)
        self.ui.property_combo.clear()

        for property_id, address in self.properties:
            self.ui.property_combo.addItem(address, property_id)

        self.ui.property_combo.blockSignals(False)

        self.load_tenants()

        if self.properties:
            self.load_history()
        else:
            self.clear_current_bill()
            self.ui.history_table.setRowCount(0)

    def load_tenants(self):
        self.tenants = get_tenants()
        self.tenants_by_property = {}

        for row in self.tenants:
            tenant_id, name, phone, email, property_id, address = row
            self.tenants_by_property.setdefault(property_id, []).append(
                (tenant_id, name)
            )

        property_id = self.ui.property_combo.currentData()

        self.ui.tenant_combo.blockSignals(True)
        self.ui.tenant_combo.clear()

        for tenant_id, name in self.tenants_by_property.get(property_id, []):
            self.ui.tenant_combo.addItem(name, tenant_id)

        self.ui.tenant_combo.blockSignals(False)

        self.load_history()

    def on_property_changed(self):
        self.current_bill_id = None
        self.load_tenants()

    def on_tenant_changed(self):
        self.load_history()

    # -------------------------
    # New / edit Bill
    # -------------------------

    def create_new_bill(self):
        if not self.properties:
            QMessageBox.information(
                self,
                "No Property",
                "Please add a property first."
            )
            return

        property_id = self.ui.property_combo.currentData()

        if not self.tenants_by_property.get(property_id):
            QMessageBox.information(
                self,
                "No Tenant",
                "This property has no tenant yet. Please add the tenant first."
            )
            return

        dialog = BillDialog(
            self.properties,
            self.tenants_by_property,
            self,
        )

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        property_id = dialog.property_combo.currentData()
        tenant_id = dialog.tenant_combo.currentData()
        start_date = dialog.start_date.date().toString("yyyy-MM-dd")
        end_date = dialog.end_date.date().toString("yyyy-MM-dd")
        note = dialog.note_edit.text().strip()

        today = datetime.now(
            ZoneInfo("Pacific/Auckland")
        ).strftime("%Y-%m-%d")

        try:
            bill_id = add_bill(
                property_id,
                tenant_id,
                start_date,
                end_date,
                today,
                note,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        self.current_bill_id = bill_id
        self.refresh_all()

        # Select the newly created bill in the history if it belongs
        # to the currently selected month.
        self.select_bill_in_history(bill_id)

    def edit_current_bill(self):
        if self.current_bill_id is None:
            return

        bill = get_bill(self.current_bill_id)
        if not bill:
            return

        charges = get_bill_charges(self.current_bill_id)
        dialog = BillEditDialog(
            self.properties,
            self.tenants_by_property,
            bill,
            charges,
            self,
        )

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        property_id = dialog.property_combo.currentData()
        tenant_id = dialog.tenant_combo.currentData()
        start_date = dialog.start_date.date().toString("yyyy-MM-dd")
        end_date = dialog.end_date.date().toString("yyyy-MM-dd")
        note = dialog.note_edit.text().strip()

        try:
            update_bill(
                self.current_bill_id,
                property_id,
                tenant_id,
                start_date,
                end_date,
                note,
            )

            original_ids = {charge[0] for charge in charges}
            working_ids = {charge[0] for charge in dialog.working_charges if charge[0] is not None}

            # Delete charges removed in the editor.
            for charge_id in original_ids - working_ids:
                delete_bill_charge(charge_id)

            # Update existing charges and insert new ones.
            for charge_id, description, amount in dialog.working_charges:
                if charge_id is None:
                    add_bill_charge(self.current_bill_id, description, amount)
                else:
                    update_bill_charge(charge_id, description, amount)

        except ValueError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        self.refresh_all()

    def delete_current_bill(self):
        if self.current_bill_id is None:
            return

        bill = get_bill(self.current_bill_id)
        if not bill:
            return

        answer = QMessageBox.question(
            self,
            "Delete Bill",
            (
                f"Delete Bill #{bill[0]} for {bill[4]}?\n\n"
                "All charges belonging to this bill will also be deleted."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        delete_bill(self.current_bill_id)
        self.current_bill_id = None
        self.refresh_all()

    # -------------------------
    # Charges
    # -------------------------

    def add_standard_charge(self, description):
        if self.current_bill_id is None:
            QMessageBox.information(
                self,
                "No Bill",
                "Please create or select a bill first."
            )
            return

        dialog = ChargeDialog(
            self,
            description=description,
        )

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        add_bill_charge(
            self.current_bill_id,
            dialog.description.text().strip(),
            dialog.amount.value(),
        )

        self.load_current_bill()
        self.load_history()

    def add_custom_charge(self):
        if self.current_bill_id is None:
            QMessageBox.information(
                self,
                "No Bill",
                "Please create or select a bill first."
            )
            return

        dialog = ChargeDialog(self)

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        add_bill_charge(
            self.current_bill_id,
            dialog.description.text().strip(),
            dialog.amount.value(),
        )

        self.load_current_bill()
        self.load_history()

    def edit_charge(self, charge_id):
        charges = get_bill_charges(self.current_bill_id)
        charge = next((c for c in charges if c[0] == charge_id), None)

        if not charge:
            return

        dialog = ChargeDialog(self, charge=charge)

        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        update_bill_charge(
            charge_id,
            dialog.description.text().strip(),
            dialog.amount.value(),
        )

        self.load_current_bill()
        self.load_history()

    def delete_charge(self, charge_id):
        answer = QMessageBox.question(
            self,
            "Delete Charge",
            "Delete this charge?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        delete_bill_charge(charge_id)
        self.load_current_bill()
        self.load_history()

    # -------------------------
    # Current bill display
    # -------------------------

    def clear_current_bill(self):
        self.current_bill_id = None
        self.ui.bill_info.setText("No bill selected.")
        self.ui.charges_table.setRowCount(0)
        self.ui.total_label.setText("Total: $0.00")
        for button in (
            self.ui.rent_button,
            self.ui.water_button,
            self.ui.electricity_button,
            self.ui.gas_button,
            self.ui.internet_button,
            self.ui.custom_button,
        ):
            button.setEnabled(False)

        self.ui.edit_bill_button.setEnabled(False)
        self.ui.delete_bill_button.setEnabled(False)

    def load_current_bill(self):
        if self.current_bill_id is None:
            self.clear_current_bill()
            return

        bill = get_bill(self.current_bill_id)

        if not bill:
            self.clear_current_bill()
            return

        # id, property_id, address, tenant_id, tenant_name,
        # start_date, end_date, created_date, note
        self.ui.bill_info.setText(
            f"<b>Bill #{bill[0]}</b><br>"
            f"Property: {bill[2]}<br>"
            f"Tenant: {bill[4]}<br>"
            f"Period: {format_date(bill[5])} - {format_date(bill[6])}"
            + (f"<br>Note: {bill[8]}" if bill[8] else "")
        )

        for button in (
            self.ui.rent_button,
            self.ui.water_button,
            self.ui.electricity_button,
            self.ui.gas_button,
            self.ui.internet_button,
            self.ui.custom_button,
        ):
            button.setEnabled(True)

        self.ui.edit_bill_button.setEnabled(True)
        self.ui.delete_bill_button.setEnabled(True)

        charges = get_bill_charges(self.current_bill_id)
        self.ui.charges_table.setRowCount(0)

        total = 0.0

        for row in charges:
            charge_id, description, amount = row
            table_row = self.ui.charges_table.rowCount()
            self.ui.charges_table.insertRow(table_row)

            self.ui.charges_table.setItem(
                table_row,
                0,
                QTableWidgetItem(description),
            )
            self.ui.charges_table.setItem(
                table_row,
                1,
                QTableWidgetItem(f"${amount:,.2f}"),
            )

            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(
                lambda checked=False, cid=charge_id:
                self.edit_charge(cid)
            )
            self.ui.charges_table.setCellWidget(
                table_row, 2, edit_button
            )

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(
                lambda checked=False, cid=charge_id:
                self.delete_charge(cid)
            )
            self.ui.charges_table.setCellWidget(
                table_row, 3, delete_button
            )

            total += amount

        self.ui.total_label.setText(f"Total: ${total:,.2f}")

    # -------------------------
    # Billing history
    # -------------------------

    def load_history(self):
        property_id = self.ui.property_combo.currentData()
        tenant_id = self.ui.tenant_combo.currentData()
        year = self.ui.year_combo.currentData()
        month = self.ui.month_combo.currentData()

        if property_id is None:
            self.ui.history_table.setRowCount(0)
            return

        bills = get_bills(
            property_id=property_id,
            tenant_id=tenant_id,
            year=year,
            month=month,
        )

        self._updating_history = True
        self.ui.history_table.setRowCount(0)

        for bill in bills:
            # id, property_id, address, tenant_id, tenant_name,
            # start_date, end_date, created_date, note, total, paid
            bill_id = bill[0]
            tenant_name = bill[4]
            start_date = bill[5]
            end_date = bill[6]
            total = float(bill[9] or 0)
            paid = float(bill[10] or 0)
            outstanding = total - paid

            row = self.ui.history_table.rowCount()
            self.ui.history_table.insertRow(row)

            values = [
                str(bill_id),
                tenant_name,
                format_date(start_date),
                format_date(end_date),
                f"${total:,.2f}",
                f"${paid:,.2f}",
                f"${outstanding:,.2f}",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)

                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                ) if column in (0, 4, 5, 6) else None

                if column not in (5, 6):
                    item.setFlags(
                        item.flags()
                        & ~Qt.ItemFlag.ItemIsEditable
                    )

                self.ui.history_table.setItem(
                    row,
                    column,
                    item,
                )

            self.ui.history_table.item(row, 0).setData(
                32, bill_id
            )
            self.ui.history_table.item(row, 5).setData(
                Qt.ItemDataRole.UserRole + 1, paid
            )
            self.ui.history_table.item(row, 6).setData(
                Qt.ItemDataRole.UserRole + 1, outstanding
            )

            view_button = QPushButton("View")
            view_button.clicked.connect(
                lambda checked=False, bid=bill_id:
                self.view_bill_by_id(bid)
            )
            self.ui.history_table.setCellWidget(row, 7, view_button)

            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(
                lambda checked=False, bid=bill_id:
                self.edit_bill_by_id(bid)
            )
            self.ui.history_table.setCellWidget(row, 8, edit_button)

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(
                lambda checked=False, bid=bill_id:
                self.delete_bill_by_id(bid)
            )
            self.ui.history_table.setCellWidget(row, 9, delete_button)

        self._updating_history = False

    def on_history_item_changed(self, item):
        if self._updating_history or item is None:
            return

        column = item.column()
        if column not in (5, 6):
            return

        row = item.row()
        bill_item = self.ui.history_table.item(row, 0)
        total_item = self.ui.history_table.item(row, 4)
        paid_item = self.ui.history_table.item(row, 5)
        outstanding_item = self.ui.history_table.item(row, 6)

        if not all((bill_item, total_item, paid_item, outstanding_item)):
            return

        bill_id = bill_item.data(32)
        if bill_id is None:
            return

        try:
            total = float(
                total_item.text().replace("$", "").replace(",", "").strip()
            )
            value = float(
                item.text().replace("$", "").replace(",", "").strip()
            )
        except ValueError:
            self.restore_history_value(item)
            return

        if value < 0 or value > total:
            QMessageBox.warning(
                self,
                "Invalid Amount",
                f"The amount must be between $0.00 and ${total:,.2f}."
            )
            self.restore_history_value(item)
            return

        value = round(value, 2)

        if column == 5:
            paid = value
            outstanding = round(total - paid, 2)
        else:
            outstanding = value
            paid = round(total - outstanding, 2)

        try:
            self._updating_history = True
            payment_date = datetime.now(
                ZoneInfo("Pacific/Auckland")
            ).strftime("%Y-%m-%d")
            set_bill_paid(
                bill_id,
                paid,
                payment_date,
            )

            paid_item.setText(f"${paid:,.2f}")
            outstanding_item.setText(f"${outstanding:,.2f}")

            paid_item.setData(
                Qt.ItemDataRole.UserRole + 1,
                paid
            )
            outstanding_item.setData(
                Qt.ItemDataRole.UserRole + 1,
                outstanding
            )
        except Exception as e:
            self.restore_history_value(item)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to update payment:\n\n{e}"
            )
        finally:
            self._updating_history = False

    def restore_history_value(self, item):
        previous = item.data(
            Qt.ItemDataRole.UserRole + 1
        )
        if previous is None:
            previous = 0.0

        self._updating_history = True
        item.setText(f"${float(previous):,.2f}")
        self._updating_history = False

    def view_bill_by_id(self, bill_id):
        bill = get_bill(bill_id)
        if not bill:
            return

        charges = get_bill_charges(bill_id)
        payments = get_bill_payments(bill_id)
        paid = sum(float(payment[1] or 0) for payment in payments)

        dialog = BillViewDialog(
            bill,
            charges,
            paid=paid,
            parent=self,
            export_callback=self.export_bill_pdf,
        )
        dialog.exec()

    def export_bill_pdf(self, bill, charges, paid):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
            )
        except ImportError:
            QMessageBox.warning(
                self,
                "PDF Export",
                "PDF export requires the 'reportlab' package.",
            )
            return

        from PyQt6.QtWidgets import QFileDialog
        import re

        safe_tenant = re.sub(r"[^A-Za-z0-9_-]+", "_", bill[4]).strip("_") or "Tenant"
        default_name = f"Bill_{bill[0]}_{safe_tenant}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Bill as PDF",
            default_name,
            "PDF Files (*.pdf)",
        )
        if not path:
            return

        total = sum(float(charge[2] or 0) for charge in charges)
        outstanding = total - float(paid or 0)

        styles = getSampleStyleSheet()
        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
        )

        story = [
            Paragraph("<b>RENTTRACK</b>", styles["Title"]),
            Paragraph("BILL", styles["Heading2"]),
            Spacer(1, 8),
            Paragraph(f"<b>Bill #:</b> {bill[0]}", styles["BodyText"]),
            Paragraph(f"<b>Property:</b> {bill[2]}", styles["BodyText"]),
            Paragraph(f"<b>Tenant:</b> {bill[4]}", styles["BodyText"]),
            Paragraph(
                f"<b>Billing Period:</b> {format_date(bill[5])} - {format_date(bill[6])}",
                styles["BodyText"],
            ),
        ]

        if bill[8]:
            story.append(Paragraph(f"<b>Note:</b> {bill[8]}", styles["BodyText"]))

        story.append(Spacer(1, 14))

        data = [["Description", "Amount"]]
        for charge in charges:
            data.append([charge[1], f"${float(charge[2]):,.2f}"])
        data.append(["TOTAL", f"${total:,.2f}"])

        table = Table(data, colWidths=[125 * mm, 40 * mm])
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(table)
        story.append(Spacer(1, 14))
        story.append(Paragraph(f"<b>Paid:</b> ${float(paid):,.2f}", styles["BodyText"]))
        story.append(Paragraph(f"<b>Outstanding:</b> ${outstanding:,.2f}", styles["BodyText"]))

        doc.build(story)

        QMessageBox.information(
            self,
            "PDF Export",
            f"Bill #{bill[0]} exported successfully.",
        )

    def edit_bill_by_id(self, bill_id):
        self.current_bill_id = bill_id
        self.edit_current_bill()

    def delete_bill_by_id(self, bill_id):
        bill = get_bill(bill_id)
        if not bill:
            return

        answer = QMessageBox.question(
            self,
            "Delete Bill",
            (
                f"Delete Bill #{bill[0]} for {bill[4]}?\\n\\n"
                "All charges belonging to this bill will also be deleted."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        delete_bill(bill_id)

        if self.current_bill_id == bill_id:
            self.current_bill_id = None

        self.refresh_all()

    def open_history_bill(self, row, column):
        item = self.ui.history_table.item(row, 0)
        if not item:
            return

        bill_id = item.data(32)
        if bill_id is None:
            return

        self.current_bill_id = int(bill_id)
        self.load_current_bill()

        bill = get_bill(self.current_bill_id)
        if not bill:
            return

        property_index = self.ui.property_combo.findData(bill[1])
        if property_index >= 0:
            self.ui.property_combo.blockSignals(True)
            self.ui.property_combo.setCurrentIndex(property_index)
            self.ui.property_combo.blockSignals(False)

        self.ui.tenant_combo.blockSignals(True)
        tenant_index = self.ui.tenant_combo.findData(bill[3])
        if tenant_index >= 0:
            self.ui.tenant_combo.setCurrentIndex(tenant_index)
        self.ui.tenant_combo.blockSignals(False)

    def select_bill_in_history(self, bill_id):
        for row in range(self.ui.history_table.rowCount()):
            item = self.ui.history_table.item(row, 0)
            if item and item.data(32) == bill_id:
                self.ui.history_table.selectRow(row)
                self.load_current_bill()
                return

    # -------------------------
    # Refresh
    # -------------------------

    def refresh_data(self):
        self.load_properties()

    def refresh_all(self):
        self.load_properties()

        if self.current_bill_id is not None:
            self.load_current_bill()
        else:
            self.clear_current_bill()
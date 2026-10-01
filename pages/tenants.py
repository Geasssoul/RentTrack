from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
    QTableWidgetItem,
    QPushButton,
)

from database import (
    get_properties,
    add_tenant,
    get_tenants,
    update_tenant,
    delete_tenant,
)

from ui.tenants_ui import TenantsUI


class TenantsPage(QWidget):

    def __init__(self):
        super().__init__()

        self.properties = []
        self.tenants = []

        self.editing_tenant_id = None

        self.ui = TenantsUI(self)

        self.connect_events()

        self.load_properties()
        self.load_tenants()

    # =====================================================
    # Refresh
    # =====================================================

    def refresh_data(self):
        """
        Re-read Properties and Tenants from the database whenever
        the Tenants page becomes active.
        """
        current_property_id = self.ui.property_combo.currentData()

        self.load_properties()

        # Restore the previous property if it still exists.
        if current_property_id is not None:
            index = self.ui.property_combo.findData(current_property_id)
            if index >= 0:
                self.ui.property_combo.blockSignals(True)
                self.ui.property_combo.setCurrentIndex(index)
                self.ui.property_combo.blockSignals(False)

        self.load_tenants()

    # =====================================================
    # Events
    # =====================================================

    def connect_events(self):

        self.ui.property_combo.currentIndexChanged.connect(
            self.property_changed
        )

        self.ui.save_button.clicked.connect(
            self.save_tenant
        )

        self.ui.cancel_button.clicked.connect(
            self.cancel_edit
        )

    # =====================================================
    # Properties
    # =====================================================

    def load_properties(self):

        self.properties = get_properties()

        self.ui.property_combo.blockSignals(True)
        self.ui.property_combo.clear()

        for property_row in self.properties:

            property_id = property_row[0]

            # Current database design uses address as the
            # displayed Property value.
            address = property_row[1]

            self.ui.property_combo.addItem(
                address,
                property_id
            )

        self.ui.property_combo.blockSignals(False)

        if self.ui.property_combo.count() > 0:

            self.ui.property_combo.setCurrentIndex(0)

        self.display_tenants()

    # =====================================================
    # Property Changed
    # =====================================================

    def property_changed(self):

        # If the user changes property while editing,
        # cancel the current edit so the tenant cannot
        # accidentally be moved to another property.
        if self.editing_tenant_id is not None:

            self.cancel_edit()

        self.display_tenants()

    # =====================================================
    # Tenants
    # =====================================================

    def load_tenants(self):

        self.tenants = get_tenants()

        self.display_tenants()

    def get_current_property_id(self):

        return self.ui.property_combo.currentData()

    def get_filtered_tenants(self):

        property_id = self.get_current_property_id()

        if property_id is None:
            return []

        filtered = []

        for tenant in self.tenants:

            # get_tenants() returns:
            # id, name, phone, email, property_id/property name
            #
            # The current project database should return
            # property_id as the fifth value.
            tenant_property_id = tenant[4]

            if tenant_property_id == property_id:
                filtered.append(tenant)

        return filtered

    def display_tenants(self):

        self.ui.table.setRowCount(0)

        filtered_tenants = self.get_filtered_tenants()

        for row, tenant in enumerate(filtered_tenants):

            self.ui.table.insertRow(row)

            tenant_id = tenant[0]

            name = tenant[1] or ""
            phone = tenant[2] or ""
            email = tenant[3] or ""

            self.ui.table.setItem(
                row,
                0,
                QTableWidgetItem(name)
            )

            self.ui.table.setItem(
                row,
                1,
                QTableWidgetItem(phone)
            )

            self.ui.table.setItem(
                row,
                2,
                QTableWidgetItem(email)
            )

            edit_button = QPushButton("Edit")

            edit_button.clicked.connect(
                lambda checked=False,
                tid=tenant_id:
                self.edit_tenant(tid)
            )

            self.ui.table.setCellWidget(
                row,
                3,
                edit_button
            )

            delete_button = QPushButton("Delete")

            delete_button.clicked.connect(
                lambda checked=False,
                tid=tenant_id:
                self.delete_tenant_clicked(tid)
            )

            self.ui.table.setCellWidget(
                row,
                4,
                delete_button
            )

    # =====================================================
    # Add / Update
    # =====================================================

    def save_tenant(self):

        property_id = self.get_current_property_id()

        if property_id is None:

            QMessageBox.warning(
                self,
                "No Property",
                "Please add a property first."
            )

            return

        name = self.ui.name_input.text().strip()
        phone = self.ui.phone_input.text().strip()
        email = self.ui.email_input.text().strip()

        if name == "":

            QMessageBox.warning(
                self,
                "Missing Name",
                "Please enter the tenant name."
            )

            return

        try:

            if self.editing_tenant_id is None:

                add_tenant(
                    name,
                    phone,
                    email,
                    property_id
                )

            else:

                update_tenant(
                    self.editing_tenant_id,
                    name,
                    phone,
                    email,
                    property_id
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Error",
                "Failed to save tenant:\n\n"
                + str(e)
            )

            return

        self.clear_form()

        self.load_tenants()

    # =====================================================
    # Edit
    # =====================================================

    def edit_tenant(self, tenant_id):

        tenant = None

        for row in self.tenants:

            if row[0] == tenant_id:
                tenant = row
                break

        if tenant is None:
            return

        # Select the tenant's property.
        property_id = tenant[4]

        index = self.ui.property_combo.findData(
            property_id
        )

        if index >= 0:
            self.ui.property_combo.blockSignals(True)
            self.ui.property_combo.setCurrentIndex(index)
            self.ui.property_combo.blockSignals(False)

        self.editing_tenant_id = tenant_id

        self.ui.name_input.setText(
            tenant[1] or ""
        )

        self.ui.phone_input.setText(
            tenant[2] or ""
        )

        self.ui.email_input.setText(
            tenant[3] or ""
        )

        self.ui.save_button.setText(
            "Update Tenant"
        )

        self.ui.cancel_button.setVisible(True)

    # =====================================================
    # Delete
    # =====================================================

    def delete_tenant_clicked(self, tenant_id):

        tenant = None

        for row in self.tenants:

            if row[0] == tenant_id:
                tenant = row
                break

        if tenant is None:
            return

        name = tenant[1] or "this tenant"

        reply = QMessageBox.question(
            self,
            "Delete Tenant",
            "Are you sure you want to delete this tenant?\n\n"
            + name
            + "\n\n"
            "Any billing records associated with this tenant "
            "may also be affected depending on the database "
            "foreign-key settings.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:

            delete_tenant(
                tenant_id
            )

        except Exception as e:

            QMessageBox.critical(
                self,
                "Error",
                "Failed to delete tenant:\n\n"
                + str(e)
            )

            return

        if self.editing_tenant_id == tenant_id:
            self.clear_form()

        self.load_tenants()

    # =====================================================
    # Cancel
    # =====================================================

    def cancel_edit(self):

        self.clear_form()

    # =====================================================
    # Clear Form
    # =====================================================

    def clear_form(self):

        self.editing_tenant_id = None

        self.ui.name_input.clear()
        self.ui.phone_input.clear()
        self.ui.email_input.clear()

        self.ui.save_button.setText(
            "Add Tenant"
        )

        self.ui.cancel_button.setVisible(
            False
        )

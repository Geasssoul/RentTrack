from PyQt6.QtWidgets import (
    QWidget,
    QMessageBox,
    QHBoxLayout,
)

from database import (
    create_database,
    add_property,
    get_properties,
    update_property,
    delete_property,
    property_exists,
)

from ui.properties_ui import PropertiesUI


class PropertiesPage(QWidget):
    """Property business logic. UI widgets are defined in PropertiesUI."""

    def __init__(self):
        super().__init__()

        create_database()

        self.ui = PropertiesUI(self)

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.ui.root)

        self.properties = []
        self.current_properties = []
        self.editing_property_id = None

        self.load_properties()

    # -------------------------
    # Data loading
    # -------------------------

    def load_properties(self):
        self.properties = get_properties()
        self.apply_search()

    def apply_search(self):
        keyword = self.ui.search_input.text().strip().lower()

        if not keyword:
            self.current_properties = list(self.properties)
        else:
            self.current_properties = [
                property_data
                for property_data in self.properties
                if keyword in (property_data[1] or "").lower()
            ]

        self.ui.display_properties(self.current_properties)

    def search_properties(self):
        self.apply_search()

    # -------------------------
    # Add / Update
    # -------------------------

    def save_property(self):
        address = self.ui.address_input.text().strip()

        if not address:
            QMessageBox.warning(
                self,
                "Missing Address",
                "Please enter a property address."
            )
            return

        if property_exists(
            address,
            exclude_property_id=self.editing_property_id
        ):
            QMessageBox.warning(
                self,
                "Duplicate Property",
                "A property with this address already exists."
            )
            return

        try:
            if self.editing_property_id is None:
                add_property(address)
            else:
                update_property(
                    self.editing_property_id,
                    address
                )
        except ValueError as e:
            QMessageBox.warning(
                self,
                "Duplicate Property",
                str(e)
            )
            return
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                "Failed to save property:\n\n" + str(e)
            )
            return

        self.cancel_edit()
        self.load_properties()

    # -------------------------
    # Edit
    # -------------------------

    def edit_property(self, property_id):
        property_data = next(
            (
                item
                for item in self.properties
                if item[0] == property_id
            ),
            None
        )

        if property_data is None:
            return

        self.editing_property_id = property_id
        self.ui.address_input.setText(
            property_data[1] or ""
        )
        self.ui.address_input.setFocus()
        self.ui.address_input.selectAll()
        self.ui.set_edit_mode(True)

    def cancel_edit(self):
        self.editing_property_id = None
        self.ui.address_input.clear()
        self.ui.set_edit_mode(False)

    # -------------------------
    # Delete
    # -------------------------

    def delete_property(self, property_id):
        property_data = next(
            (
                item
                for item in self.properties
                if item[0] == property_id
            ),
            None
        )

        if property_data is None:
            return

        address = property_data[1] or ""

        reply = QMessageBox.question(
            self,
            "Delete Property",
            "Are you sure you want to delete this property?\n\n"
            + address
            + "\n\n"
            "This will also delete tenants and bills belonging to this property.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            delete_property(property_id)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                "Failed to delete property:\n\n" + str(e)
            )
            return

        if self.editing_property_id == property_id:
            self.cancel_edit()

        self.load_properties()

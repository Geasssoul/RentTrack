from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
)


class PropertiesUI:
    """UI only. Database/business logic lives in pages/properties.py."""

    def __init__(self, page):
        self.page = page

        self.root = QWidget()
        self.layout = QVBoxLayout(self.root)

        # -------------------------
        # Title
        # -------------------------
        title = QLabel("Properties")
        self.layout.addWidget(title)

        # -------------------------
        # Search
        # -------------------------
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Address...")
        self.layout.addWidget(self.search_input)

        # -------------------------
        # Add / Edit Property
        # -------------------------
        form_layout = QHBoxLayout()

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Address")

        # Press Enter = Add Property
        self.address_input.returnPressed.connect(
            self.page.save_property
        )

        form_layout.addWidget(self.address_input)

        self.save_button = QPushButton("Add Property")
        form_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setVisible(False)
        form_layout.addWidget(self.cancel_button)

        self.layout.addLayout(form_layout)

        # -------------------------
        # Table
        # -------------------------
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels([
            "Address",
            "Edit",
            "Delete",
        ])

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents
        )

        self.layout.addWidget(self.table)

        # -------------------------
        # Events
        # -------------------------
        self.search_input.textChanged.connect(
            self.page.search_properties
        )
        self.save_button.clicked.connect(
            self.page.save_property
        )
        self.cancel_button.clicked.connect(
            self.page.cancel_edit
        )

    def display_properties(self, properties):
        """Render data only. No database logic here."""
        self.table.setRowCount(0)

        for row, property_data in enumerate(properties):
            property_id, address = property_data

            self.table.insertRow(row)

            address_item = QTableWidgetItem(address or "")
            address_item.setData(
                Qt.ItemDataRole.UserRole,
                property_id
            )
            self.table.setItem(row, 0, address_item)

            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(
                lambda checked=False, pid=property_id:
                self.page.edit_property(pid)
            )
            self.table.setCellWidget(row, 1, edit_button)

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(
                lambda checked=False, pid=property_id:
                self.page.delete_property(pid)
            )
            self.table.setCellWidget(row, 2, delete_button)

    def set_edit_mode(self, editing):
        self.cancel_button.setVisible(editing)
        self.save_button.setText(
            "Update Property" if editing else "Add Property"
        )

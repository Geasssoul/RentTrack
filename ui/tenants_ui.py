from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)


class TenantsUI:
    """
    UI-only class for the Tenants page.
    Business/database logic stays in pages/tenants.py.
    """

    def __init__(self, page):
        self.page = page

        self.build_ui()

    def build_ui(self):
        main_layout = QVBoxLayout(self.page)

        # -------------------------------------------------
        # Title
        # -------------------------------------------------

        title = QLabel("Tenants")
        main_layout.addWidget(title)

        # -------------------------------------------------
        # Property
        # -------------------------------------------------

        property_layout = QHBoxLayout()

        property_label = QLabel("Property:")
        property_label.setFixedWidth(60)
        property_layout.addWidget(property_label)

        self.property_combo = QComboBox()
        self.property_combo.setFixedWidth(260)
        property_layout.addWidget(self.property_combo)

        property_layout.addStretch()

        main_layout.addLayout(property_layout)

        # -------------------------------------------------
        # Name
        # -------------------------------------------------

        name_layout = QHBoxLayout()

        name_label = QLabel("Name:")
        name_label.setFixedWidth(60)
        name_layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Tenant name")

        # Press Enter = Add / Update Tenant
        self.name_input.returnPressed.connect(
            self.page.save_tenant
        )

        name_layout.addWidget(self.name_input)

        main_layout.addLayout(name_layout)

        # -------------------------------------------------
        # Phone
        # -------------------------------------------------

        phone_layout = QHBoxLayout()

        phone_label = QLabel("Phone:")
        phone_label.setFixedWidth(60)
        phone_layout.addWidget(phone_label)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone number")
        phone_layout.addWidget(self.phone_input)

        main_layout.addLayout(phone_layout)

        # -------------------------------------------------
        # Email
        # -------------------------------------------------

        email_layout = QHBoxLayout()

        email_label = QLabel("Email:")
        email_label.setFixedWidth(60)
        email_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email address")
        email_layout.addWidget(self.email_input)

        main_layout.addLayout(email_layout)

        # -------------------------------------------------
        # Buttons
        # -------------------------------------------------

        button_layout = QHBoxLayout()

        button_layout.addStretch()

        self.save_button = QPushButton("Add Tenant")
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setVisible(False)
        button_layout.addWidget(self.cancel_button)

        button_layout.addStretch()

        main_layout.addLayout(button_layout)

        # -------------------------------------------------
        # Tenant Table
        # -------------------------------------------------

        self.table = QTableWidget()

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels([
            "Name",
            "Phone",
            "Email",
            "Edit",
            "Delete",
        ])

        self.table.verticalHeader().setVisible(False)

        self.table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        header = self.table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.Stretch
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch
        )

        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.ResizeToContents
        )

        header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.ResizeToContents
        )

        main_layout.addWidget(self.table)

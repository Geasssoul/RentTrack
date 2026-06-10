from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidget,
    QLabel
)

from database import (
    add_property,
    get_properties
)


class PropertiesPage(QWidget):

    def __init__(self):

        super().__init__()

        layout = QVBoxLayout(self)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(
            "Property Name"
        )

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText(
            "Address"
        )

        self.save_button = QPushButton(
            "Save Property"
        )

        self.list_widget = QListWidget()

        layout.addWidget(
            QLabel("Properties")
        )

        layout.addWidget(
            self.name_input
        )

        layout.addWidget(
            self.address_input
        )

        layout.addWidget(
            self.save_button
        )

        layout.addWidget(
            self.list_widget
        )

        self.save_button.clicked.connect(
            self.save_property
        )

        self.load_properties()

    def load_properties(self):

        self.list_widget.clear()

        for row in get_properties():

            self.list_widget.addItem(
                f"{row[1]} - {row[2]}"
            )

    def save_property(self):

        name = self.name_input.text()

        address = self.address_input.text()

        if not name:
            return

        add_property(
            name,
            address
        )

        self.name_input.clear()
        self.address_input.clear()

        self.load_properties()
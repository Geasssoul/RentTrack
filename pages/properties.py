from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem
)

from database import (
    add_property,
    get_properties,
    update_property
)


class PropertiesPage(QWidget):

    def __init__(self):
        super().__init__()

        self.selected_id = None
        self.properties = []

        layout = QVBoxLayout(self)

        # ===== 标题 =====
        title = QLabel("Properties")
        layout.addWidget(title)

        # ===== 搜索 =====
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search Property...")
        layout.addWidget(self.search_input)
        self.search_input.textChanged.connect(self.search_properties)

        # ===== 输入 =====
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Property Name")
        layout.addWidget(self.name_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Address")
        layout.addWidget(self.address_input)

        # ===== 按钮 =====
        self.save_button = QPushButton("Save Property")
        layout.addWidget(self.save_button)

        # ===== Table =====
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([
            "Property Name",
            "Address"
        ])

        layout.addWidget(self.table)

        # ===== Events =====
        self.save_button.clicked.connect(self.save_property)
        self.table.cellDoubleClicked.connect(self.edit_property)

        self.load_properties()

    def load_properties(self):

        self.properties = get_properties()

        self.display_properties(self.properties)

    def display_properties(self, properties):

        self.current_properties = properties

        self.table.setRowCount(len(properties))

        for row, property in enumerate(properties):

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(property[1])
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(property[2] or "")
            )

    def save_property(self):

        name = self.name_input.text().strip()
        address = self.address_input.text().strip()

        if name == "":
            return

        if self.selected_id is None:

            add_property(name, address)

        else:

            update_property(
                self.selected_id,
                name,
                address
            )

            self.selected_id = None
            self.save_button.setText("Save Property")

        self.name_input.clear()
        self.address_input.clear()

        self.load_properties()

    def edit_property(self, row, column):

        property = self.current_properties[row]

        self.selected_id = property[0]

        self.name_input.setText(property[1])
        self.address_input.setText(property[2] or "")

        self.save_button.setText("Update Property")


    def display_properties(self, properties):

        self.current_properties = properties

        self.table.setRowCount(len(properties))

        for row, property in enumerate(properties):

            self.table.setItem(
                row,
                0,
                QTableWidgetItem(property[1])
            )

            self.table.setItem(
                row,
                1,
                QTableWidgetItem(property[2] or "")
            )


    def search_properties(self):

        keyword = self.search_input.text().lower().strip()

        if keyword == "":

            self.display_properties(self.properties)

            return

        filtered = []

        for property in self.properties:

            name = property[1].lower()
            address = (property[2] or "").lower()

            if keyword in name or keyword in address:
                filtered.append(property)

        self.display_properties(filtered)
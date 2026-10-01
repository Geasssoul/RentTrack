import sys

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QListWidget,
    QLabel,
    QStackedWidget
)

from pages.dashboard import DashboardPage
from pages.properties import PropertiesPage
from pages.tenants import TenantsPage
from pages.billing import BillingPage
from database import create_database

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("RentTrack")
        self.resize(1200, 800)

        container = QWidget()
        self.setCentralWidget(container)

        layout = QHBoxLayout(container)

        self.menu = QListWidget()
        self.menu.addItems([
            "Dashboard",
            "Properties",
            "Tenants",
            "Billing"
        ])

        # 右侧页面区域
        self.pages = QStackedWidget()

        self.pages.addWidget(DashboardPage())
        self.pages.addWidget(PropertiesPage())
        self.pages.addWidget(TenantsPage())
        self.pages.addWidget(BillingPage())
        # self.pages.addWidget(QLabel("Payments"))

        self.menu.currentRowChanged.connect(
            self.change_page
        )

        layout.addWidget(self.menu, 1)
        layout.addWidget(self.pages, 4)

        self.menu.setCurrentRow(0)

    def change_page(self, index):
        self.pages.setCurrentIndex(index)

        page = self.pages.widget(index)

        if hasattr(page, "refresh_data"):
            page.refresh_data()

app = QApplication(sys.argv)

# Ensure the SQLite database and all required tables exist before
# any page (especially Dashboard) tries to query the database.
create_database()

window = MainWindow()
window.show()

sys.exit(app.exec())
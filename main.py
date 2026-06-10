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

from pages.properties import PropertiesPage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("RentTrack")
        self.resize(1200, 800)

        container = QWidget()
        self.setCentralWidget(container)

        layout = QHBoxLayout(container)

        # 左侧菜单
        self.menu = QListWidget()
        self.menu.addItems([
            "Dashboard",
            "Properties",
            "Tenants",
            "Invoices",
            "Payments"
        ])

        # 右侧页面区域
        self.pages = QStackedWidget()

        self.pages.addWidget(QLabel("Dashboard"))
        self.pages.addWidget(PropertiesPage())
        self.pages.addWidget(QLabel("Tenants"))
        self.pages.addWidget(QLabel("Invoices"))
        self.pages.addWidget(QLabel("Payments"))

        self.menu.currentRowChanged.connect(
            self.pages.setCurrentIndex
        )

        layout.addWidget(self.menu, 1)
        layout.addWidget(self.pages, 4)

        self.menu.setCurrentRow(0)


app = QApplication(sys.argv)

window = MainWindow()
window.show()

sys.exit(app.exec())
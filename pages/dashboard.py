from datetime import datetime
from zoneinfo import ZoneInfo

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from database import get_properties, get_tenants, get_bills


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()
        self.build_ui()
        self.refresh_data()

    def build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(18)

        title = QLabel("Dashboard")
        title.setStyleSheet(
            "QLabel { font-size: 24px; font-weight: bold; }"
        )
        main_layout.addWidget(title)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(15)

        self.properties_card = self.create_card("Properties")
        self.tenants_card = self.create_card("Tenants")
        self.bills_card = self.create_card("Bills This Month")

        cards_layout.addWidget(self.properties_card["frame"])
        cards_layout.addWidget(self.tenants_card["frame"])
        cards_layout.addWidget(self.bills_card["frame"])
        main_layout.addLayout(cards_layout)

        recent_title = QLabel("Recent Bills")
        recent_title.setStyleSheet(
            "QLabel { font-size: 18px; font-weight: bold; }"
        )
        main_layout.addWidget(recent_title)

        self.recent_table = QTableWidget()
        self.recent_table.setColumnCount(5)
        self.recent_table.setHorizontalHeaderLabels(
            ["Bill #", "Tenant", "Property", "Period", "Total"]
        )
        self.recent_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.recent_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.recent_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.recent_table.verticalHeader().setVisible(False)

        header = self.recent_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        main_layout.addWidget(self.recent_table)
        main_layout.addStretch()

    def create_card(self, title_text):
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setMinimumHeight(105)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)

        title = QLabel(title_text)
        title.setStyleSheet("QLabel { font-size: 14px; }")

        value = QLabel("0")
        value.setStyleSheet(
            "QLabel { font-size: 26px; font-weight: bold; }"
        )

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(value)

        return {"frame": frame, "value": value}

    def refresh_data(self):
        properties = get_properties()
        tenants = get_tenants()
        bills = get_bills()

        self.properties_card["value"].setText(str(len(properties)))
        self.tenants_card["value"].setText(str(len(tenants)))

        now = datetime.now(ZoneInfo("Pacific/Auckland"))
        current_month = now.strftime("%Y-%m")

        bills_this_month = [
            bill for bill in bills
            if str(bill[7] or "").startswith(current_month)
        ]
        self.bills_card["value"].setText(str(len(bills_this_month)))

        recent_bills = sorted(
            bills,
            key=lambda bill: (
                str(bill[7] or ""),
                int(bill[0] or 0),
            ),
            reverse=True,
        )[:5]

        self.recent_table.setRowCount(0)

        for bill in recent_bills:
            bill_id = bill[0]
            address = bill[2] or ""
            tenant_name = bill[4] or ""
            start_date = bill[5]
            end_date = bill[6]
            total = float(bill[9] or 0)

            row = self.recent_table.rowCount()
            self.recent_table.insertRow(row)

            values = [
                str(bill_id),
                tenant_name,
                address,
                self.format_period(start_date, end_date),
                f"${total:,.2f}",
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 4):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight
                        | Qt.AlignmentFlag.AlignVCenter
                    )
                self.recent_table.setItem(row, column, item)

    @staticmethod
    def format_period(start_date, end_date):
        try:
            start = datetime.strptime(
                start_date, "%Y-%m-%d"
            ).strftime("%d/%m/%Y")
            end = datetime.strptime(
                end_date, "%Y-%m-%d"
            ).strftime("%d/%m/%Y")
            return f"{start} - {end}"
        except (ValueError, TypeError):
            return f"{start_date} - {end_date}"

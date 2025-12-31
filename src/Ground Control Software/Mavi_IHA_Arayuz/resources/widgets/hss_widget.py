from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QSplitter
)
from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtGui  import QColor

from .map_widget import MapWidget


class HssWidget(QWidget):
    """No-fly / HSS zones: table + live map overlay."""

    # Haritayı güncellemek için üst kata “yasak bölge verisi iste” sinyali
    istek_hss_koordinatlari = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Splitter – solda harita, sağda tablo
        splitter = QSplitter()
        splitter.setHandleWidth(8)

        self.map_view = MapWidget()
        self.table_box = self._build_table_panel()

        splitter.addWidget(self.map_view)
        splitter.addWidget(self.table_box)
        splitter.setSizes([800, 350])

        lay = QVBoxLayout(self)
        lay.addWidget(splitter)

    # --------------------------------------------------------------
    def _build_table_panel(self):
        grp = QGroupBox("HSS / Yasak Bölgeler")
        v   = QVBoxLayout(grp)

        self.btn_refresh = QPushButton("Yasak Bölge Bilgilerini Güncelle")
        v.addWidget(self.btn_refresh)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Merkez", "Çap (m)", "Durum"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        v.addWidget(self.table)

        self.btn_refresh.clicked.connect(self.istek_hss_koordinatlari.emit)
        return grp

    # --------------------------------------------------------------
    @pyqtSlot(list)
    def update_zones(self, zones: list):
        """Called by networking layer / simulator with list of zones."""
        self.table.setRowCount(len(zones))
        for i, z in enumerate(zones):
            self.table.setItem(i, 0, QTableWidgetItem(str(z["id"])))
            self.table.setItem(
                i, 1, QTableWidgetItem(f"{z['lat']:.4f}, {z['lon']:.4f}")
            )
            self.table.setItem(i, 2, QTableWidgetItem(str(z["diameter"])))

            status_item = QTableWidgetItem(z.get("status", "N/A"))
            if z.get("status", "").upper() == "AKTİF":
                status_item.setBackground(QColor("#c0392b"))
                status_item.setForeground(QColor("white"))
            self.table.setItem(i, 3, status_item)

        # Haritadaki overlay’i yenile
        self.map_view.set_hss_zones(zones)

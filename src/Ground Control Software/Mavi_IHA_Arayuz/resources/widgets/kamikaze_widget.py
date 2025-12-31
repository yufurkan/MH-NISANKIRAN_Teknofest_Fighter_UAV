from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QFormLayout, QLabel, QPushButton
from PyQt6.QtCore import pyqtSlot, pyqtSignal

class KamikazeWidget(QWidget):
    istek_qr_koordinati = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        control_group = QGroupBox("Otonom Kamikaze Kontrol")
        form_layout = QFormLayout(control_group)

        self.target_pos_label = QLabel("Bekleniyor...")
        self.lock_status_label = QLabel("Kilitli Değil")
        self.dive_status_label = QLabel("Başlamadı")
        self.qr_code_label = QLabel("Okunmadı")
        
        self.get_qr_button = QPushButton("QR Konumunu Sunucudan Al")
        self.start_kamikaze_button = QPushButton("OTONOM DALIŞI BAŞLAT")
        self.start_kamikaze_button.setStyleSheet("background-color: #c0392b; font-size: 16px; padding: 8px;")

        form_layout.addRow(self.get_qr_button)
        form_layout.addRow("Hedef Konumu:", self.target_pos_label)
        form_layout.addRow("Kilitlenme Durumu:", self.lock_status_label)
        form_layout.addRow("Dalış Durumu:", self.dive_status_label)
        form_layout.addRow("QR Kod Şifresi:", self.qr_code_label)
        form_layout.addRow(self.start_kamikaze_button)

        layout.addWidget(control_group)
        layout.addStretch()
        
        self.get_qr_button.clicked.connect(self.istek_qr_koordinati.emit)

    @pyqtSlot(dict)
    def update_target(self, target_data):
        lat = target_data.get('qrEnlem', 0)
        lon = target_data.get('qrBoylam', 0)
        self.target_pos_label.setText(f"Lat: {lat:.6f}, Lon: {lon:.6f}")
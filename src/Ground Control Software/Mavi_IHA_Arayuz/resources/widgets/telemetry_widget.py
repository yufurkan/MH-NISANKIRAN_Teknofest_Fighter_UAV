# resources/widgets/telemetry_widget.py
from PyQt6.QtWidgets import QWidget, QFormLayout, QLabel, QGroupBox, QVBoxLayout
from PyQt6.QtCore import pyqtSlot, QDateTime

class TelemetryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        groupbox = QGroupBox("Uçuş Bilgileri")
        layout.addWidget(groupbox)

        self.form_layout = QFormLayout(groupbox)
        
        # Etiketleri oluştururken "---" ile başlat
        self.takim_numarasi_label = QLabel("4155")
        self.enlem_label = QLabel("---")
        self.boylam_label = QLabel("---")
        self.irtifa_label = QLabel("---")
        self.hiz_label = QLabel("---")
        self.heading_label = QLabel("---")
        self.batarya_label = QLabel("---")
        self.gps_saat_label = QLabel("---")

        # Etiketleri forma ekle
        self.form_layout.addRow("Takım Numarası:", self.takim_numarasi_label)
        self.form_layout.addRow("Enlem:", self.enlem_label)
        self.form_layout.addRow("Boylam:", self.boylam_label)
        self.form_layout.addRow("İrtifa (m):", self.irtifa_label)
        self.form_layout.addRow("Hız (m/s):", self.hiz_label)
        self.form_layout.addRow("Yönelme (°):", self.heading_label)
        self.form_layout.addRow("Batarya (%):", self.batarya_label)
        self.form_layout.addRow("GPS Saati:", self.gps_saat_label)

    @pyqtSlot(object)
    def update_vfr_hud(self, msg):
        """VFR_HUD mesajından gelen verilerle arayüzü günceller."""
        self.heading_label.setText(f"{msg.heading:.1f}")
        self.hiz_label.setText(f"{msg.groundspeed:.1f}")
        # --- DÜZELTME: msg.altitude yerine msg.alt kullanılıyor ---
        self.irtifa_label.setText(f"{msg.alt:.1f}")
        # ---------------------------------------------------------

    @pyqtSlot(float, float)
    def update_gps(self, lat, lon):
        """GPS mesajından gelen verilerle arayüzü günceller."""
        self.enlem_label.setText(f"{lat:.6f}")
        self.boylam_label.setText(f"{lon:.6f}")
        # GPS saatini de sistem saatinden alıp yazabiliriz (yaklaşık olarak)
        self.gps_saat_label.setText(QDateTime.currentDateTimeUtc().toString("hh:mm:ss.zzz"))

    @pyqtSlot(object)
    def update_battery(self, msg):
        """Batarya mesajından gelen verilerle arayüzü günceller."""
        self.batarya_label.setText(f"{msg.percentage * 100:.1f}")

    def update_data(self, data):
        """Tek bir sözlükten gelen tüm verilerle telemetriyi günceller."""
        if 'lat' in data:
            self.enlem_label.setText(f"{data['lat']:.6f}")
        if 'lon' in data:
            self.boylam_label.setText(f"{data['lon']:.6f}")
        if 'alt' in data:
            self.irtifa_label.setText(f"{data['alt']:.1f}")
        if 'groundspeed' in data:
            self.hiz_label.setText(f"{data['groundspeed']:.1f}")
        if 'heading' in data:
            self.heading_label.setText(f"{data['heading']:.1f}")
        if 'battery_percentage' in data:
            self.batarya_label.setText(f"{data['battery_percentage'] * 100:.1f}")
        
        # GPS saati, veri geldiği anda sistemden alınabilir
        self.gps_saat_label.setText(QDateTime.currentDateTimeUtc().toString("hh:mm:ss.zzz"))
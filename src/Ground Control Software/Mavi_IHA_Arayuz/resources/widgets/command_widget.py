# resources/widgets/command_widget.py
from PyQt6.QtWidgets import QWidget, QGridLayout, QGroupBox, QPushButton

class CommandWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        groupbox = QGroupBox("Hızlı Komut")
        layout.addWidget(groupbox)
        
        self.command_layout = QGridLayout(groupbox)
        
        self.btn_goreve_basla = QPushButton("Göreve Başla")
        self.btn_rtl = QPushButton("RTL Yap")
        self.btn_goreve_devam = QPushButton("Göreve Devam Et")
        self.btn_gorevi_durdur = QPushButton("Görevi Durdur")
        self.btn_rotayi_temizle = QPushButton("Rotayı Temizle")
        self.btn_rotayi_gonder = QPushButton("Rotayı Gönder")
        
        # --- YENİ BUTON ---
        self.btn_rotayi_cek = QPushButton("Rotayı QGC'den Çek")
        # ------------------
        
        self.command_layout.addWidget(self.btn_goreve_basla, 0, 0)
        self.command_layout.addWidget(self.btn_rtl, 0, 1)
        self.command_layout.addWidget(self.btn_goreve_devam, 1, 0)
        self.command_layout.addWidget(self.btn_gorevi_durdur, 1, 1)
        self.command_layout.addWidget(self.btn_rotayi_temizle, 2, 0)
        self.command_layout.addWidget(self.btn_rotayi_gonder, 2, 1)
        self.command_layout.addWidget(self.btn_rotayi_cek, 3, 0, 1, 2) # İki sütunu kapla
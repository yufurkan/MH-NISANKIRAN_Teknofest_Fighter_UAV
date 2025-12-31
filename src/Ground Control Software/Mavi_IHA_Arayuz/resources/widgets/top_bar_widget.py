from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QSpacerItem, QSizePolicy
from PyQt6.QtCore import QTimer, QDateTime, pyqtSlot

class TopBarWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TopBarWidget")
        self.setFixedHeight(50)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)

        self.title_label = QLabel("KAPSÜL MAVİ HİLAL | GCS")
        self.title_label.setObjectName("TitleLabel")

        self.toggle_log_panel_button = QPushButton("Veri Akışı")
        self.status_label = QLabel("Bağlanıyor...")
        self.message_label = QLabel("")
        self.message_label.setStyleSheet("font-style: italic;")
        self.time_label = QLabel()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        self.update_time()

        layout.addWidget(self.title_label)
        layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        layout.addWidget(self.message_label)
        layout.addSpacerItem(QSpacerItem(20, 20))
        layout.addWidget(self.toggle_log_panel_button)
        layout.addWidget(self.status_label)
        layout.addWidget(self.time_label)

    def update_time(self):
        self.time_label.setText(QDateTime.currentDateTime().toString("dd.MM.yyyy hh:mm:ss"))
        
    @pyqtSlot(bool, str)
    def update_connection_status(self, is_connected, message):
        if is_connected:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #2ECC71; font-weight: bold;")
        else:
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: #E74C3C; font-weight: bold;")

    @pyqtSlot(str)
    def set_temp_message(self, message):
        self.message_label.setText(message)
        QTimer.singleShot(5000, lambda: self.message_label.setText(""))
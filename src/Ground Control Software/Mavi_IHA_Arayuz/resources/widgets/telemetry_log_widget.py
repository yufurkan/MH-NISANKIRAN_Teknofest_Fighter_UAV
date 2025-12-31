import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QTextEdit
from PyQt6.QtCore import pyqtSlot

class TelemetryLogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        groupbox = QGroupBox("Sunucu Veri Akışı")
        layout.addWidget(groupbox)
        
        log_layout = QVBoxLayout(groupbox)
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setStyleSheet("background-color: #1c1c1c; color: #a2d24a; font-family: 'Courier New', monospace;")
        log_layout.addWidget(self.log_text_edit)

    @pyqtSlot(dict)
    def log_server_response(self, data):
        formatted_json = json.dumps(data, indent=4, ensure_ascii=False)
        self.log_text_edit.append(formatted_json + "\n" + "-"*40)
        self.log_text_edit.verticalScrollBar().setValue(self.log_text_edit.verticalScrollBar().maximum())
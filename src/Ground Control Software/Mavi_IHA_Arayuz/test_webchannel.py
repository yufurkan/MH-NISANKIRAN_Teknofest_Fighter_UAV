import sys
from PyQt6.QtCore import QObject, pyqtSlot, QUrl
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel
import os

# Python'dan çağrılacak basit bir köprü nesnesi
class Bridge(QObject):
    @pyqtSlot(str)
    def show_message(self, msg):
        print(f"JavaScript'ten Mesaj Geldi: '{msg}'")

# Ana Uygulama
app = QApplication(sys.argv)

# Ana Pencere
window = QMainWindow()
window.setWindowTitle("Minimal QWebChannel Testi")
window.setGeometry(100, 100, 500, 300)

browser = QWebEngineView()
window.setCentralWidget(browser)

# WebChannel Kurulumu
channel = QWebChannel()
bridge = Bridge()
channel.registerObject("bridge", bridge)
browser.page().setWebChannel(channel)

# HTML dosyasını yükle
html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'test.html'))
browser.setUrl(QUrl.fromLocalFile(html_path))

window.show()
print("Minimal test uygulaması başlatıldı...")
print("Eğer JavaScript'teki butona tıklayınca terminalde mesaj görünürse, WebChannel çalışıyor demektir.")
sys.exit(app.exec())

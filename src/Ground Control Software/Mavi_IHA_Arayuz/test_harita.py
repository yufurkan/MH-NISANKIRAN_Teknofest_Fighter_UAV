# test_harita_fixed.py
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl

class FixedMapTest(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Düzeltilmiş Harita Test - Esri World Imagery")
        self.setGeometry(100, 100, 1200, 800)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Durum etiketi
        self.status_label = QLabel("Durum: Hazır")
        layout.addWidget(self.status_label)
        
        # Test butonları
        button_layout = QHBoxLayout()
        
        self.test_esri_btn = QPushButton("Test: Esri World Imagery")
        self.test_openstreet_btn = QPushButton("Test: OpenStreetMap")
        self.test_local_btn = QPushButton("Test: Yerel Harita")
        self.reload_btn = QPushButton("Yeniden Yükle")
        
        button_layout.addWidget(self.test_esri_btn)
        button_layout.addWidget(self.test_openstreet_btn)
        button_layout.addWidget(self.test_local_btn)
        button_layout.addWidget(self.reload_btn)
        
        layout.addLayout(button_layout)
        
        # Web görünümü
        self.browser = QWebEngineView()
        layout.addWidget(self.browser)
        
        # Buton bağlantıları
        self.test_esri_btn.clicked.connect(self.load_esri_map)
        self.test_openstreet_btn.clicked.connect(self.load_osm_map)
        self.test_local_btn.clicked.connect(self.load_local_map)
        self.reload_btn.clicked.connect(self.reload_page)
        
        # Sayfa yükleme olayları
        self.browser.page().loadFinished.connect(self.on_load_finished)
        
        # JavaScript console mesajlarını yakala
        self.browser.page().javaScriptConsoleMessage = self.handle_js_console
        
        self.status_label.setText("Durum: Hazır - Bir test butonu seçin")
        
    def handle_js_console(self, level, message, line, source):
        """JavaScript console mesajlarını yakala"""
        print(f"JS Console: {message} (Line: {line})")
        
    def load_esri_map(self):
        """Esri World Imagery haritasını yükle"""
        self.status_label.setText("Durum: Esri World Imagery yükleniyor...")
        
        esri_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Esri World Imagery Test</title>
            <meta charset="utf-8" />
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" 
                  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" 
                  crossorigin=""/>
            <style>
                html, body, #map { height: 100%; margin: 0; }
                .loading { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                          font-size: 18px; color: #333; z-index: 1000; }
            </style>
        </head>
        <body>
            <div id="loading" class="loading">Esri World Imagery yükleniyor...</div>
            <div id="map"></div>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" 
                    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" 
                    crossorigin=""></script>
            <script>
                window.onload = function() {
                    if (typeof L === 'undefined') {
                        document.getElementById('loading').innerHTML = 'Leaflet yüklenemedi!';
                        return;
                    }
                    
                    console.log("Leaflet yüklendi, harita oluşturuluyor...");
                    
                    var map = L.map('map').setView([37.8746, 32.4932], 10);
                    
                    // Esri World Imagery
                    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                        attribution: '&copy; Esri, Maxar, Earthstar Geographics',
                        maxZoom: 19
                    }).addTo(map);
                    
                    // Test marker
                    L.marker([37.8746, 32.4932])
                        .addTo(map)
                        .bindPopup('Konya - Esri World Imagery Test')
                        .openPopup();
                    
                    document.getElementById('loading').style.display = 'none';
                    console.log("Esri World Imagery haritası yüklendi!");
                };
            </script>
        </body>
        </html>
        """
        
        self.save_and_load_html(esri_html, "esri_test.html")
        
    def load_osm_map(self):
        """OpenStreetMap haritasını yükle"""
        self.status_label.setText("Durum: OpenStreetMap yükleniyor...")
        
        osm_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>OpenStreetMap Test</title>
            <meta charset="utf-8" />
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" 
                  integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" 
                  crossorigin=""/>
            <style>
                html, body, #map { height: 100%; margin: 0; }
                .loading { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); 
                          font-size: 18px; color: #333; z-index: 1000; }
            </style>
        </head>
        <body>
            <div id="loading" class="loading">OpenStreetMap yükleniyor...</div>
            <div id="map"></div>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" 
                    integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" 
                    crossorigin=""></script>
            <script>
                window.onload = function() {
                    if (typeof L === 'undefined') {
                        document.getElementById('loading').innerHTML = 'Leaflet yüklenemedi!';
                        return;
                    }
                    
                    console.log("Leaflet yüklendi, harita oluşturuluyor...");
                    
                    var map = L.map('map').setView([37.8746, 32.4932], 10);
                    
                    // OpenStreetMap
                    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                        attribution: '&copy; OpenStreetMap contributors',
                        maxZoom: 19
                    }).addTo(map);
                    
                    // Test marker
                    L.marker([37.8746, 32.4932])
                        .addTo(map)
                        .bindPopup('Konya - OpenStreetMap Test')
                        .openPopup();
                    
                    document.getElementById('loading').style.display = 'none';
                    console.log("OpenStreetMap haritası yüklendi!");
                };
            </script>
        </body>
        </html>
        """
        
        self.save_and_load_html(osm_html, "osm_test.html")
        
    def load_local_map(self):
        """Yerel harita dosyasını yükle"""
        self.status_label.setText("Durum: Yerel harita kontrol ediliyor...")
        
        # Orijinal HTML dosyasının yolunu kontrol et
        possible_paths = [
            os.path.join(os.getcwd(), "web_map", "index.html"),
            os.path.join(os.path.dirname(__file__), "web_map", "index.html"),
            os.path.join(os.path.dirname(__file__), "..", "web_map", "index.html"),
        ]
        
        html_path = None
        for path in possible_paths:
            abs_path = os.path.abspath(path)
            print(f"Kontrol ediliyor: {abs_path}")
            if os.path.exists(abs_path):
                html_path = abs_path
                break
        
        if html_path:
            url = QUrl.fromLocalFile(html_path)
            self.browser.setUrl(url)
            self.status_label.setText(f"Durum: Yerel harita yükleniyor - {html_path}")
            print(f"Yerel harita yükleniyor: {url.toString()}")
        else:
            self.status_label.setText("Durum: Yerel HTML dosyası bulunamadı!")
            print("HATA: Yerel HTML dosyası bulunamadı!")
            print("Kontrol edilen yollar:")
            for path in possible_paths:
                print(f"  - {os.path.abspath(path)}")
    
    def save_and_load_html(self, html_content, filename):
        """HTML içeriğini dosyaya kaydet ve yükle"""
        temp_path = os.path.join(os.getcwd(), filename)
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            url = QUrl.fromLocalFile(temp_path)
            self.browser.setUrl(url)
            print(f"HTML dosyası oluşturuldu ve yüklendi: {temp_path}")
            
        except Exception as e:
            print(f"HTML dosyası oluşturma hatası: {e}")
            self.status_label.setText(f"Durum: HTML dosyası oluşturma hatası - {e}")
    
    def reload_page(self):
        """Sayfayı yeniden yükle"""
        self.browser.reload()
        self.status_label.setText("Durum: Sayfa yeniden yüklendi")
        print("Sayfa yeniden yüklendi")
    
    def on_load_finished(self, success):
        """Sayfa yükleme tamamlandığında"""
        if success:
            self.status_label.setText("Durum: ✓ Sayfa başarıyla yüklendi")
            print("✓ Sayfa başarıyla yüklendi")
        else:
            self.status_label.setText("Durum: ✗ Sayfa yüklenemedi!")
            print("✗ Sayfa yüklenemedi!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FixedMapTest()
    window.show()
    sys.exit(app.exec())
import sys
import math
import requests
from io import BytesIO

# Pillow kütüphanesi (resim işleme için)
from PIL import Image

# Gerekli PyQt6 modülleri
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

# --- Yardımcı Fonksiyonlar ---
# Enlem/Boylam'ı web harita piksel koordinatlarına çevirir
def latlon_to_pixel(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return (x * 256, y * 256)

# Piksel koordinatını karo numarasına çevirir
def pixel_to_tile(px, py):
    return (math.floor(px / 256), math.floor(py / 256))

# --- Ana Pencere Sınıfı ---
class StitchedMapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Birleştirilmiş Statik Uydu Haritası (JS'siz)")
        self.setGeometry(100, 100, 800, 600)

        self.image_label = QLabel("Uydu haritası oluşturuluyor, lütfen bekleyin...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCentralWidget(self.image_label)
        self.load_stitched_map()

    def load_stitched_map(self):
        # --- Ayarlar ---
        latitude = 37.8746
        longitude = 32.4931
        zoom = 14
        width, height = 800, 600  # Pencere boyutu

        # 1. Haritanın merkezinin hangi piksele denk geldiğini hesapla
        center_px, center_py = latlon_to_pixel(latitude, longitude, zoom)

        # 2. Gerekli karo aralığını hesapla
        top_left_px = center_px - width / 2
        top_left_py = center_py - height / 2
        
        start_tile_x, start_tile_y = pixel_to_tile(top_left_px, top_left_py)
        
        # Kaç tane yatay ve dikey karo gerektiğini bul
        tiles_x = math.ceil(width / 256) + 1
        tiles_y = math.ceil(height / 256) + 1

        # 3. Son resmi oluşturmak için boş bir tuval yarat
        # Tuval, indirilen tüm karoları içerecek kadar büyük olmalı
        full_image = Image.new('RGB', (tiles_x * 256, tiles_y * 256))

        print(f"{tiles_x * tiles_y} adet uydu karosu indiriliyor...")
        
        # 4. Gerekli tüm karoları indir ve tuvale yapıştır
        for x in range(tiles_x):
            for y in range(tiles_y):
                tile_x = start_tile_x + x
                tile_y = start_tile_y + y
                
                # Esri uydu sunucusunun URL'i (anahtarsız)
                url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{tile_y}/{tile_x}"
                headers = {'User-Agent': 'My-Map-App/1.0'}
                
                try:
                    res = requests.get(url, headers=headers, timeout=5)
                    res.raise_for_status()
                    tile_image = Image.open(BytesIO(res.content))
                    full_image.paste(tile_image, (x * 256, y * 256))
                except requests.exceptions.RequestException:
                    print(f"Karo indirilemedi: z={zoom}, x={tile_x}, y={tile_y}")
                    continue
        
        print("Tüm karolar indirildi ve birleştiriliyor.")

        # 5. Oluşturulan büyük resimden tam olarak istediğimiz alanı kesip al
        final_image = full_image.crop((
            int(top_left_px % 256),
            int(top_left_py % 256),
            int(top_left_px % 256) + width,
            int(top_left_py % 256) + height
        ))

        # 6. Son resmi PyQt'de göstermek için hazırla
        # PIL resmini byte verisine çevir
        img_byte_array = BytesIO()
        final_image.save(img_byte_array, format='PNG')
        img_data = img_byte_array.getvalue()

        pixmap = QPixmap()
        pixmap.loadFromData(img_data)
        self.image_label.setPixmap(pixmap)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = StitchedMapWindow()
    window.show()
    sys.exit(app.exec())
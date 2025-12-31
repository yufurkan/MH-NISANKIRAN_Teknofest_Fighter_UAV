import os
import math
import json
import requests
from io import BytesIO
from PIL import Image

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, 
                             QPushButton, QDoubleSpinBox, QSpinBox)
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QPolygonF, QTransform
from PyQt6.QtCore import Qt, QObject, QThread, pyqtSignal, pyqtSlot, QPointF

# --- Yardımcı Fonksiyonlar ---
def latlon_to_pixel(lat: float, lon: float, zoom: int, tile_size: int = 256):
    """Verilen enlem/boylamı, belirtilen zoom seviyesindeki mutlak piksel koordinatına çevirir."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x_px = (lon + 180.0) / 360.0 * n * tile_size
    y_px = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * tile_size
    return (x_px, y_px)

def pixel_to_tile(px: float, py: float, tile_size: int = 256):
    return (math.floor(px / tile_size), math.floor(py / tile_size))

# --- Haritayı Arka Planda Oluşturacak Worker Sınıfı ---
class MapGenerator(QObject):
    map_ready = pyqtSignal(QPixmap)
    status_update = pyqtSignal(str)

    @pyqtSlot(float, float, int, int, int)
    def run(self, lat, lon, zoom, width, height):
        """Verilen koordinatlar için internetten uydu karolarını indirir ve birleştirir."""
        try:
            center_px_x, center_px_y = latlon_to_pixel(lat, lon, zoom)
            top_left_px_x = center_px_x - width / 2
            top_left_px_y = center_px_y - height / 2
            start_tile_x, start_tile_y = pixel_to_tile(top_left_px_x, top_left_px_y)
            tiles_x = math.ceil(width / 256) + 1
            tiles_y = math.ceil(height / 256) + 1
            full_image = Image.new('RGB', (tiles_x * 256, tiles_y * 256))

            self.status_update.emit(f"{tiles_x * tiles_y} karo indiriliyor...")
            for x in range(tiles_x):
                for y in range(tiles_y):
                    tile_x, tile_y_req = start_tile_x + x, start_tile_y + y
                    url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{tile_y_req}/{tile_x}"
                    try:
                        res = requests.get(url, headers={'User-Agent': 'GCS-Map-App/1.0'}, timeout=3)
                        if res.status_code == 200:
                            tile_image = Image.open(BytesIO(res.content))
                            full_image.paste(tile_image, (x * 256, y * 256))
                    except requests.exceptions.RequestException:
                        continue
            
            self.status_update.emit("Harita oluşturuluyor...")
            final_image = full_image.crop((
                int(top_left_px_x % 256), int(top_left_px_y % 256),
                int(top_left_px_x % 256) + width, int(top_left_px_y % 256) + height
            ))

            data = final_image.convert("RGBA").tobytes("raw", "RGBA")
            qim = QImage(data, final_image.size[0], final_image.size[1], QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qim)
            
            self.map_ready.emit(pixmap)
            self.status_update.emit("Harita hazır.")
        except Exception as e:
            self.status_update.emit(f"Harita hatası: {e}")

# --- Ana Harita Widget Sınıfı ---
class MapWidget(QWidget):
    start_generation = pyqtSignal(float, float, int, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        groupbox = QGroupBox("Görev Haritası")
        main_layout.addWidget(groupbox)
        
        content_layout = QVBoxLayout(groupbox)
        
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        self.lat_input = QDoubleSpinBox(); self.lat_input.setRange(-90, 90); self.lat_input.setDecimals(6); self.lat_input.setValue(47.3977)
        self.lon_input = QDoubleSpinBox(); self.lon_input.setRange(-180, 180); self.lon_input.setDecimals(6); self.lon_input.setValue(8.5456)
        self.zoom_input = QSpinBox(); self.zoom_input.setRange(1, 19); self.zoom_input.setValue(17)
        self.update_button = QPushButton("Haritayı Getir")
        self.status_label = QLabel("Hazır")
        
        control_layout.addWidget(QLabel("Enlem:"))
        control_layout.addWidget(self.lat_input)
        control_layout.addWidget(QLabel("Boylam:"))
        control_layout.addWidget(self.lon_input)
        control_layout.addWidget(QLabel("Zoom:"))
        control_layout.addWidget(self.zoom_input)
        control_layout.addWidget(self.update_button)
        control_layout.addStretch()
        control_layout.addWidget(self.status_label)
        
        self.map_label = QLabel("Haritayı getirmek için butona basın.")
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_label.setStyleSheet("background-color: #2C3E50; color: white;")

        content_layout.addWidget(control_panel)
        content_layout.addWidget(self.map_label, 1)

        self.map_thread = QThread()
        self.map_generator = MapGenerator()
        self.map_generator.moveToThread(self.map_thread)
        
        self.update_button.clicked.connect(self.request_new_map)
        self.start_generation.connect(self.map_generator.run)
        self.map_generator.map_ready.connect(self.on_map_ready)
        self.map_generator.status_update.connect(self.status_label.setText)
        
        self.map_thread.start()
        
        self.base_map_pixmap = QPixmap()
        self.vehicle_gps_position = None
        self.vehicle_heading = 0.0
        self.received_route = []
        
        # Uçak ikonunu yükle
        icon_path = os.path.join(os.path.dirname(__file__), '..', '..', 'icons', 'plane_icon.png')
        self.vehicle_icon = QPixmap(icon_path)
        if self.vehicle_icon.isNull():
            print(f"UYARI: Uçak ikonu yüklenemedi! Yol: {icon_path}")
        else:
            self.vehicle_icon = self.vehicle_icon.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def request_new_map(self):
        lat, lon, zoom = self.lat_input.value(), self.lon_input.value(), self.zoom_input.value()
        width = self.map_label.width() if self.map_label.width() > 50 else 800
        height = self.map_label.height() if self.map_label.height() > 50 else 600
        self.status_label.setText("Harita isteniyor...")
        self.start_generation.emit(lat, lon, zoom, width, height)

    @pyqtSlot(QPixmap)
    def on_map_ready(self, pixmap):
        self.base_map_pixmap = pixmap
        self.redraw_overlays()

    def redraw_overlays(self):
        """Tüm dinamik elemanları (İHA, rota vb.) temel haritanın üzerine çizer."""
        if self.base_map_pixmap.isNull(): return
        
        overlay_pixmap = self.base_map_pixmap.copy()
        painter = QPainter(overlay_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        map_lat, map_lon, map_zoom = self.lat_input.value(), self.lon_input.value(), self.zoom_input.value()
        center_px_x, center_px_y = latlon_to_pixel(map_lat, map_lon, map_zoom)

        # Alınan rotayı çiz
        if self.received_route:
            painter.setPen(QPen(QColor("#3498DB"), 3, Qt.PenStyle.SolidLine))
            points_to_draw = []
            for wp in self.received_route:
                wp_px_x, wp_px_y = latlon_to_pixel(wp['lat'], wp['lon'], map_zoom)
                draw_x = (overlay_pixmap.width() / 2) + (wp_px_x - center_px_x)
                draw_y = (overlay_pixmap.height() / 2) + (wp_px_y - center_px_y)
                points_to_draw.append(QPointF(draw_x, draw_y))
            painter.drawPolyline(QPolygonF(points_to_draw))

        # Araç pozisyonunu çiz
        if self.vehicle_gps_position:
            vehicle_px_x, vehicle_px_y = latlon_to_pixel(self.vehicle_gps_position[0], self.vehicle_gps_position[1], map_zoom)
            draw_x = (overlay_pixmap.width() / 2) + (vehicle_px_x - center_px_x)
            draw_y = (overlay_pixmap.height() / 2) + (vehicle_px_y - center_px_y)
            
            if self.vehicle_icon.isNull():
                painter.setBrush(QColor("#E74C3C"))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(QPointF(draw_x, draw_y), 8, 8)
            else:
                painter.save()
                painter.translate(draw_x, draw_y)
                painter.rotate(self.vehicle_heading)
                icon_rect = self.vehicle_icon.rect()
                target_pos = QPointF(-icon_rect.width() / 2, -icon_rect.height() / 2)
                painter.drawPixmap(target_pos.toPoint(), self.vehicle_icon)
                painter.restore()
        
        painter.end()
        self.map_label.setPixmap(overlay_pixmap)
        
    @pyqtSlot(dict)
    def update_data(self, data):
        """Tek bir sözlükten gelen tüm verilerle haritayı günceller."""
        if 'heading' in data:
            self.vehicle_heading = data['heading']
        if 'lat' in data and 'lon' in data:
            self.update_vehicle_position(data['lat'], data['lon'])

    def update_vehicle_position(self, lat, lon):
        self.vehicle_gps_position = (lat, lon)
        self.redraw_overlays()
        
    @pyqtSlot(list)
    def draw_received_route(self, waypoints_list):
        """QGC'den çekilen rota verisini saklar ve haritayı yeniden çizer."""
        print(f"{len(waypoints_list)} adet waypoint haritaya çizilmek üzere alındı.")
        self.received_route = waypoints_list
        self.redraw_overlays()
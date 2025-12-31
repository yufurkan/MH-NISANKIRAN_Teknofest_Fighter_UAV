import time
import random
import math
from PyQt6.QtCore import QObject, pyqtSignal

# Gerçek MAVLink mesajındaki gibi 'altitude' yerine 'alt' kullanalım
class DummyVFRHUD:
    def __init__(self, altitude, groundspeed, heading):
        self.alt = altitude # Değişken adı 'alt' olarak düzeltildi
        self.groundspeed = groundspeed
        self.heading = heading

class DummyBatteryState:
    def __init__(self, percentage):
        self.percentage = percentage

class VeriSimulatoru(QObject):
    connection_status_changed = pyqtSignal(bool, str)
    new_vfr_hud_data = pyqtSignal(object)
    new_gps_data = pyqtSignal(float, float)
    new_battery_data = pyqtSignal(object)
    kamikaze_target_received = pyqtSignal(dict)
    hss_zone_update = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.running = False
        self.latitude = 37.8743
        self.longitude = 32.4932
        self.altitude = 1200.0
        self.heading = 45.0
        self.speed = 20.0
        self.battery = 1.0
        self.kamikaze_target = {'lat': 37.8720, 'lon': 32.5000}
        self.hss_zones = [
            {'id': 1, 'lat': 37.8800, 'lon': 32.4980, 'diameter': 400, 'status': 'AKTİF'},
            {'id': 2, 'lat': 37.8650, 'lon': 32.4850, 'diameter': 300, 'status': 'BEKLEMEDE'}
        ]

    def start_simulation(self):
        self.running = True
        print("Veri Simülatörü Başlatıldı.")
        self.connection_status_changed.emit(True, "SIMULATOR_ACTIVE")
        
        self.kamikaze_target_received.emit(self.kamikaze_target)
        self.hss_zone_update.emit(self.hss_zones)

        angle = 0
        counter = 0
        while self.running:
            self.altitude += random.uniform(-0.5, 0.5)
            self.speed = max(0, self.speed + random.uniform(-0.1, 0.1))
            self.heading = (self.heading + random.uniform(-1, 1) + 360) % 360
            self.battery = max(0, self.battery - 0.00005)
            angle += 0.01
            self.latitude += math.cos(angle) * 0.00005
            self.longitude += math.sin(angle) * 0.00005

            vfr_hud_msg = DummyVFRHUD(self.altitude, self.speed, self.heading)
            self.new_vfr_hud_data.emit(vfr_hud_msg)
            battery_msg = DummyBatteryState(self.battery)
            self.new_battery_data.emit(battery_msg)
            self.new_gps_data.emit(self.latitude, self.longitude)
            
            if counter > 0 and counter % 50 == 0: 
                if self.hss_zones[1]['status'] == 'BEKLEMEDE':
                    print("Simülatör: HSS Bölge 2 aktif edildi.")
                    self.hss_zones[1]['status'] = 'AKTİF'
                    self.hss_zone_update.emit(self.hss_zones)

            time.sleep(0.2)
            counter +=1
            
        print("Veri Simülatörü Durduruldu.")

    def stop_simulation(self):
        self.running = False
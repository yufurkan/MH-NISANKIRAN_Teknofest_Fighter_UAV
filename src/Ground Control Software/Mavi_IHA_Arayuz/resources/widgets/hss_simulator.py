# resources/hss_simulator.py
from PyQt6.QtCore import QObject, pyqtSignal
import random
import time


class HssSimulator(QObject):
    """Gerçek sunucu yerine sahte HSS (no-fly) bölgeleri üretir."""

    hss_zone_update = pyqtSignal(list)   # -> HssWidget.update_zones(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        random.seed(time.time())

    # ------------------------------------------------------------------
    def produce_new_zones(self):
        """Rasgele 2-5 bölge oluşturup sinyal yayar."""
        zones = []
        num = random.randint(2, 5)
        for i in range(num):
            zones.append({
                "id":        i + 1,
                "lat":       47.3977 + random.uniform(-0.01, 0.01),
                "lon":       8.5456 + random.uniform(-0.01, 0.01),
                "diameter":  random.choice([200, 300, 400]),   # metre
                "status":    random.choice(["AKTİF", "PASİF"])
            })
        self.hss_zone_update.emit(zones)

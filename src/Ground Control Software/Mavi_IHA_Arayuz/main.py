import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter, QVBoxLayout,
    QHBoxLayout, QTabWidget, QSizePolicy
)
from PyQt6.QtCore import Qt

# Dahili modüller
from mavlink_manager                           import MavlinkManager
from resources.widgets.hss_simulator           import HssSimulator
from resources.widgets.top_bar_widget          import TopBarWidget
from resources.widgets.camera_widget           import CameraWidget
from resources.widgets.map_widget              import MapWidget
from resources.widgets.command_widget          import CommandWidget
from resources.widgets.indicators_widget       import IndicatorsWidget
from resources.widgets.telemetry_widget        import TelemetryWidget
from resources.widgets.kamikaze_widget         import KamikazeWidget
from resources.widgets.hss_widget              import HssWidget


class AnaPencere(QMainWindow):
    def __init__(self, mav_mgr: MavlinkManager, hss_sim: HssSimulator) -> None:
        super().__init__()
        self.mav_mgr, self.hss_sim = mav_mgr, hss_sim
        self.showMaximized()      # tavsiye edilen
        # ——————— Stil (renk paleti değişmeden) ———————
        try:
            with open("styles.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("Uyarı: styles.qss bulunamadı – varsayılan tema uygulanıyor.")

        self.setWindowTitle("KAPSÜL MAVİ HİLAL | GCS [CANLI MOD]")

        # ---------------- Ekran boyutu & konum ----------------
        avail = QApplication.primaryScreen().availableGeometry()
        w = min(int(avail.width()  * 0.85), avail.width()  - 10)
        h = min(int(avail.height() * 0.85), avail.height() - 10)
        self.resize(w, h)
        frame = self.frameGeometry()
        frame.moveCenter(avail.center())
        self.move(frame.topLeft())

        # ---------------- Widget’ler ----------------
        self.top_bar       = TopBarWidget()

        self.map_view      = MapWidget()
        self.kamikaze_view = KamikazeWidget()
        self.hss_view      = HssWidget()
        self.camera_view   = CameraWidget()

        self.commands      = CommandWidget()
        self.indicators    = IndicatorsWidget()
        self.telemetry     = TelemetryWidget()

        # Alt üç widget’ın min boyut kısıtlarını gevşet
        for wdg in (self.commands, self.indicators, self.telemetry, self.camera_view):
            wdg.setMinimumSize(0, 0)
            wdg.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # --------- ÜST panel: sekmeler + kamera ---------
        tabs = QTabWidget()
        tabs.addTab(self.map_view,      "Görev Haritası")
        tabs.addTab(self.kamikaze_view, "Kamikaze Görevi")
        tabs.addTab(self.hss_view,      "HSS / Yasak Bölgeler")

        h_split = QSplitter(Qt.Orientation.Horizontal); h_split.setHandleWidth(8)
        h_split.addWidget(tabs)
        h_split.addWidget(self.camera_view)
        h_split.setStretchFactor(0, 3)          # ~60 %
        h_split.setStretchFactor(1, 2)          # ~40 %

        # --------- ALT panel: komut + göstergeler + telemetri ---------
        bottom_widget = QWidget()
        b_lay = QHBoxLayout(bottom_widget); b_lay.setContentsMargins(0, 0, 0, 0)
        b_lay.addWidget(self.commands)
        b_lay.addWidget(self.indicators)
        b_lay.addWidget(self.telemetry)

        bottom_h = max(260, int(avail.height() * 0.25))   # min 260 px, max %25
        bottom_widget.setFixedHeight(bottom_h)

        # --------- Ana dikey splitter ---------
        v_split = QSplitter(Qt.Orientation.Vertical); v_split.setHandleWidth(8)
        v_split.addWidget(h_split)
        v_split.addWidget(bottom_widget)
        v_split.setStretchFactor(0, 3)   # üst 75 %
        v_split.setStretchFactor(1, 1)   # alt 25 %

        # --------- Merkez layout ---------
        central = QWidget()
        main_v  = QVBoxLayout(central); main_v.setContentsMargins(5, 5, 5, 5)
        main_v.addWidget(self.top_bar)
        main_v.addWidget(v_split)
        self.setCentralWidget(central)

        # --------- Sinyaller ---------
        self._bagla_sinyaller()

    # ---------- sinyal bağlantıları ----------
    def _bagla_sinyaller(self):
        self.mav_mgr.connection_status_changed.connect(self.top_bar.update_connection_status)
        self.mav_mgr.new_telemetry_data.connect(self.indicators.update_data)
        self.mav_mgr.new_telemetry_data.connect(self.telemetry.update_data)
        self.mav_mgr.new_telemetry_data.connect(self.map_view.update_data)

        self.commands.btn_rotayi_cek.clicked.connect(self.mav_mgr.request_mission_from_vehicle)
        self.mav_mgr.mission_received.connect(self.map_view.draw_received_route)

        self.hss_view.istek_hss_koordinatlari.connect(self.hss_sim.produce_new_zones)
        self.hss_sim.hss_zone_update.connect(self.hss_view.update_zones)

    # ---------- pencere kapanışı ----------
    def closeEvent(self, event) -> None:
        self.mav_mgr.stop_listening()
        super().closeEvent(event)


# ---------------- Entry point ----------------
def main():
    app = QApplication(sys.argv)

    mav_mgr = MavlinkManager(udp_endpoint="udp:127.0.0.1:14552")
    hss_sim = HssSimulator()

    win = AnaPencere(mav_mgr, hss_sim)
    win.show()


    sys.exit(app.exec())


if __name__ == "__main__":
    main()

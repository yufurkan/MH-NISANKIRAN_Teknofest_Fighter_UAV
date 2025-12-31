import time
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from pymavlink import mavutil

class MavlinkManager(QObject):
    """Pixhawk bağlantısını yönetir, MAVLink paketlerini çözer ve arayüze sinyaller yollar."""

    connection_status_changed = pyqtSignal(bool, str)
    new_telemetry_data = pyqtSignal(dict)
    mission_received = pyqtSignal(list)

    def __init__(self, udp_endpoint: str = "udp:127.0.0.1:14552") -> None:
        super().__init__()
        self.udp_endpoint = udp_endpoint
        self.vehicle: mavutil.mavlink_connection | None = None
        self.running = True
        self.telemetry_dict: dict = {}
        self.mission_waypoints: list = []
        self.mission_count = 0
        self.listener_thread = QThread()
        self.moveToThread(self.listener_thread)
        self.listener_thread.started.connect(self._connect_and_listen)
        self.listener_thread.start()

    def _connect_and_listen(self) -> None:
        try:
            print(f"MAVProxy'ye bağlanılıyor: {self.udp_endpoint}")
            self.vehicle = mavutil.mavlink_connection(self.udp_endpoint, autoreconnect=True)
            self.connection_status_changed.emit(False, "Heartbeat bekleniyor…")
            if not self.vehicle.wait_heartbeat(timeout=5):
                self.connection_status_changed.emit(False, "Heartbeat yok")
                return
            print("Heartbeat alındı! Bağlantı başarılı.")
            self.connection_status_changed.emit(True, "Bağlandı")

            while self.running:
                msg = self.vehicle.recv_match(blocking=True, timeout=1)
                if not msg: continue
                
                if self._process_telemetry_message(msg):
                    self.new_telemetry_data.emit(self.telemetry_dict.copy())
                
                self._process_mission_message(msg)
        except Exception as e:
            print(f"Bağlantı hatası: {e}")
            self.connection_status_changed.emit(False, f"Hata: {e}")

    def _process_telemetry_message(self, msg) -> bool:
        t = msg.get_type()
        changed = False
        if t == "GLOBAL_POSITION_INT":
            self.telemetry_dict["lat"] = msg.lat / 1e7
            self.telemetry_dict["lon"] = msg.lon / 1e7
            self.telemetry_dict["alt"] = msg.relative_alt / 1000.0
            changed = True
        elif t == "VFR_HUD":
            self.telemetry_dict["groundspeed"] = msg.groundspeed
            self.telemetry_dict["heading"] = msg.heading
            changed = True
        elif t == "SYS_STATUS":
            self.telemetry_dict["battery_percentage"] = msg.battery_remaining
            changed = True
        return changed

    def _process_mission_message(self, msg) -> None:
        t = msg.get_type()
        if t == "MISSION_COUNT":
            self.mission_count = msg.count
            print(f"DEBUG: MISSION_COUNT mesajı alındı. Waypoint sayısı: {self.mission_count}")
            self.mission_waypoints = []
            if self.mission_count > 0:
                print("DEBUG: Waypoint 0 isteniyor...")
                self.vehicle.mav.mission_request_int_send(
                    self.vehicle.target_system, self.vehicle.target_component, 0
                )
        elif t == "MISSION_ITEM_INT":
            print(f"DEBUG: MISSION_ITEM_INT (seq: {msg.seq}) mesajı alındı.")
            if msg.command == mavutil.mavlink.MAV_CMD_NAV_WAYPOINT:
                wp = {'lat': msg.x / 1e7, 'lon': msg.y / 1e7, 'alt': msg.z}
                self.mission_waypoints.append(wp)
            
            if msg.seq < self.mission_count - 1:
                next_seq = msg.seq + 1
                print(f"DEBUG: Waypoint {next_seq} isteniyor...")
                self.vehicle.mav.mission_request_int_send(
                    self.vehicle.target_system, self.vehicle.target_component, next_seq
                )
            else:
                print(f"DEBUG: Tüm görev ({len(self.mission_waypoints)} waypoint) başarıyla indirildi.")
                self.mission_received.emit(self.mission_waypoints)
                print("DEBUG: Görev alımının tamamlandığına dair ACK gönderiliyor.")
                self.vehicle.mav.mission_ack_send(
                    self.vehicle.target_system, self.vehicle.target_component, mavutil.mavlink.MAV_MISSION_ACCEPTED
                )

    def request_mission_from_vehicle(self) -> None:
        if self.vehicle:
            print("DEBUG: Rota listesi talep ediliyor (MISSION_REQUEST_LIST)...")
            self.vehicle.mav.mission_request_list_send(
                self.vehicle.target_system, self.vehicle.target_component
            )
        else:
            print("HATA: Rota çekilemedi, İHA'ya bağlı değil.")

    def stop_listening(self) -> None:
        self.running = False
        if self.listener_thread.isRunning():
            self.listener_thread.quit()
            self.listener_thread.wait()
        if self.vehicle:
            try: self.vehicle.close()
            except Exception: pass
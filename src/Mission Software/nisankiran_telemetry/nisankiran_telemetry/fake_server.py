import rclpy
from rclpy.node import Node
from px4_msgs.msg import VehicleLocalPosition
from flask import Flask, jsonify, request
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
import threading
import time
import math

app = Flask(__name__)

#daha sonra düzenleyecem launch a eklenmeyecek


# tüm uçakların anlık verilerinin tutulduğu havuz
FLEET_METRICS = {}

@app.route('/api/telemetri_gonder', methods=['GET', 'POST'])
def get_metrics():
    # teknofest yarışma dökümanındaki formata benzetilmiş uydurma paket
    # normalde x y z değil enlem boylam istenir ama simülasyon xyz'sini basıyoz
    konum_bilgileri = []
    
    for uav_id, data in FLEET_METRICS.items():
        paket = {
            "takim_numarasi": int(uav_id),
            "IHA_enlem": data['x'],     # aslında x koordinatı
            "IHA_boylam": data['y'],    # aslında y koordinatı
            "IHA_irtifa": data['z'],    # aslında z (yerden yükseklik)
            "IHA_dikilme": 0.0,         # pitch - şimdilik uydurma
            "IHA_yonelme": data['heading'], # derece cinsinden yaw
            "IHA_yatis": 0.0,           # roll - uydurma
            "IHA_hiz": 15.0,            # m/s uydurma hız
            "IHA_batarya": 99,          # bitmeyen batarya :)
            "IHA_otonom": 1,
            "IHA_kilitlenme": 0,
            "Hedef_merkez_X": 0,
            "Hedef_merkez_Y": 0,
            "Hedef_genislik": 0,
            "Hedef_yukseklik": 0,
            "Zaman_farki": 93
        }
        konum_bilgileri.append(paket)

    # sunucu saati
    sunucu_saati = {
        "gun": 16, "saat": 14, "dakika": 30, "saniye": 15, "milisaniye": 500
    }

    #paketi bas
    return jsonify({
        "sunucusaati": sunucu_saati,
        "konumBilgileri": konum_bilgileri
    })


class FakeServerNode(Node):
    def __init__(self):
        super().__init__('fake_server_node')
        
        # QoS profili patlamasın diye best effort
        self.qos_fast = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT, 
            durability=DurabilityPolicy.VOLATILE,
            depth=1 
        )


        self.active_subs = set()
        
        self.create_timer(2.0, self.update_subscriptions)

        self.get_logger().info("Gazebo aktarıcı hazırlandı.")



    def update_subscriptions(self):
        topic_list = self.get_topic_names_and_types()
        for name, types in topic_list:
            if 'vehicle_local_position' in name and 'px4_msgs/msg/VehicleLocalPosition' in types:
                if name not in self.active_subs:
                    try:
                        # id'yi çek px4_1 -> 1
                        uav_id = name.split('/')[1].replace('px4_', '')
                        
                        # lambda'daki late binding hatasını ezmek için uid=uav_id ataması yapıldı
                        self.create_subscription(
                            VehicleLocalPosition, 
                            name, 
                            lambda msg, uid=uav_id: self.metric_cb(msg, uid), 
                            self.qos_fast
                        )
                        self.active_subs.add(name)
                        self.get_logger().info(f"Yeni ucak eklendi ve dinleniyor: UAV_{uav_id}")
                    except Exception as e:
                        self.get_logger().error(f"Ucak eklenirken patladı: {e}")


    # veriyi havuza at
    def metric_cb(self, msg, uav_id):
        if msg.timestamp > 0:
            FLEET_METRICS[uav_id] = {
                'x': float(msg.x),
                'y': float(msg.y),
                'z': float(-msg.z), 
                'heading': float(msg.heading * (180.0 / math.pi)) 
            }


def main(args=None):
    # ros2'yi ayrı bir thread'de (arkaplanda) çalıştır ki flask sunucusunu kitlemesin
    # daemon=True 
    threading.Thread(target=lambda: (rclpy.init(args=args), rclpy.spin(FakeServerNode())), daemon=True).start()
    
    # flask sunucusunu ayağa kaldır
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
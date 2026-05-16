import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseArray, Pose
from px4_msgs.msg import VehicleLocalPosition
from std_msgs.msg import Bool
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
from nisankiran_interfaces.srv import TargetKill
import math
import time

from dataclasses import dataclass, field
from typing import Dict, Optional

# struct
@dataclass
class EnemyState:
    id: str
    last_position: VehicleLocalPosition = None
    hit_count: int = 0
    last_seen_time: float = 0.0

    def is_active(self, timeout=3.0):
        
        return (time.time() - self.last_seen_time) < timeout # 3 saniye timeout

    


class WSORadar(Node):
    def __init__(self):
        super().__init__('wso_radar_node')

        
        # QoS PROFİLLERİ -----------
        # kritik komutlar 
        self.qos_reliable = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=rclpy.qos.HistoryPolicy.KEEP_LAST,
            depth=1
        )

        # Telemetri 
        self.qos_fast_telemetry = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT, 
            durability=DurabilityPolicy.VOLATILE,
            history=rclpy.qos.HistoryPolicy.KEEP_LAST,
            depth=1 
        )     

        # QoS PROFİLLERİ -----------/
       


        #PUBLISHERS 

        # 10ları kaldırdım
        self.enemy_pub = self.create_publisher(PoseArray, '/enemy_telemetry', self.qos_fast_telemetry)
        self.hedef_pub = self.create_publisher(Pose, '/locked_target', self.qos_reliable)  # qos_fast_telemetry de sıkıntı çıktı reliable daha güvenilir
        self.weapons_pub = self.create_publisher(Bool, '/weapons_hot', self.qos_reliable)
        
        
        # özel kill servisi
        self.kill_service = self.create_service(TargetKill, 'confirm_kill', self.handle_kill_request)


        self.my_pos: Optional[VehicleLocalPosition] = None
        self.targets: Dict[str, EnemyState] = {} # UAV_ID -> EnemyState eski adı(TrackedTarget) 
        self.active_subs = set()
        self.locked_target_id: Optional[str] = None 

        #  TIMERS 
        self.create_timer(2.0, self.update_subscriptions)
        self.create_timer(0.5, self.radar_loop)
        
        self.get_logger().info("WSO Init")



    # Özel servis vision ie haberleş
    def handle_kill_request(self, request, response):
        if self.locked_target_id and self.locked_target_id in self.targets: # id none and id in targets
            self.get_logger().info(f"Target destroyed: {request.target_id}")
            
            # nesne üzerinden hit_count artırımı 
            self.targets[self.locked_target_id].hit_count += 1
            self.locked_target_id = None
            
            hot_msg = Bool()
            hot_msg.data = False
            self.weapons_pub.publish(hot_msg)
            
        response.success = True
        return response
    


    #Tüm uçakları süreki tara
    def update_subscriptions(self):
        topic_list = self.get_topic_names_and_types()

        for name, types in topic_list:
            if 'vehicle_local_position' in name and 'px4_msgs/msg/VehicleLocalPosition' in types:
                if name not in self.active_subs:
                    # eğer takip edilen topicler yok olursa destroy da edebilirim ilerde burda ancak gerek yok
                    # yeni subcribtoinları ekle
                    self.create_subscription(VehicleLocalPosition, name, lambda msg, n=name: self.universal_cb(msg, n), self.qos_fast_telemetry) # qos_profile_sensor_data yerine kendi profilimiz
                    self.active_subs.add(name)
                    




    # isim atamalarını sağla
    def universal_cb(self, msg, topic_name):
        if msg.timestamp > 0:
            try:
                uav_id = topic_name.split('/')[1].replace('px4_', '')
                if uav_id == '1': 
                    self.my_pos = msg
                else:
                    if uav_id not in self.targets:
                        self.targets[uav_id] = EnemyState(id=uav_id)
                    
                    
                    self.targets[uav_id].last_position = msg
                    self.targets[uav_id].last_seen_time = time.time()
            except Exception as e:
                self.get_logger().error(f"CB Error: {e}")





    def radar_loop(self):
        if self.my_pos is None or not self.targets:
            return

        # hedef sec
        if self.locked_target_id is None or self.locked_target_id not in self.targets:
            best_target_id = None
            min_hits = float('inf')
            min_dist = float('inf') # Kriter değişikliği: Hizalanma yerine mesafe

            for uav_id, target_obj in self.targets.items():
                # last_position kontrolü (Sınıf tanımındadan dolayı ismi değişti)

                if not target_obj.is_active(timeout=3.0):
                    continue


                pos = target_obj.last_position 
                if pos is None:
                    continue
                
                # Mesafe Hesabı 
                dx = pos.x - self.my_pos.x
                dy = pos.y - self.my_pos.y
                dz = pos.z - self.my_pos.z
                dist = math.sqrt(dx**2 + dy**2 + dz**2)

                # SEÇİM ---------------------------
                # en az vurulan
                if target_obj.hit_count < min_hits:
                    min_hits = target_obj.hit_count
                    min_dist = dist
                    best_target_id = uav_id
                
                # en yakın olan
                elif target_obj.hit_count == min_hits:
                    if dist < min_dist:
                        min_dist = dist
                        best_target_id = uav_id
                # SEÇİM ---------------------------/

            if best_target_id:
                self.locked_target_id = best_target_id
                self.get_logger().info(f"Target locked: UAV_{self.locked_target_id} (Dist: {min_dist:.1f}m)")
            

        # ------
        if self.locked_target_id and self.locked_target_id in self.targets:
            target_obj = self.targets[self.locked_target_id]

            # kaybolan uçağın son verisini yayınlamaya devam edebiliriz  bu yüzden timout kontrolünü kullanıcaz ve 
            if not target_obj.is_active(timeout=3.0):
                self.get_logger().warn(f"Lost track of UAV_{self.locked_target_id}! Breaking lock.")
                self.locked_target_id = None
                
                # Weapons Hotı kapat 
                hot_msg = Bool()
                hot_msg.data = False
                self.weapons_pub.publish(hot_msg)
                return



            target_msg = target_obj.last_position
            
            if target_msg:
                #düşmaının konumuu yayınla------
                self.publish_target(target_msg) # Koordinatları Pose olarak basar
                #düşmaının konumuu yayınla------/

                # mesafe hesaplarken irtifa katılmalı mı tartış

                # Weapons Hot-------------------
                dx = target_msg.x - self.my_pos.x
                dy = target_msg.y - self.my_pos.y
                dz = target_msg.z - self.my_pos.z
                dist = math.sqrt(dx**2 + dy**2 + dz**2)
   
                angle_to_target = math.atan2(dy, dx)
                alignment = math.cos(self.my_pos.heading - angle_to_target)

                # Hedef 100m yakınasa ve burn hedefe %40'den fazla dönükse kamera 120derce 1/3 ü olarak güncelleyebilirim 
                # visiondaki çerçeve kontrolü eklenince önemi kalmaz 
                is_hot = bool(dist < 100.0 and alignment > 0.4)
                
                hot_msg = Bool()
                hot_msg.data = is_hot
                self.weapons_pub.publish(hot_msg)
                # Weapons Hot-------------------/



    #düşman konumunu yayınla
    def publish_target(self, target_msg):
        p = Pose()
        p.position.x = float(target_msg.x)
        p.position.y = float(target_msg.y)
        p.position.z = float(target_msg.z)
        self.hedef_pub.publish(p)





def main(args=None):
    rclpy.init(args=args)
    rclpy.spin(WSORadar())
    rclpy.shutdown()

if __name__ == '__main__':
    main()
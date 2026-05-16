import os
# terminali kapatan uyarıları gizle
os.environ["QT_LOGGING_RULES"] = "qt.qpa.fonts.warning=false;default.warning=false"

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray, Bool
from cv_bridge import CvBridge
import cv2
from ultralytics import YOLO
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from nisankiran_interfaces.srv import TargetKill

class VisionTracker(Node):
    def __init__(self):
        super().__init__('vision_tracker_node')
        self.get_logger().info("[VISION] Module initialized with high tolerance.")

        self.model = YOLO('/home/federstation/nisankiran_ws/best.pt')# model yolu
        self.bridge = CvBridge()


        # özel protokol için
        qos_reliable = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=rclpy.qos.HistoryPolicy.KEEP_LAST,
            depth=1
        )


        # kamera UDP de de best effort ayaralanacak similasyon için bu şekilde ancak rocket ac 5 den gönderilirken UDP yi ayarlıyıcam best effort olarak
        #qos ayarları kamera
        qos_camera = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=rclpy.qos.HistoryPolicy.KEEP_LAST,
            depth=1
        )


        # gz ros bridge gerekiyo her seferinde
        # kamera yolu 
        self.subscription = self.create_subscription(Image,'/world/default/model/rc_cessna_1/link/base_link/sensor/camera/image',self.image_callback,qos_camera)# 10 u kaldırdım yeni profil uyguladım. kamera için 10 görüntü tutmaya gerek yok jetsonu yormasın Son parametre Qos profile | int Eski(profil 10 :Keep last 10 depth reliable)
            

        #kamera görüntüsü best effort olmalı 
        self.weapons_hot_sub = self.create_subscription(Bool, '/weapons_hot', self.weapons_hot_cb, qos_reliable)


        self.bbox_pub = self.create_publisher(Float32MultiArray, '/enemy_bbox', 10)
        self.kill_client = self.create_client(TargetKill, 'confirm_kill')



        self.lock_frames = 0#kilitliyken
        self.lost_frames = 0#kilitlenememe timoutu

        self.REQUIRED_FRAMES_FOR_KILL = 120 # sayaç yarışma için kilitlenme süresini 5sn yapıcaz şuan 4 civarı
        self.MAX_TOLERANCE_FRAMES = 35 # yaklaşık 1 saniye kayıp payı (35 kare yaptım) biraz düşebilir
        self.is_weapons_hot = False



    # hedef vurma servisi-------
    def weapons_hot_cb(self, msg):
        self.is_weapons_hot = msg.data


    #-- 

    def call_kill_service(self):
        if not self.kill_client.service_is_ready():
            return
     
        req = TargetKill.Request()
        req.target_id = "CURRENT_LOCK" 
        self.kill_client.call_async(req)
        self.get_logger().info("[VISION] Target destruction request sent.")
    # hedef vurma servisi-------/  




    def image_callback(self, msg):


        try:
            frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
            results = self.model(frame, verbose=False)
            
            enemy_detected = False
            best_bbox = None
            max_conf = 0.0




            #birden fazla tespit durumu-------

            # uçağın heading bilgisini fighter nodundan alırsam kamera pixel konumuna göre değerlendirem yapabilirim ilerde 
            # şuan en yüksek güven skoruna sahip uçağa kitlen

            for result in results:
                boxes = result.boxes
                for box in boxes:
                    conf = float(box.conf[0])
                    if conf > 0.25 and conf > max_conf: # en az %25 güven skoru gerek
                        max_conf = conf
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        best_bbox = (x1, y1, x2, y2)
                        enemy_detected = True
            #birden fazla tespit durumu-------/



            pub_data = Float32MultiArray()
            pub_data.data = [-1.0, -1.0, 0.0, 0.0, 0.0]

            COLOR_GREEN = (0, 255, 0)
            COLOR_YELLOW = (0, 255, 255)
            COLOR_RED = (0, 0, 255)



            #Tespit?-------------------------------------------
            if enemy_detected:
                x1, y1, x2, y2 = best_bbox
                width, height = x2 - x1, y2 - y1
                bbox_center_x, bbox_center_y = x1 + (width // 2), y1 + (height // 2)

                lock_status = 0.0 
                box_color = COLOR_GREEN



                # listener nodundan onay geldi mi--------------
                if self.is_weapons_hot:
                    self.lost_frames = 0
                    self.lock_frames += 1
                    lock_status = 1.0
                    box_color = COLOR_RED


                    
                    cv2.putText(frame, f"LOCK: {int((self.lock_frames/self.REQUIRED_FRAMES_FOR_KILL)*100)}%", (x1, y2+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_RED, 2)

                    if self.lock_frames >= self.REQUIRED_FRAMES_FOR_KILL:
                        lock_status = 2.0
                        self.lock_frames = 0
                        self.call_kill_service()
                else:
                    self.lost_frames += 1
                    if self.lost_frames > self.MAX_TOLERANCE_FRAMES:#timeout kontrolü
                        self.lock_frames = 0
                    box_color = COLOR_YELLOW
                    cv2.putText(frame, "STANDBY", (x1, y2+20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_YELLOW, 2)

                # listener nodundan onay geldi mi--------------/




                pub_data.data = [float(bbox_center_x), float(bbox_center_y), float(width), float(height), lock_status]

                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2) 
                cv2.circle(frame, (bbox_center_x, bbox_center_y), 5, box_color, -1)#merkez
                cv2.putText(frame, f"CONF: {max_conf*100:.0f}%", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

            else:
                self.lost_frames += 1
                if self.lost_frames > self.MAX_TOLERANCE_FRAMES:
                    self.lock_frames = 0

            #Tespit?-------------------------------------------





            wso_text = "WSO: HOT" if self.is_weapons_hot else "WSO: STANDBY"
            wso_color = COLOR_RED if self.is_weapons_hot else COLOR_YELLOW
            cv2.putText(frame, wso_text, (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, wso_color, 2)

            self.bbox_pub.publish(pub_data)
            cv2.imshow("HUD", frame)
            cv2.waitKey(1)



        except Exception as e:
            self.get_logger().error(f"[VISION] CV Error: {e}")








def main(args=None):
    rclpy.init(args=args)
    visionT = VisionTracker()
    try:
        rclpy.spin(visionT)
    except KeyboardInterrupt:
        pass
    finally:
        visionT.destroy_node()
        cv2.destroyAllWindows()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
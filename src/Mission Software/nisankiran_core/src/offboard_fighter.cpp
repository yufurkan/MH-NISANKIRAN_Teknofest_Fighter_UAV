#include <rclcpp/rclcpp.hpp>
#include <px4_msgs/msg/offboard_control_mode.hpp>
#include <px4_msgs/msg/trajectory_setpoint.hpp>
#include <px4_msgs/msg/vehicle_command.hpp>
#include <px4_msgs/msg/vehicle_status.hpp>
#include <px4_msgs/msg/vehicle_local_position.hpp>
#include <geometry_msgs/msg/pose.hpp>
#include <cmath>

#include <expected>
#include <algorithm> 

using namespace std::chrono_literals;

class OffboardFighter : public rclcpp::Node {


// GPS hesaplaması sadece listner nodunda yapılacak paylaşılan konumlar xyz şeklinde  
// Listenerden hedef seçliyo ve bilgiler buraya yayınlanıyor 


public:
    OffboardFighter() : Node("offboard_fighter_node") {
        auto qos = rclcpp::SensorDataQoS();
        std::string prefix = "/px4_1"; 

        offboard_pub_ = this->create_publisher<px4_msgs::msg::OffboardControlMode>(prefix + "/fmu/in/offboard_control_mode", 10);
        trajectory_pub_ = this->create_publisher<px4_msgs::msg::TrajectorySetpoint>(prefix + "/fmu/in/trajectory_setpoint", 10);
        command_pub_ = this->create_publisher<px4_msgs::msg::VehicleCommand>(prefix + "/fmu/in/vehicle_command", 10);

        // anasını sattımın uçağının topiğin sonunda _v1 olacak 
        
        // şu i 0 parametresiyle uçak başlatma gazeboda ortalık karışıyo
        //artık ana uçak i 1 ile başlıyo KESİN

        //ana uçağın STATUS bilgisi
        status_sub_ = this->create_subscription<px4_msgs::msg::VehicleStatus>(prefix + "/fmu/out/vehicle_status_v1", qos, [this](const px4_msgs::msg::VehicleStatus::SharedPtr msg) { this->status_cb(msg); });        
        //status_sub_ = this->create_subscription<px4_msgs::msg::VehicleStatus>(prefix + "/fmu/out/vehicle_status_v1", qos, std::bind(&OffboardFighter::status_cb, this, std::placeholders::_1));
            

        //ana uçağın geometrik konum bilgisi xyz
        pos_sub_ = this->create_subscription<px4_msgs::msg::VehicleLocalPosition>(prefix + "/fmu/out/vehicle_local_position_v1", qos, [this](const px4_msgs::msg::VehicleLocalPosition::SharedPtr msg) { this->position_cb(msg); });
        //pos_sub_ = this->create_subscription<px4_msgs::msg::VehicleLocalPosition>(prefix + "/fmu/out/vehicle_local_position_v1", qos, std::bind(&OffboardFighter::position_cb, this, std::placeholders::_1));


        // hedef uçağın konum bilgisi yayını xyz
        target_sub_ = this->create_subscription<geometry_msgs::msg::Pose>("/locked_target", 10, [this](const geometry_msgs::msg::Pose::SharedPtr msg) { this->target_cb(msg); });
        //target_sub_ = this->create_subscription<geometry_msgs::msg::Pose>("/locked_target", 10, std::bind(&OffboardFighter::target_cb, this, std::placeholders::_1));

        //kontrol döngüsü 20hz
        timer_ = this->create_wall_timer(50ms, std::bind(&OffboardFighter::control_loop, this));
        //arm olmama sorunu çözüldü sürekli kontrol

        RCLCPP_INFO(this->get_logger(), "Pilot node init.");
    }





// vision düğümünden kilitlenme başlarsa arada görüntü bazlı bir takip yaptırabilirim ilerde bunun için fighter modu ile vision track nodları arasında haberleşecek yeni bir modül lazım. Ayrıca vision track için bir pid düğümü yazılabilir?
// aslında yeni düğüm yerine burda mod değiştimek daha kolay 

private:

  
    static constexpr float PI = std::numbers::pi_v<float>;

    // derlemee uyarısı verdir
        [[nodiscard]] bool is_ready_for_takeoff() const {
        return (arming_state_ == 2 && nav_state_ == 14);
    }

    //hedef yoksa 
    std::expected<float, std::string> calculate_distance_to_target() const {
        if (!hedeftemi) {
            return std::unexpected("No ememy exist!");
        }
        float dist = std::sqrt(std::pow(hedef_x - my_x, 2) + std::pow(hedef_y - my_y, 2));
        return dist;
    }

    //publisers
    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::Publisher<px4_msgs::msg::OffboardControlMode>::SharedPtr offboard_pub_;
    rclcpp::Publisher<px4_msgs::msg::TrajectorySetpoint>::SharedPtr trajectory_pub_;
    rclcpp::Publisher<px4_msgs::msg::VehicleCommand>::SharedPtr command_pub_;
    

    //subscribers
    rclcpp::Subscription<px4_msgs::msg::VehicleStatus>::SharedPtr status_sub_;
    rclcpp::Subscription<px4_msgs::msg::VehicleLocalPosition>::SharedPtr pos_sub_;
    rclcpp::Subscription<geometry_msgs::msg::Pose>::SharedPtr target_sub_;


    // durum bilgileri
    uint8_t arming_state_ = 0;
    uint8_t nav_state_ = 0;
    
    // Konum verileri
    float my_x = 0.0, my_y = 0.0, my_alt = 0.0, my_heading = 0.0;

    // ilk yönelim bilgileri
    float bas_x = 0.0, bas_y = 0.0, bas_h = 0.0;
    

    //hedef bilgileri 
    float hedef_x = 0.0, hedef_y = 0.0, hedef_z = 0.0;
    bool hedeftemi = false;
    rclcpp::Time sonGorme;



    uint64_t control_sayac = 0;
    int flight_state_ = 0; 


    //status bilgilerini ata
    void status_cb(const px4_msgs::msg::VehicleStatus::SharedPtr msg) {
        arming_state_ = msg->arming_state;
        nav_state_ = msg->nav_state;
    }


    // ana uçağın konum bilgilerini ata
    void position_cb(const px4_msgs::msg::VehicleLocalPosition::SharedPtr msg) {

        my_x = msg->x;
        my_y = msg->y;
        my_alt = -msg->z; 
        my_heading = msg->heading;
    }


    // hedef uçağın bilgilerini ata
    void target_cb(const geometry_msgs::msg::Pose::SharedPtr msg) {

        hedef_x = msg->position.x;
        hedef_y = msg->position.y;
        hedef_z = msg->position.z;
        hedeftemi = true;
        sonGorme = this->get_clock()->now();

    }



    // KONTROL DÖNGÜSÜ----------------------------------------------
    void control_loop() {

        if (hedeftemi && (this->get_clock()->now() - sonGorme).seconds() > 2.0) {
            hedeftemi = false;
            

            std::string warn_msg = std::format("Radar timeout. Last Distance: {:.1f}m. Loitering.", calculate_distance_to_target().value_or(0.0f));

            RCLCPP_WARN(this->get_logger(), warn_msg.c_str());
        }

        //Param 1 =1 özel mod arm
        //Param 1 =0 disarm

        //Param2 = 1 manual
        //Param2 = 2 altctl
         //Param2 = 3 ppsctl
        //Param2 = 4 auto
        //Param2 = 6 offboard
         //Param2 = stabilized
        

        // YKİ den aktifleştirilecek bir RTL modu ekleyeceğim yki den yapılan yayınla görev bitirilebilecek satate machine ekle

        publish_offboard_control_mode();
        publish_trajectory_setpoint();

        if (control_sayac < 20) { control_sayac++; return; }

        if (control_sayac % 20 == 0) { 
            switch (flight_state_) {
                case 0: // Kontrolü al
                    if (nav_state_ != 14) { // nav_state 6 offboard mode 14 değil
                        publish_vehicle_command(px4_msgs::msg::VehicleCommand::VEHICLE_CMD_DO_SET_MODE, 1.0f, 6.0f);// param1=1 özel mod param2=6 offboard
                    } else {
                        RCLCPP_INFO(this->get_logger(), "Offboard active.");
                        flight_state_ = 1;
                    }
                    break;

                case 1: // Uçağı kaldır
                    if (arming_state_ != 2) { 
                        publish_vehicle_command(px4_msgs::msg::VehicleCommand::VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0f); //param1=1 param2=0
                    } else {
                        // Kalkış bilgilerini kaydet
                        bas_x = my_x;
                        bas_y = my_y;
                        bas_h = my_heading;
                        RCLCPP_INFO(this->get_logger(), "Armed. Takeoff initiated.");
                        flight_state_ = 2;
                    }
                    break;

                case 2:  // Fighter modunu başlat
                    if (my_alt > 30.0f) { 
                        RCLCPP_INFO(this->get_logger(), "Takeoff complete. Hunting mode active.");
                        flight_state_ = 3;
                    }
                    break;
                case 3: 
                     break;
            }
        }
        control_sayac++;
    }
    // KONTROL DÖNGÜSÜ----------------------------------------------\-




    void publish_offboard_control_mode() {
        px4_msgs::msg::OffboardControlMode msg{};
        msg.timestamp = this->get_clock()->now().nanoseconds() / 1000ULL;
        
        // pozisyon kontrolü 
        msg.position = true; 
        msg.velocity = false;   
        msg.acceleration = false;
        msg.attitude = false;
        msg.body_rate = false;
        offboard_pub_->publish(msg);

    }


    // Yer istasyonundan setpoint fonksiyonuna erişilebilir mi topicler ile?
    // YeR istasyonundan litener e komut atmak daha mantıklı listeden hedefi seçerim
    // Hedef ve mod belirleme
    void publish_trajectory_setpoint() {
        px4_msgs::msg::TrajectorySetpoint msg{};
        msg.timestamp = this->get_clock()->now().nanoseconds() / 1000ULL;

        if (flight_state_ < 3) {
            // Kalkış
            // yönelinen yönde 1000m ileri, 50m irtifa tırmanış
            msg.position[0] = bas_x + 1000.0f * std::cos(bas_h);//
            msg.position[1] = bas_y + 1000.0f * std::sin(bas_h);
            msg.position[2] = -50.0f; 
        } 
        else if (hedeftemi) {
            // Hedef takibi
            msg.position[0] = hedef_x;
            msg.position[1] = hedef_y;
            msg.position[2] = hedef_z; 
            
            // std::clamp  
            // hızı 15 e sınırla
            msg.velocity[0] = std::clamp(hedef_x - my_x, -15.0f, 15.0f);
            msg.velocity[1] = std::clamp(hedef_y - my_y, -15.0f, 15.0f);
        } 
        else {
            // Bekleme Geçerli yönde düz uçuş
            // Burada nav_state 4 yaparak daire çizme komutu ile değiştirebilirim
  
            msg.position[0] = bas_x + 1000.0f * std::cos(bas_h);
            msg.position[1] = bas_y + 1000.0f * std::sin(bas_h);
            msg.position[2] = -50.0f;  
        }


        // parametreleri px4 e bırak 
        if (!hedeftemi) {
            msg.velocity[0] = NAN; msg.velocity[1] = NAN; 
        }
        msg.velocity[2] = NAN;
        
        msg.acceleration[0] = NAN; msg.acceleration[1] = NAN; msg.acceleration[2] = NAN;
        msg.yaw = NAN; msg.yawspeed = NAN;
        
        trajectory_pub_->publish(msg);
    }




    //px4 e emir ver Şablon
    void publish_vehicle_command(uint16_t command, float param1 = 0.0, float param2 = 0.0) {
        px4_msgs::msg::VehicleCommand msg{};
        msg.param1 = param1;
        msg.param2 = param2;
        msg.command = command;
        
        msg.target_system = 2; 
        msg.target_component = 1;
        msg.source_system = 1;
        msg.source_component = 1;
        msg.from_external = true;
        msg.timestamp = this->get_clock()->now().nanoseconds() / 1000ULL;
        command_pub_->publish(msg);
    }
};

int main(int argc, char *argv[]) {
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<OffboardFighter>());
    rclcpp::shutdown();
    return 0;
}
#include "nisankiran_core/offboard_controller.hpp"
#include <px4_msgs/msg/vehicle_odometry.hpp> // Hız verisi için 

using namespace std::chrono_literals;

OffboardController::OffboardController() : Node("nisankiran_offboard_node") {
    auto qos = rclcpp::SensorDataQoS();

    // Publishers
    offboard_mode_pub_ = this->create_publisher<px4_msgs::msg::OffboardControlMode>("/fmu/in/offboard_control_mode", 10);
    trajectory_setpoint_pub_ = this->create_publisher<px4_msgs::msg::TrajectorySetpoint>("/fmu/in/trajectory_setpoint", 10);
    vehicle_command_pub_ = this->create_publisher<px4_msgs::msg::VehicleCommand>("/fmu/in/vehicle_command", 10);

    // Subscribers (Adreslere _v1 eklendi ve Odometry eklendi)
    vehicle_status_sub_ = this->create_subscription<px4_msgs::msg::VehicleStatus>("/fmu/out/vehicle_status_v1", qos, std::bind(&OffboardController::vehicle_status_callback, this, std::placeholders::_1));

    local_position_sub_ = this->create_subscription<px4_msgs::msg::VehicleLocalPosition>("/fmu/out/vehicle_local_position_v1", qos, std::bind(&OffboardController::local_position_callback, this, std::placeholders::_1));

    timer_ = this->create_wall_timer(50ms, std::bind(&OffboardController::timer_callback, this));
    
    RCLCPP_INFO(this->get_logger(), "Nişankıran Telemetri & Kontrol Sistemi Hazır.");
}

void OffboardController::vehicle_status_callback(const px4_msgs::msg::VehicleStatus::SharedPtr msg) {
    arming_state_ = msg->arming_state;
    nav_state_ = msg->nav_state;
}

void OffboardController::local_position_callback(const px4_msgs::msg::VehicleLocalPosition::SharedPtr msg) {
    altitude_ = -msg->z;
    // Terminale konum ve hız bilgisini saniyede bir basıyoruz
    RCLCPP_INFO_THROTTLE(this->get_logger(), *this->get_clock(), 1000,"CANLI VERİ -> Konum: [X:%.1f, Y:%.1f, Z:%.1f] | Hız: %.1f m/s", msg->x, msg->y, altitude_, sqrt(msg->vx*msg->vx + msg->vy*msg->vy));
}

void OffboardController::timer_callback() {
    publish_offboard_control_mode();
    publish_trajectory_setpoint();

    if (counter_ < 50) { counter_++; return; }

    if (counter_ % 20 == 0) {
        switch (flight_state_) {
            case 0: // OFFBOARD GECISI (Durum kodu 14 bekleniyor)
                if (nav_state_ != 14) {
                    publish_vehicle_command(px4_msgs::msg::VehicleCommand::VEHICLE_CMD_DO_SET_MODE, 1.0f, 6.0f);
                } else {
                    RCLCPP_INFO(this->get_logger(), "--> OFFBOARD AKTİF!");
                    flight_state_ = 1;
                }
                break;

            case 1: // ARM ET
                if (arming_state_ != 2) {
                    publish_vehicle_command(px4_msgs::msg::VehicleCommand::VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0f, 21196.0f);
                } else {
                    RCLCPP_INFO(this->get_logger(), "--> MOTORLAR ÇALIŞTI!");
                    flight_state_ = 2;
                }
                break;

            case 2: // UÇUŞ TAKİBİ
                if (altitude_ > 5.0f) RCLCPP_INFO_ONCE(this->get_logger(), "--> TEKER KESTİ! UÇUŞ BAŞLADI.");
                break;
        }
    }
    counter_++;
}

void OffboardController::publish_offboard_control_mode() {
    px4_msgs::msg::OffboardControlMode msg{};
    msg.timestamp = this->get_clock()->now().nanoseconds() / 1000;
    msg.position = true; // Konum kontrolü de yapalım ki uçup gitmesin
    msg.velocity = true;
    offboard_mode_pub_->publish(msg);
}

void OffboardController::publish_trajectory_setpoint() {
    px4_msgs::msg::TrajectorySetpoint msg{};
    msg.timestamp = this->get_clock()->now().nanoseconds() / 1000;
    // Uçağın sürekli dümdüz gitmemesi için dairesel bir yörünge setpointi verilebilir 
    // ama şimdilik güvenli kalkış için 100m ileri ve 30m yukarısını hedefliyoruz
    msg.position[0] = 100.0f; 
    msg.position[2] = -30.0f; 
    msg.velocity[0] = 16.0f; // Cessna için ideal seyir hızı
    trajectory_setpoint_pub_->publish(msg);
}

void OffboardController::publish_vehicle_command(uint16_t command, float param1, float param2, float param7) {
    px4_msgs::msg::VehicleCommand msg{};
    msg.timestamp = this->get_clock()->now().nanoseconds() / 1000;
    msg.command = command;
    msg.param1 = param1; msg.param2 = param2; msg.param7 = param7;
    msg.target_system = 1; msg.target_component = 1;
    msg.source_system = 1; msg.source_component = 1;
    msg.from_external = true;
    vehicle_command_pub_->publish(msg);
}
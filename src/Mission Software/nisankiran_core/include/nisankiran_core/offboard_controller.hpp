#ifndef OFFBOARD_CONTROLLER_HPP_
#define OFFBOARD_CONTROLLER_HPP_

#include <rclcpp/rclcpp.hpp>
#include <px4_msgs/msg/offboard_control_mode.hpp>
#include <px4_msgs/msg/trajectory_setpoint.hpp>
#include <px4_msgs/msg/vehicle_command.hpp>
#include <px4_msgs/msg/vehicle_status.hpp>
#include <px4_msgs/msg/vehicle_local_position.hpp>
#include <cmath>

class OffboardController : public rclcpp::Node {
public:
    OffboardController();

private:
    void timer_callback();
    void vehicle_status_callback(const px4_msgs::msg::VehicleStatus::SharedPtr msg);
    void local_position_callback(const px4_msgs::msg::VehicleLocalPosition::SharedPtr msg);
    
    void publish_offboard_control_mode();
    void publish_trajectory_setpoint();
    void publish_vehicle_command(uint16_t command, float param1 = NAN, float param2 = NAN, float param7 = NAN);

    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::Publisher<px4_msgs::msg::OffboardControlMode>::SharedPtr offboard_mode_pub_;
    rclcpp::Publisher<px4_msgs::msg::TrajectorySetpoint>::SharedPtr trajectory_setpoint_pub_;
    rclcpp::Publisher<px4_msgs::msg::VehicleCommand>::SharedPtr vehicle_command_pub_;
    
    rclcpp::Subscription<px4_msgs::msg::VehicleStatus>::SharedPtr vehicle_status_sub_;
    rclcpp::Subscription<px4_msgs::msg::VehicleLocalPosition>::SharedPtr local_position_sub_;

    uint8_t nav_state_{0};
    uint8_t arming_state_{0};
    uint64_t counter_{0};
    int flight_state_{0}; 
    float altitude_{0.0f};
};

#endif
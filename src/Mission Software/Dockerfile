FROM ros:jazzy-ros-base
WORKDIR /nisankiran_ws
COPY ./src ./src
RUN apt-get update && apt-get install -y python3-pip \
    && rosdep install --from-paths src --ignore-src -r -y \
    && pip3 install flask --break-system-packages
RUN /bin/bash -c "source /opt/ros/jazzy/setup.bash && colcon build"
CMD ["/bin/bash", "-c", "source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch nisankiran_telemetry nisankiran_bringup.launch.py"]
ARG BASE_IMAGE=base:latest
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ARG ROS_DISTRO=humble

RUN apt update && apt install -y --no-install-recommends \
    build-essential cmake pkg-config \
    python3-opencv libopencv-dev \
    ros-${ROS_DISTRO}-camera-info-manager \
    ros-${ROS_DISTRO}-camera-calibration-parsers \
    ros-${ROS_DISTRO}-image-transport \
    ros-${ROS_DISTRO}-image-common \
    libopencv-dev libopenni2-0 libopenni2-dev \
    ros-${ROS_DISTRO}-vision-opencv \
    && rm -rf /var/lib/apt/lists/*

# RUN pip install --upgrade pip && pip install catkin_pkg empy lark pandas matplotlib numpy
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install \
        empy==3.3.4 \
        catkin_pkg lark pandas \
        matplotlib numpy pyyaml

# openni2_camera
ENV PATH=/usr/bin:$PATH
RUN cd /ros2_ws/src \
    && git clone -b iron https://github.com/ros-drivers/openni2_camera.git \
    && cd /ros2_ws \
    && /bin/bash -lc "source /opt/ros/${ROS_DISTRO}/setup.bash && colcon build" \
    && source install/setup.bash
RUN echo 'source /ros2_ws/install/setup.bash' >> /root/.bashrc

COPY docker/entrypoints/sensor-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
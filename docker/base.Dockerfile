FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG DEBIAN_FRONTEND=noninteractive
ARG ROS_DISTRO=humble
ENV TZ=Asia/Tokyo \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# 必須ツール & GUI/画像系ランタイム
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ >/etc/timezone && \
    apt-get update && apt-get install -y --no-install-recommends \
      tzdata locales ca-certificates curl gnupg lsb-release \
      git wget usbutils vim byobu net-tools \
      ffmpeg libgl1 libglib2.0-0 libgtk-3-0 libsm6 libxrender1 libxext6 x11-apps \
      python3-opencv && \
    rm -rf /var/lib/apt/lists/*

# ROS 2 Humble
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  > /etc/apt/sources.list.d/ros2.list && \
  curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
    -o /usr/share/keyrings/ros-archive-keyring.gpg && \
  apt update && apt install -y --no-install-recommends \
    ros-${ROS_DISTRO}-desktop \
    python3-colcon-common-extensions \
    python3-rosdep && \
  rosdep init || true && rosdep update && \
  rm -rf /var/lib/apt/lists/*

# RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc && source .bashrc

# Gazebo, rqt
RUN apt update && apt install -y --no-install-recommends \
  gazebo ros-${ROS_DISTRO}-gazebo-* ros-${ROS_DISTRO}-rqt-*

# 共通ワークスペース
WORKDIR /ros2_ws
RUN mkdir -p /ros2_ws/src
ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp

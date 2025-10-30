FROM pytorch/pytorch:2.5.1-cuda12.1-cudnn9-runtime

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG DEBIAN_FRONTEND=noninteractive
ARG ROS_DISTRO=humble
ENV TZ=Asia/Tokyo \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

# 1) Python 3.10 を導入して実行系を 3.10 に固定
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3.10 python3.10-venv python3.10-distutils python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN /usr/bin/python3.10 -m ensurepip --upgrade || true && \
    /usr/bin/python3.10 -m pip install -U pip

# 既定の python/pip を 3.10 に向ける
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/local/bin/pip 1 || true

# PyTorch(2.5.1/cu121) を cp310 で入れ直す
RUN /usr/bin/python3.10 -m pip install --index-url https://download.pytorch.org/whl/cu121 \
      torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1

RUN /usr/bin/python3.10 -m pip install \
      opencv-python "transformers>=4.44" accelerate

# 必須ツール & GUI/画像系ランタイム
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ >/etc/timezone && \
    apt-get update && apt-get install -y --no-install-recommends \
      tzdata locales ca-certificates curl gnupg lsb-release \
      git wget usbutils vim byobu net-tools \
      ffmpeg libgl1 libglib2.0-0 libgtk-3-0 libsm6 libxrender1 libxext6 x11-apps \
      && rm -rf /var/lib/apt/lists/*

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

# Gazebo, rqt
RUN apt update && apt install -y --no-install-recommends \
  gazebo ros-${ROS_DISTRO}-gazebo-* ros-${ROS_DISTRO}-rqt-*

# 共通ワークスペース
WORKDIR /ros2_ws
RUN mkdir -p /ros2_ws/src
ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp

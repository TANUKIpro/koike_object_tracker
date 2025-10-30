ARG BASE_IMAGE=base-py310:latest
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO=humble
ENV HF_HUB_ENABLE_HF_TRANSFER=1 \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:128

# SAM2/Transformers
RUN git clone https://github.com/facebookresearch/sam2.git /opt/sam2 && \
    /usr/bin/python3.10 -m pip install -U pip "transformers>=4.44" accelerate opencv-python && \
    /usr/bin/python3.10 -m pip install -e /opt/sam2 && \
    /usr/bin/python3.10 -m pip install hf_transfer && \
    /usr/bin/python3.10 -m pip install -U 'numpy<2'

WORKDIR /ros2_ws
RUN source /opt/ros/${ROS_DISTRO}/setup.bash && \
    apt-get update && rosdep update && \
    rosdep install --rosdistro ${ROS_DISTRO} --from-paths src --ignore-src -y || true && \
    colcon build --symlink-install || true

WORKDIR /workspace

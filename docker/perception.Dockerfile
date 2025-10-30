ARG BASE_IMAGE=base-py310:latest
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
ARG ROS_DISTRO=humble
ENV HF_HUB_ENABLE_HF_TRANSFER=1 \
    PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True,max_split_size_mb:128

# 1) 3.10 venv 作成・有効化
RUN /usr/bin/python3.10 -m venv /opt/py310
ENV VIRTUAL_ENV=/opt/py310
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONNOUSERSITE=1

# 2) pip初期化 & 必須依存（cv_bridge安定のためnumpyは1.26.4固定）
RUN /usr/bin/python3.10 -m pip install -U pip wheel setuptools \
    && /usr/bin/python3.10 -m pip install "numpy==1.26.4" ultralytics onnxruntime-gpu matplotlib

# SAM2/Transformers
RUN git clone https://github.com/facebookresearch/sam2.git /opt/sam2 \
    && /usr/bin/python3.10 -m pip install -e /opt/sam2 \
    && /usr/bin/python3.10 -m pip install "transformers>=4.44" accelerate opencv-python hf_transfer

WORKDIR /ros2_ws
RUN /bin/bash -lc "source /opt/ros/${ROS_DISTRO}/setup.bash && \
    /usr/bin/python3.10 -m pip install -U colcon-common-extensions && \
    colcon build --symlink-install || true"

WORKDIR /workspace

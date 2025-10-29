#!/usr/bin/env bash
set -euo pipefail

# ROS を有効化
source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash" || true
# ワークスペースを有効化
[ -f /root/ros2_ws/install/setup.bash ] && source /root/ros2_ws/install/setup.bash
[ -f /root/robovision_ros2_ws/install/setup.bash ] && source /root/robovision_ros2_ws/install/setup.bash

# python -m robovision_ros2.migrate || true

exec "$@"

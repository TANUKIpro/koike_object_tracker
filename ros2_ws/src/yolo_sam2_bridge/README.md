# yolo_sam2_bridge

A ROS2 (Humble) Python package that:
- Subscribes to `/camera/rgb/image_raw` (Xtion)
- Runs YOLOv11 (default: `yolo11s.pt`) to get bounding boxes
- Refines each box with SAM2 to get pixel-accurate masks
- Publishes JSON detections and a debug overlay image

## Topics
- Sub: `/camera/rgb/image_raw` (`sensor_msgs/Image`)
- Pub: `/perception/detections` (`std_msgs/String`) JSON payload
- Pub: `/perception/overlay/image` (`sensor_msgs/Image`) with boxes & masks drawn

## Parameters
Defined in `params.yaml` and can be set via launch:
- `image_topic`: default `/camera/rgb/image_raw`
- `yolo_weights`: default `yolo11s.pt` (override with absolute path if needed)
- `yolo_conf`: default 0.4
- `yolo_iou`: default 0.5
- `max_dets`: default 10
- `device`: default `cuda:0`
- `sam2_enabled`: bool, default true
- `sam2_model_cfg`: path to SAM2 model config (e.g. `/opt/sam2/configs/sam2_hiera_t.yaml`)
- `sam2_checkpoint`: path to SAM2 checkpoint (e.g. `/opt/sam2/checkpoints/sam2_hiera_tiny.pt`)

## Run
```
source /opt/ros/$ROS_DISTRO/setup.bash
source /ros2_ws/install/setup.bash

ros2 launch yolo_sam2_bridge yolo_sam2.launch.py
```

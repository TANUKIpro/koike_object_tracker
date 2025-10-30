import os
import json
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge

from .yolo_wrapper import YOLOv11Detector
from .visualization import draw_overlay

def try_import_sam2(model_cfg, checkpoint, device='cuda'):
    try:
        from .sam2_wrapper import SAM2BoxSegmentor
        seg = SAM2BoxSegmentor(model_cfg=model_cfg, checkpoint=checkpoint, device=device)
        return seg, None
    except Exception as e:
        return None, str(e)

class YoloSam2Node(Node):
    def __init__(self):
        super().__init__('yolo_sam2_node')

        self.declare_parameter('image_topic', '/camera/rgb/image_raw')
        self.declare_parameter('yolo_weights', 'yolo11s.pt')
        self.declare_parameter('yolo_conf', 0.4)
        self.declare_parameter('yolo_iou', 0.5)
        self.declare_parameter('max_dets', 10)
        self.declare_parameter('device', 'cuda:0')
        self.declare_parameter('sam2_enabled', True)
        self.declare_parameter('sam2_model_cfg', '/opt/sam2/configs/sam2_hiera_t.yaml')
        self.declare_parameter('sam2_checkpoint', '/opt/sam2/checkpoints/sam2_hiera_tiny.pt')
        self.declare_parameter('publish_overlay', True)
        self.declare_parameter('overlay_topic', '/perception/overlay/image')
        self.declare_parameter('detections_topic', '/perception/detections')

        image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        yolo_weights = self.get_parameter('yolo_weights').get_parameter_value().string_value
        yolo_conf = float(self.get_parameter('yolo_conf').get_parameter_value().double_value)
        yolo_iou = float(self.get_parameter('yolo_iou').get_parameter_value().double_value)
        max_dets = int(self.get_parameter('max_dets').get_parameter_value().integer_value)
        device = self.get_parameter('device').get_parameter_value().string_value
        sam2_enabled = self.get_parameter('sam2_enabled').get_parameter_value().bool_value
        sam2_model_cfg = self.get_parameter('sam2_model_cfg').get_parameter_value().string_value
        sam2_checkpoint = self.get_parameter('sam2_checkpoint').get_parameter_value().string_value
        publish_overlay = self.get_parameter('publish_overlay').get_parameter_value().bool_value
        overlay_topic = self.get_parameter('overlay_topic').get_parameter_value().string_value
        detections_topic = self.get_parameter('detections_topic').get_parameter_value().string_value

        self.bridge = CvBridge()

        self.get_logger().info(f"Loading YOLOv11 weights: {yolo_weights}")
        self.detector = YOLOv11Detector(weights=yolo_weights, conf=yolo_conf, iou=yolo_iou, device=device, max_dets=max_dets)

        self.segmentor = None
        self.sam2_error = None
        if sam2_enabled:
            # device like 'cuda:0' -> 'cuda'
            dev_sam = device.split(':')[0] if ':' in device else device
            self.segmentor, self.sam2_error = try_import_sam2(sam2_model_cfg, sam2_checkpoint, device=dev_sam)
        if self.segmentor is None and sam2_enabled:
            self.get_logger().warn(f"SAM2 disabled (init failed): {self.sam2_error}")

        qos = QoSProfile(depth=10)
        qos.reliability = ReliabilityPolicy.BEST_EFFORT
        qos.history = HistoryPolicy.KEEP_LAST

        self.sub = self.create_subscription(Image, image_topic, self.on_image, qos)
        self.pub_json = self.create_publisher(String, detections_topic, 10)
        self.pub_overlay = self.create_publisher(Image, overlay_topic, 10) if publish_overlay else None

        self.get_logger().info("yolo_sam2_node ready.")

    def on_image(self, msg: Image):
        t0 = time.time()
        img_bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

        dets = self.detector.infer(img_bgr)

        refined = []
        for d in dets:
            box = d['bbox']
            item = dict(d)
            if self.segmentor is not None:
                try:
                    mask, score = self.segmentor.segment_with_box(img_bgr, box)
                except Exception as e:
                    self.get_logger().warn(f"SAM2 segment error: {e}")
                    mask, score = None, 0.0
                item['mask_score'] = float(score)
                item['mask'] = mask
            refined.append(item)

        serializable = {
            'stamp': {'sec': msg.header.stamp.sec, 'nanosec': msg.header.stamp.nanosec},
            'height': int(img_bgr.shape[0]),
            'width': int(img_bgr.shape[1]),
            'objects': [
                {
                    'cls_name': d['cls_name'],
                    'cls_id': int(d['cls_id']),
                    'conf': float(d['conf']),
                    'bbox': [float(x) for x in d['bbox']],
                    'mask_score': float(d.get('mask_score', 0.0)),
                } for d in refined
            ],
            'latency_ms': (time.time() - t0) * 1000.0
        }
        self.pub_json.publish(String(data=json.dumps(serializable)))

        if self.pub_overlay is not None:
            dets_for_overlay = []
            for d in refined:
                e = dict(d)
                e['mask'] = d.get('mask', None)
                dets_for_overlay.append(e)
            overlay = draw_overlay(img_bgr, dets_for_overlay)
            out_msg = self.bridge.cv2_to_imgmsg(overlay, encoding='bgr8')
            out_msg.header = msg.header
            self.pub_overlay.publish(out_msg)

def main():
    rclpy.init()
    node = YoloSam2Node()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

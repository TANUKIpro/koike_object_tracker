#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAM2 streaming tracker for ROS2 image topic.
- Subscribe /camera/rgb/image_raw
- Click once to initialize the object (positive point)
- Overlay mask in real-time with low VRAM usage
"""

import os
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True,max_split_size_mb:128")

import argparse
import signal
import sys
import time
import threading
import cv2
import numpy as np

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import torch
from transformers import Sam2VideoModel, Sam2VideoProcessor, infer_device

# --------------------- Utilities ---------------------

def downscale_max_side(img_rgb: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img_rgb.shape[:2]
    if max(h, w) <= max_side:
        return img_rgb
    scale = max_side / float(max(h, w))
    nh, nw = int(round(h * scale)), int(round(w * scale))
    return cv2.resize(img_rgb, (nw, nh), interpolation=cv2.INTER_AREA)

def overlay_mask(bgr: np.ndarray, mask: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    """mask: uint8 {0,255} with shape (H,W); bgr is (H,W,3)"""
    color = np.array([0, 255, 0], dtype=np.uint8)
    overlay = bgr.copy()
    m = (mask > 0)
    overlay[m, :] = color
    return cv2.addWeighted(overlay, alpha, bgr, 1 - alpha, 0)

# --------------------- Node ---------------------

class Sam2TraceNode(Node):
    def __init__(self, topic, model_id, max_side, window, encoding, throttle_n):
        super().__init__("sam2_trace_node")
        self.topic = topic
        self.window = window
        self.encoding = encoding
        self.max_side = max_side
        self.throttle_n = max(1, throttle_n)

        self.bridge = CvBridge()
        self.sub = self.create_subscription(Image, self.topic, self.cb, qos_profile_sensor_data)

        # GUI state
        self.clicked_xy = None
        self.click_lock = threading.Lock()
        cv2.namedWindow(self.window, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.window, self.on_mouse)

        # Device / model
        self.device = infer_device()
        self.dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        self.get_logger().info(f"Device={self.device}, dtype={self.dtype}, model={model_id}")

        self.processor = Sam2VideoProcessor.from_pretrained(model_id)
        self.model = Sam2VideoModel.from_pretrained(model_id).to(self.device, dtype=self.dtype).eval()

        # SAM2 streaming session (created after first frame arrives)
        self.session = None
        self.inited = False          # whether prompt added
        self.frame_count = 0         # throttle

        # graceful exit
        signal.signal(signal.SIGINT, self._sigint)

        self.last_vis = None
        self.last_time = time.time()

    # Mouse: left click sets positive point; press 'r' to reset during display
    def on_mouse(self, event, x, y, flags, userdata=None):
        if event == cv2.EVENT_LBUTTONDOWN:
            with self.click_lock:
                self.clicked_xy = (x, y)
                self.inited = False  # will (re-)initialize on next callback

    def _sigint(self, *_):
        rclpy.shutdown()

    def _maybe_reset(self, key):
        if key in (ord('r'), ord('R')):
            with self.click_lock:
                self.clicked_xy = None
                self.inited = False
                self.session = None
                self.get_logger().info("Reset tracker.")

    def cb(self, msg: Image):
        # Convert ROS -> cv2 BGR -> RGB
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding=self.encoding)  # usually 'bgr8'
        except Exception as e:
            self.get_logger().error(f"cv_bridge error: {e}")
            return

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        rgb = downscale_max_side(rgb, self.max_side)

        # Throttle if requested
        self.frame_count += 1
        if self.frame_count % self.throttle_n != 0:
            self._show(rgb, bgr_hint=True)
            return

        # Prepare inputs per-frame (streaming; do NOT store history)
        with torch.inference_mode(), torch.autocast(
            device_type="cuda", dtype=torch.float16, enabled=torch.cuda.is_available()
        ):
            inputs = self.processor(images=rgb, device=self.device, return_tensors="pt")

            # Initialize session (once or after reset)
            if self.session is None:
                self.session = self.processor.init_video_session(
                    inference_device=self.device,
                    dtype=self.dtype
                )

            # If user clicked -> add prompt at this frame (frame_idx=0 for streaming)
            if not self.inited:
                with self.click_lock:
                    cxcy = self.clicked_xy
                if cxcy is not None:
                    # NOTE: coordinates are in current (resized) frame space
                    self.processor.add_inputs_to_inference_session(
                        inference_session=self.session,
                        frame_idx=0,
                        obj_ids=1,
                        input_points=[[[[cxcy[0], cxcy[1]]]]],
                        input_labels=[[[1]]],
                        original_size=inputs.original_sizes[0],  # crucial for streaming
                    )
                    self.inited = True
                    self.get_logger().info(f"Initialized at {cxcy}")
                else:
                    # show hint and return
                    self._show(rgb, text="Click a target to start tracking")
                    return

            # One-step streaming inference
            out = self.model(inference_session=self.session, frame=inputs.pixel_values[0])
            masks_pp = self.processor.post_process_masks(
                [out.pred_masks], original_sizes=inputs.original_sizes, binarize=True
            )[0]

        # 形状ゆらぎに対応（[N,1,H,W] or [1,H,W]）
        if masks_pp.ndim == 4:
            m_t = masks_pp[0, 0]          # [1,1,H,W] → (H,W)
        elif masks_pp.ndim == 3:
            m_t = masks_pp[0]             # [1,H,W] → (H,W)
        else:
            m_t = masks_pp
        m = (m_t.detach().cpu().numpy() * 255).astype("uint8")
        vis = overlay_mask(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), m, alpha=0.5)
        self._show(vis)

    def _show(self, bgr_img, text=None, bgr_hint=False):
        if text:
            cv2.putText(bgr_img, text, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2, cv2.LINE_AA)
        cv2.imshow(self.window, bgr_img)
        key = cv2.waitKey(1) & 0xFF
        self._maybe_reset(key)
        if key == 27:  # ESC
            rclpy.shutdown()

# --------------------- main ---------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", default="/camera/rgb/image_raw")
    ap.add_argument("--model", default="facebook/sam2.1-hiera-tiny")
    ap.add_argument("--max-side", type=int, default=640, help="resize so that max(H,W)=max-side")
    ap.add_argument("--encoding", default="bgr8", help="bgr8/rgb8/mono8 etc.")
    ap.add_argument("--window", default="SAM2 Trace")
    ap.add_argument("--throttle-n", type=int, default=1, help="process every N frames to cut load")
    args = ap.parse_args()

    rclpy.init()
    node = Sam2TraceNode(
        topic=args.topic,
        model_id=args.model,
        max_side=args.max_side,
        window=args.window,
        encoding=args.encoding,
        throttle_n=args.throttle_n,
    )
    try:
        rclpy.spin(node)
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()

if __name__ == "__main__":
    main()

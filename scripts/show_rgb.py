import argparse
import signal
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

class ImageViewer(Node):
    def __init__(self, topic, encoding='bgr8', window='RGB'):
        super().__init__('image_viewer')
        self.topic = topic
        self.encoding = encoding
        self.bridge = CvBridge()
        self.window = window
        cv2.namedWindow(self.window, cv2.WINDOW_NORMAL)
        self.sub = self.create_subscription(
            Image, self.topic, self.cb, qos_profile_sensor_data
        )
        self.get_logger().info(f"Subscribed: {self.topic}")

    def cb(self, msg: Image):
        try:
            # 通常は bgr8 / rgb8 / mono8 など。必要に応じて --encoding 変更
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding=self.encoding)
        except Exception as e:
            self.get_logger().error(f"cv_bridge error: {e}")
            return
        cv2.imshow(self.window, frame)
        # GUIを回すために waitKey(1)
        if cv2.waitKey(1) == 27:  # ESC で終了
            rclpy.shutdown()

    def close(self):
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', default='/camera/rgb/image_raw')
    parser.add_argument('--encoding', default='bgr8', help='bgr8/rgb8/mono8 など')
    parser.add_argument('--window', default='RGB')
    args = parser.parse_args()

    rclpy.init()
    node = ImageViewer(args.topic, args.encoding, args.window)

    # Ctrl+C を丁寧に処理
    def _sigint(_sig, _frm):
        rclpy.shutdown()
    signal.signal(signal.SIGINT, _sigint)

    try:
        rclpy.spin(node)
    finally:
        node.close()
        node.destroy_node()

if __name__ == '__main__':
    main()

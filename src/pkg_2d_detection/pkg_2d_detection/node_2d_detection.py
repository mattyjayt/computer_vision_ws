import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge

class DetectionNode(Node):
    def __init__(self):
        super().__init__('detection_node_2d')
        self.get_logger().info('2D Detection Node has been started.')

        self.declare_parameter('model_path', 'models/yolo26n.pt')
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('detection_topic', '/detections')
        self.declare_parameter('annotated_image_topic', '/annotated_image')

        self.model_path = self.get_parameter('model_path').get_parameter_value().string_value
        self.image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        self.detection_topic = self.get_parameter('detection_topic').get_parameter_value().string_value
        self.annotated_image_topic = self.get_parameter('annotated_image_topic').get_parameter_value().string_value

        package_share_directory = get_package_share_directory('pkg_2d_detection')
        model_full_path = f"{package_share_directory}/{self.model_path}"

        self.get_logger().info(f'Using model: {self.model_path}')
        self.get_logger().info(f'Subscribing to image topic: {self.image_topic}')
        self.get_logger().info(f'Publishing detections to topic: {self.detection_topic}')
        self.get_logger().info(f'Publishing annotated images to topic: {self.annotated_image_topic}')

def main(args=None):
    rclpy.init(args=args)
    try:
        node = DetectionNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
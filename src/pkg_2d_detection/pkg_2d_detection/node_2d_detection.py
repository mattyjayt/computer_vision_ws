import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from vision_msgs.msg import Detection2DArray, Detection2D, ObjectHypothesisWithPose
from ament_index_python.packages import get_package_share_directory
from cv_bridge import CvBridge

from ultralytics import YOLO
import supervision as sv

class DetectionNode(Node):
    def __init__(self):
        super().__init__('detection_node_2d')
        self.get_logger().info('2D Detection Node has been started.')

        self.declare_parameter('model_path', 'models/yolo26n.pt')
        self.declare_parameter('image_topic', '/image_raw')
        self.declare_parameter('detection_topic', '/detections')
        self.declare_parameter('annotated_image_topic', '/annotated_image')

        self.model_path = self.get_parameter('model_path').get_parameter_value().string_value
        self.image_topic = self.get_parameter('image_topic').get_parameter_value().string_value
        self.detection_topic = self.get_parameter('detection_topic').get_parameter_value().string_value
        self.annotated_image_topic = self.get_parameter('annotated_image_topic').get_parameter_value().string_value

        self.bbox_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()

        self.bridge = CvBridge()

        package_share_directory = get_package_share_directory('pkg_2d_detection')
        model_full_path = f"{package_share_directory}/{self.model_path}"

        self.model = YOLO(model_full_path)

        self.image_subscriber = self.create_subscription(Image, self.image_topic, self.image_callback, 10)
        self.detection_publisher = self.create_publisher(Detection2DArray, self.detection_topic, 10)
        self.annotated_image_publisher = self.create_publisher(CompressedImage, self.annotated_image_topic, 10)

        self.get_logger().info(f'Using model: {self.model_path}')
        self.get_logger().info(f'Subscribing to image topic: {self.image_topic}')
        self.get_logger().info(f'Publishing detections to topic: {self.detection_topic}')
        self.get_logger().info(f'Publishing annotated images to topic: {self.annotated_image_topic}')

    def get_labels(self, results):
        labels = []
        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0].cpu().numpy())
                confidence = float(box.conf[0].cpu().numpy())
                class_name = self.model.names[class_id]
                labels.append(f"{class_name} {confidence:.2f}")
        return labels

    def image_callback(self, msg):
        try:
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        except Exception as e:
            self.get_logger().error(f'Error converting ROS Image to OpenCV: {e}')
            return

        results = self.model(cv_image, verbose=False)
        detections = sv.Detections.from_ultralytics(results[0])

        # if len(detections) == 0:
        #     pass

        detection_array_msg = Detection2DArray()
        detection_array_msg.header = msg.header

        for detection in detections:
            detection_msg = Detection2D()
            detection_msg.header = msg.header

            x1, y1, x2, y2 = detections.xyxy[0]
            detection_msg.bbox.center.position.x = float(x1 + (x2 - x1) / 2)
            detection_msg.bbox.center.position.y = float(y1 + (y2 - y1) / 2)
            detection_msg.bbox.size_x = float(x2 - x1)
            detection_msg.bbox.size_y = float(y2 - y1)

            labels = self.get_labels(results)

            cv_image_annotated = self.bbox_annotator.annotate(scene=cv_image.copy(), detections=detections)
            cv_image_annotated = self.label_annotator.annotate(scene=cv_image_annotated, detections=detections, labels=labels)

            hypothesis = ObjectHypothesisWithPose()
            hypothesis.hypothesis.class_id = str(detections.class_id[0])
            hypothesis.hypothesis.score = float(detections.confidence[0])
            detection_msg.results.append(hypothesis)
            detection_array_msg.detections.append(detection_msg)

        annotated_image_msg = self.bridge.cv2_to_compressed_imgmsg(cv_image_annotated, dst_format='jpeg')
        annotated_image_msg.header = msg.header

        self.detection_publisher.publish(detection_array_msg)
        self.annotated_image_publisher.publish(annotated_image_msg)

        self.get_logger().info(f'Published {len(detections)} detections and annotated image.')

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
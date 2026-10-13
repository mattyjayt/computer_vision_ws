import rclpy
from rclpy.node import Node

class DetectionNode(Node):
    def __init__(self):
        super().__init__('detection_node_2d')
        self.get_logger().info('2D Detection Node has been started.')

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
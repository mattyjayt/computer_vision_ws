from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    image_topic_arg = DeclareLaunchArgument(
        'image_topic',
        default_value='/image_raw',
        description='Topic name for the input image'
    )

    detection_topic_arg = DeclareLaunchArgument(
        'detection_topic',
        default_value='/detections',
        description='Topic name for the output detections'
    )

    annotated_image_topic_arg = DeclareLaunchArgument(
        'annotated_image_topic',
        default_value='/annotated_image',
        description='Topic name for the annotated image'
    )

    model_path_arg = DeclareLaunchArgument(
        'model_path',
        default_value='models/yolo26n.pt',
        description='Path to the YOLO model file'
    )

    camera_node = Node(
        package='usb_cam',
        executable='usb_cam_node_exe',
        name='cam_node',
        parameters=[
            {'video_device': '/dev/video0'},
            {'image_width': 640},
            {'image_height': 480},
            {'pixel_format': 'yuyv2rgb'},
        ],
        output='screen'
    )

    detection_node_2d = Node(
        package='pkg_2d_detection',
        executable='node_2d_detection',
        name='detection_node_2d',
        parameters=[
            {'model_path': LaunchConfiguration('model_path')},
            {'image_topic': LaunchConfiguration('image_topic')},
            {'detection_topic': LaunchConfiguration('detection_topic')},
            {'annotated_image_topic': LaunchConfiguration('annotated_image_topic')}
        ],
        output='screen'
    )

    return LaunchDescription([
        image_topic_arg,
        detection_topic_arg,
        annotated_image_topic_arg,
        model_path_arg,
        camera_node,
        detection_node_2d
    ])
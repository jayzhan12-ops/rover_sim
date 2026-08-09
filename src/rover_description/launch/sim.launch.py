import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = 'rover_description'
    pkg_share = get_package_share_directory(pkg)

    world_file = os.path.join(pkg_share, 'worlds', 'rover_world.sdf')
    rviz_config = os.path.join(pkg_share, 'rviz', 'rover.rviz')

    urdf = PathJoinSubstitution([
        FindPackageShare(pkg), 'urdf', 'rover.urdf.xacro'
    ])
    robot_description = ParameterValue(
        Command(['xacro ', urdf]), value_type=str
    )

    # Start Gazebo Harmonic with our world
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch', 'gz_sim.launch.py'
            )
        ),
        launch_arguments={'gz_args': f'-r -s -v 3 {world_file}'}.items(),
    )

    # Publishes the URDF and base_link -> sensor transforms
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
    )

    # Spawn the robot into Gazebo from the /robot_description topic
    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'rover',
            '-x', '0', '-y', '0', '-z', '0.1',
        ],
        output='screen',
    )

    # Translate between Gazebo transport and ROS 2 topics.
    #   @  = bidirectional
    #   [  = Gazebo -> ROS only
    #   ]  = ROS -> Gazebo only
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
        ],
        parameters=[{'use_sim_time': True}],
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([
        gz_sim,
        robot_state_publisher,
        spawn,
        bridge,
        rviz,
    ])
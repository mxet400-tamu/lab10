import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from ur_msgs.srv import SetIO, SetAnalogOutput
from ur_msgs.msg import Analog
import time

class UR3eActionController(Node):
    def __init__(self):
        super().__init__('ur_action_controller')

        # 1. Robot Configuration
        self.declare_parameter('robot_id', 1) 
        self.robot_id = self.get_parameter('robot_id').value

        # 2. Action Client for Movement
        self._action_client = ActionClient(
            self, 
            FollowJointTrajectory, 
            '/scaled_joint_trajectory_controller/follow_joint_trajectory'
        )

        # 3. Service Clients for IO (Gripper and Conveyor)
        self.io_client = self.create_client(SetIO, '/io_and_status_controller/set_io')
        self.analog_client = self.create_client(SetAnalogOutput, '/io_and_status_controller/set_analog_output')

        # 4. Waypoints
        self.waypoint_names = [
            "home", "above_pallet", "approach_cube", "pick_up_pos",
            "raise_cube", "approach_conveyor", "drop_cube", "exit_conveyor"
        ]
        for name in self.waypoint_names:
            self.declare_parameter(f'waypoints.{name}', [0.0]*6)

        self.get_logger().info(f"UR3e Controller for Robot {self.robot_id} Initialized")

    def send_move_goal(self, waypoint_name):
        if not self._action_client.wait_for_server(timeout_sec=5.0):
            return

        joint_positions = self.get_parameter(f'waypoints.{waypoint_name}').value
        goal_msg = FollowJointTrajectory.Goal()
        # Match the joint order published by /joint_states and recorded by joint_reader.py
        goal_msg.trajectory.joint_names = [
            'elbow_joint', 'shoulder_lift_joint', 'shoulder_pan_joint',
            'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint'
        ]

        # Log the start of movement
        self.get_logger().info(f"Moving to waypoint: {waypoint_name}")

        point = JointTrajectoryPoint()
        point.positions = joint_positions
        point.time_from_start = Duration(sec=3, nanosec=0) 
        goal_msg.trajectory.points.append(point)

        send_goal_future = self._action_client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            return

        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)

        # After the result_future is complete
        self.get_logger().info(f"Arrived at waypoint: {waypoint_name}")

    def pulse_gripper(self, state):
        """
        PULSE LOGIC:
        state 1 (Close): TO1 High, TO0 Low -> Wait -> Both Low
        state 0 (Open):  TO0 High, TO1 Low -> Wait -> Both Low
        """
        if not self.io_client.wait_for_service(timeout_sec=1.0):
            return

        # 1. TRIGGER THE MOVE
        req_pulse = SetIO.Request()
        req_pulse.fun = SetIO.Request.FUN_SET_DIGITAL_OUT

        action = "Closing" if state == 1 else "Opening"
        self.get_logger().info(f"Gripper: {action}...")

        if state == 1: # CLOSE
            # Set Close Pin High, Open Pin Low
            self._set_tool_io(SetIO.Request.PIN_TOOL_DOUT1, 1.0)
            self._set_tool_io(SetIO.Request.PIN_TOOL_DOUT0, 0.0)
        else: # OPEN
            # Set Open Pin High, Close Pin Low
            self._set_tool_io(SetIO.Request.PIN_TOOL_DOUT0, 1.0)
            self._set_tool_io(SetIO.Request.PIN_TOOL_DOUT1, 0.0)

        # 2. WAIT for the physical mechanism to move
        time.sleep(0.5)

        # 3. RESET BOTH TO 0 (The robot maintains position)
        self._set_tool_io(SetIO.Request.PIN_TOOL_DOUT0, 0.0)
        self._set_tool_io(SetIO.Request.PIN_TOOL_DOUT1, 0.0)

        self.get_logger().info(f"Gripper: {action} Complete (Pins Reset)")

    def _set_tool_io(self, pin, state):
        """Helper to send SetIO requests quickly"""
        req = SetIO.Request()
        req.fun = SetIO.Request.FUN_SET_DIGITAL_OUT
        req.pin = pin
        req.state = float(state)
        future = self.io_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=0.5)

    def power_conveyor(self, power):
        if not self.analog_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().error("Conveyor service '/io_and_status_controller/set_analog_output' not available!")
            return
        
        status = f"Turning ON (Power: {power})" if power > 0 else "Turning OFF"
        self.get_logger().info(f"Conveyor: {status}")
        
        # Robot 1/2: Port 0 | Robot 3: Port 1
        port = 0 if self.robot_id in [1, 2] else 1

        # Use SetAnalogOutput to explicitly set domain to VOLTAGE (0-10V) and output level
        req = SetAnalogOutput.Request()
        req.data.pin = port
        req.data.domain = Analog.VOLTAGE
        req.data.state = float(power)
        
        future = self.analog_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)

        

def main():
    rclpy.init()
    node = UR3eActionController()

    try:
        time.sleep(1)
        # MOVE the robot to a single waypoint:
    	#   node.send_move_goal("<waypoint_name>")
        
        # MOVE the robot through a set of waypoints
        #   pick_sequence = ["above_pallet", "approach_cube", "pick_up_pos", "raise_cube"]
        #   for wp in pick_sequence:
        #       node.send_move_goal(wp)
        
        # OPEN the gripper:
        #   node.pulse_gripper(0)
        
        # CLOSE the gripper:
        #   node.pulse_gripper(1)
         
    	
    	# RUN Conveyor Belt:
        #   node.power_conveyor(0.8)
        
    	
    	# STOP Conveyor Belt:
        #   node.power_conveyor(0.0)
    	
    	# WAIT:
    	#   time.sleep(<time in seconds>)


        # Create your logic to:
    	# 1. Pick up the block
    	# 2. Place the block in front of the color sensor
    	# 3. Clear the robot from the conveyor belt
    	# 4. Clear the block by running the conveyor belt
    	# 5. Loop 3 times


    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()
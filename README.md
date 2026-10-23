# Lab 10: UR3e Robot Programming & Sensor Integration
**Course**: MXET 400 – Mechatronics II: Industrial Robotic Systems  
**Department**: Multidisciplinary Engineering Technology, Texas A&M University  

---

## 1. Overview & Objectives

In this culminating lab, you integrate all major concepts learned across the semester into a complete autonomous industrial workcell:
1. **Motion Control via Actions**: Send multi-point trajectories to the UR3e arm using `control_msgs/action/FollowJointTrajectory` via `/scaled_joint_trajectory_controller/follow_joint_trajectory`.
2. **Gripper Actuation via Services**: Control the Zimmer pneumatic/electric gripper by toggling tool digital outputs using `ur_msgs/srv/SetIO` (`PIN_TOOL_DOUT0` for open, `PIN_TOOL_DOUT1` for close).
3. **Conveyor Control via Services**: Actuate the physical conveyor belt motor by commanding analog outputs using `ur_msgs/srv/SetIO`.
4. **Sensor Feedback via Topics**: Subscribe to block color readings published by the ESP32 UART bridge (`color_node.py`) on `/block_color`.
5. **Calibrated Waypoint Management**: Parameterize Cartesian and joint positions inside YAML configuration files (`config/lab10_Section50X.yaml`).

---

## 2. Package Structure

```text
lab10/
├── README.md                          # This lab guide & command reference
├── package.xml                        # Package dependencies
├── setup.py                           # Python module setup & console scripts
├── setup.cfg
├── config/
│   └── lab10_Section50X.yaml          # Student calibrated joint waypoints
├── startup_commands/                  # Copy-paste station execution commands
│   ├── ROBOT1.txt                     # Station 1 launch sequence
│   ├── ROBOT2.txt                     # Station 2 launch sequence
│   ├── ROBOT3.txt                     # Station 3 launch sequence
│   └── SIMULATION_DRY_RUN.txt         # Offline / at-home simulation commands
└── lab10/
    ├── __init__.py
    ├── color_node.py                  # ESP32 UART color sensor reader node
    └── Section50X/
        ├── __init__.py
        └── ur_controller.py           # Student controller template with # MODIFY HERE
```

---

## 3. Getting Started & Workspace Build

Build the package from the root of your workspace:

```bash
# 1. Navigate to workspace root
cd ~/ros2_ws

# 2. Build lab10
colcon build --symlink-install --packages-select lab10

# 3. Source the workspace
source install/setup.bash
```

---

## 4. Calibration Workflow: Waypoints in YAML

Before programming your pick-and-place sequence, you must calibrate the 8 joint waypoints for your assigned robot station and save them into `config/lab10_Section50X.yaml`:

```yaml
/**:
  ros__parameters:
    waypoints:
      home: [0.0, -1.57, 0.0, -1.57, 0.0, 0.0]
      above_pallet: [...]
      approach_cube: [...]
      pick_up_pos: [...]
      raise_cube: [...]
      approach_conveyor: [...]
      drop_cube: [...]
      exit_conveyor: [...]
```

### How to Record Joint Angles:
1. In PolyScope (Teach Pendant) or RViz, move the robot to the desired position.
2. Open a terminal and run:
   ```bash
   ros2 topic echo /joint_states --once
   ```
3. Copy the 6 joint values under `position` into your YAML file in the order expected by your controller:
   `[shoulder_lift, elbow, wrist_1, wrist_2, wrist_3, shoulder_pan]`

---

## 5. Execution Workflows

### Workflow A: Physical Robot Station in Lab

Follow the commands in your assigned station file inside `startup_commands/` (`ROBOT1.txt`, `ROBOT2.txt`, or `ROBOT3.txt`):

#### Terminal 1 (Robot Driver):
```bash
# For Robot Station 1 (IP: 192.168.1.31)
ros2 launch mxet_ur_launch ex-ur3e-1.launch.py robot_ip:=192.168.1.31 ur_type:="ur3e" launch_rviz:=false
```
*Wait for reverse interface ready, then press PLAY on the Teach Pendant.*

#### Terminal 2 (MoveIt 2):
```bash
ros2 launch mxet_ur_launch moveit-ur3-1.launch.py ur_type:="ur3e"
```

#### Terminal 3 (Color Sensor Node):
```bash
ros2 run lab10 color_sensor
```

#### Terminal 4 (Run Controller Program):
```bash
ros2 run lab10 Section50X --ros-args -p robot_id:=1 --params-file ~/ros2_ws/src/lab10/config/lab10_Section50X.yaml
```
*(Replace `Section50X` with your assigned lab section, e.g. `Section501`).*

---

### Workflow B: Offline / At-Home Simulation (No Robot Required)

You can test and verify all waypoints, gripper pulses, and loops at home without the physical robot using **Mock Hardware**:

#### Terminal 1 (Start Mock Hardware Driver):
```bash
ros2 launch ur_robot_driver ur_control.launch.py ur_type:=ur3e robot_ip:=127.0.0.1 use_mock_hardware:=true launch_rviz:=false
```
*Spawns the local `/scaled_joint_trajectory_controller/follow_joint_trajectory` action server and `/io_and_status_controller/set_io` service server.*

#### Terminal 2 (Start MoveIt & RViz):
```bash
ros2 launch ur_moveit_config ur_moveit.launch.py ur_type:=ur3e launch_rviz:=true
```

#### Terminal 3 (Mock Color Detection via CLI):
```bash
ros2 topic pub -r 1 /block_color std_msgs/msg/String "data: 'red'"
```

#### Terminal 4 (Run Controller Program):
```bash
ros2 run lab10 Section50X --ros-args -p robot_id:=1 --params-file ~/ros2_ws/src/lab10/config/lab10_Section50X.yaml
```
*Watch the simulated UR3e in RViz execute your waypoints and log arrival messages.*

---

## 6. Pick-and-Place State Machine Logic

Your `ur_controller.py` should implement the following loop sequence:
```python
for x in range(3):
    # 1. Move to pick up block
    pick_sequence = ["home", "above_pallet", "approach_cube", "pick_up_pos"]
    for wp in pick_sequence:
        node.send_move_goal(wp)
    node.pulse_gripper(1)  # Close gripper

    # 2. Move to drop off block on conveyor
    drop_sequence = ["approach_cube", "above_pallet", "approach_conveyor", "drop_cube"]
    for wp in drop_sequence:
        node.send_move_goal(wp)
    node.pulse_gripper(0)  # Open gripper

    # 3. Exit conveyor and clear block
    node.send_move_goal("exit_conveyor")
    node.power_conveyor(0.8)
    time.sleep(4.0)
    node.power_conveyor(0.0)
```

---

## 7. Checkpoint Checklist

Before completing your lab report, verify:
* [ ] Calibrated all 8 waypoints without joint limit or collision faults.
* [ ] Gripper opens and closes properly via `pulse_gripper()`.
* [ ] Conveyor starts and stops via `power_conveyor()`.
* [ ] Color sensor node broadcasts color on `/block_color`.
* [ ] Robot successfully picks, places, clears, and repeats for 3 complete cycles.

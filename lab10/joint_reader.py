#!/usr/bin/env python3

import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointWaypointRecorder(Node):
    def __init__(self):
        super().__init__("joint_waypoint_recorder")

        self.latest_positions = None
        self.latest_joint_names = None
        self.data_lock = threading.Lock()

        self.subscription = self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_state_callback,
            10,
        )

        self.get_logger().info("Subscribed to /joint_states")

    def joint_state_callback(self, msg):
        # Store the latest received values safely.
        with self.data_lock:
            self.latest_positions = list(msg.position)
            self.latest_joint_names = list(msg.name)

    def get_latest_joint_positions(self):
        with self.data_lock:
            if self.latest_positions is None:
                return None, None

            return (
                self.latest_joint_names.copy(),
                self.latest_positions.copy(),
            )


class WaypointGUI:
    def __init__(self, ros_node):
        self.node = ros_node
        self.file_path = None

        self.root = tk.Tk()
        self.root.title("ROS 2 Joint Waypoint Recorder")
        self.root.geometry("620x410")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.status_var = tk.StringVar(
            value="Waiting for /joint_states..."
        )

        self.file_var = tk.StringVar(value="No output file selected")
        self.joint_display_vars = [
            tk.StringVar(value=f"Joint {i + 1}: ---")
            for i in range(6)
        ]

        self.create_widgets()

        # Update displayed ROS joint values every 100 ms.
        self.root.after(100, self.update_joint_display)

    def create_widgets(self):
        title = tk.Label(
            self.root,
            text="ROS 2 Joint Waypoint Recorder",
            font=("Arial", 16, "bold"),
        )
        title.pack(pady=(15, 10))

        waypoint_frame = tk.Frame(self.root)
        waypoint_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            waypoint_frame,
            text="Waypoint name:",
            font=("Arial", 11),
        ).pack(side="left")

        self.waypoint_entry = tk.Entry(
            waypoint_frame,
            width=35,
            font=("Arial", 11),
        )
        self.waypoint_entry.pack(side="left", padx=10)
        self.waypoint_entry.focus_set()

        joint_frame = tk.LabelFrame(
            self.root,
            text="Current Joint Positions [rad]",
            padx=15,
            pady=10,
        )
        joint_frame.pack(fill="both", expand=True, padx=20, pady=10)

        for i, joint_var in enumerate(self.joint_display_vars):
            label = tk.Label(
                joint_frame,
                textvariable=joint_var,
                font=("Courier", 12),
                anchor="w",
            )
            label.grid(row=i, column=0, sticky="w", pady=2)

        file_frame = tk.Frame(self.root)
        file_frame.pack(fill="x", padx=20, pady=(0, 5))

        tk.Button(
            file_frame,
            text="Choose Output File",
            command=self.choose_file,
        ).pack(side="left")

        tk.Label(
            file_frame,
            textvariable=self.file_var,
            anchor="w",
        ).pack(side="left", padx=10)

        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="Record Waypoint",
            command=self.record_waypoint,
            font=("Arial", 12, "bold"),
            bg="#4CAF50",
            fg="white",
            padx=15,
            pady=6,
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="Exit",
            command=self.on_close,
            font=("Arial", 12),
            padx=15,
            pady=6,
        ).pack(side="left", padx=5)

        status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            fg="blue",
            wraplength=560,
        )
        status_label.pack(pady=(0, 12))

    def choose_file(self):
        path = filedialog.asksaveasfilename(
            title="Select Waypoint File",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
            initialfile="waypoints.txt",
        )

        if path:
            self.file_path = path
            self.file_var.set(os.path.basename(path))
            self.status_var.set(f"Saving waypoints to: {path}")

    def update_joint_display(self):
        joint_names, joint_positions = self.node.get_latest_joint_positions()

        if joint_positions is None:
            self.status_var.set("Waiting for /joint_states...")
        else:
            # Shows the first 6 joint positions received.
            for i in range(6):
                if i < len(joint_positions):
                    joint_name = (
                        joint_names[i]
                        if joint_names and i < len(joint_names)
                        else f"joint_{i + 1}"
                    )

                    self.joint_display_vars[i].set(
                        f"{joint_name:<15}: {joint_positions[i]: .6f} rad"
                    )
                else:
                    self.joint_display_vars[i].set(
                        f"Joint {i + 1}: not received"
                    )

            self.status_var.set(
                f"Receiving {len(joint_positions)} joint position value(s)."
            )

        self.root.after(100, self.update_joint_display)

    def record_waypoint(self):
        waypoint_name = self.waypoint_entry.get().strip()

        if not waypoint_name:
            messagebox.showwarning(
                "Missing waypoint name",
                "Enter a name for the waypoint first.",
            )
            return

        # Avoid spaces in names if these will later be parsed by another script.
        waypoint_name = waypoint_name.replace(" ", "_")

        joint_names, joint_positions = self.node.get_latest_joint_positions()

        if joint_positions is None:
            messagebox.showerror(
                "No joint data",
                "No /joint_states message has been received yet.",
            )
            return

        if len(joint_positions) < 6:
            messagebox.showerror(
                "Insufficient joints",
                f"Expected at least 6 joints, but received "
                f"{len(joint_positions)}.",
            )
            return

        if self.file_path is None:
            self.choose_file()

            # User cancelled the save-file dialog.
            if self.file_path is None:
                return

        # Use only the first six joints.
        positions = joint_positions[:6]

        # Requested output form:
        # waypoint_name: [0.00, 0.00, 0.00, 0.00, 0.00, 0.00]
        waypoint_line = (
            f"{waypoint_name}: "
            f"[{', '.join(f'{position:.6f}' for position in positions)}]\n"
        )

        try:
            with open(self.file_path, "a", encoding="utf-8") as waypoint_file:
                waypoint_file.write(waypoint_line)

            self.status_var.set(
                f"Recorded '{waypoint_name}' to "
                f"{os.path.basename(self.file_path)}"
            )

            self.node.get_logger().info(
                f"Saved waypoint: {waypoint_line.strip()}"
            )

            # Clears the field so a new waypoint name can be entered.
            self.waypoint_entry.delete(0, tk.END)
            self.waypoint_entry.focus_set()

        except OSError as error:
            self.node.get_logger().error(
                f"Could not write waypoint file: {error}"
            )
            messagebox.showerror(
                "File error",
                f"Could not save waypoint:\n{error}",
            )

    def on_close(self):
        self.node.get_logger().info("Closing waypoint recorder.")
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main(args=None):
    rclpy.init(args=args)

    node = JointWaypointRecorder()

    # ROS spinning must run separately because Tkinter owns the main thread.
    ros_spin_thread = threading.Thread(
        target=rclpy.spin,
        args=(node,),
        daemon=True,
    )
    ros_spin_thread.start()

    try:
        gui = WaypointGUI(node)
        gui.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
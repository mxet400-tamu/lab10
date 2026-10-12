# Import ROS 2 Python client library
import rclpy
from rclpy.node import Node

# Import the standard ROS message type used for publishing text
from std_msgs.msg import String, ColorRGBA
import serial
import json
import argparse


#ESP_ID = "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0"
ESP_ID = "/dev/ttyUSB0"

# Define a custom ROS node called ColorPublisher
class ColorPublisher(Node):

    def __init__(self, station_num):
        # Initialize the ROS node with the name 'color_publisher'
        super().__init__('color_publisher')

        self.station = station_num

        # Create a publisher that will publish RGB datasensor
        self.rgb_publisher = self.create_publisher(ColorRGBA, '/rgba', 10)

#######################################################################
######################### MODIFY HERE #################################
        '''
        Create the subscriber to send the block's color information
        1. Use a message type that will allow you to distinguish between:
            Red, Green, Blue, or None (no colored block detected)
        2. Assign a unique topic name for the publisher to publish to
            Standard naming convention is snake case (lowercase_underlines)
        '''
        
        self.box_publisher = self.create_publisher(
            String,                         # add correct message type
            'block_color',                  # add correct topic name
            10)

######################### END #########################################
#######################################################################

        if not self._init_serial():
            return

        self.last_color = ""
        self.read_err_ct = 0
        # Create a timer to repeatedly call the callback function
        timer_period = 0.2  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)

    def _init_serial(self):
        try:
            self.sensor = serial.Serial(ESP_ID, 115200, timeout=1)
            self.sensor.reset_input_buffer()
            self.get_logger().info("ESP32 Connected!")
            return True

        except Exception as e:
            self.get_logger().error("Could not establish Serial Connection: %s" % str(e))
            return False

    # This function is called repeatedly by the timer
    def timer_callback(self):
        try:
            # Read RGB values from the sensor
            doc = self.sensor.read_until(b"\n").strip()
            rgba = json.loads(doc)
        except Exception as e:
            self.get_logger().warning("Read Error: %s" % str(e))
            self.sensor.reset_input_buffer()
            self.read_err_ct += 1
            rgba: dict = {}
            if self.read_err_ct > 3:
                self.get_logger().error("Too many failed read attempts. Resetting serial port...")
                self.sensor.close()
                if not self._init_serial():
                    self.destroy_node()

        if len(rgba) > 1:
            r = float(rgba.get("red", 0))
            g = float(rgba.get("green" ,0))
            b = float(rgba.get("blue", 0))
            a = float(rgba.get("clear", 0))
        else:
            return
            
        # Format the RGB values into a string and publish it
        rgb_msg = ColorRGBA()
        rgb_msg.r = r
        rgb_msg.g = g
        rgb_msg.b = b
        rgb_msg.a = a
        self.rgb_publisher.publish(rgb_msg)
            
#######################################################################
######################### MODIFY HERE #################################
        '''
        Evaluate the block's color and publish it
        1. Create a message of an appropriate type
        2. Store the color in the message created
        3. Publish the message
            - Use the self.box_publisher created earlier
        '''
        # RECEIVES THE BLOCK'S COLOR
        box_color = self.evaluate_color(r, g, b, a)

        # CREATE MESSAGE
        box_msg = String()
        # STORE VALUE(S) IN MESSAGE 
        box_msg.data = box_color
        # PUBLISH MESSAGE
        self.box_publisher.publish(box_msg)
        if self.last_color != box_color:
            self.get_logger().info("Color: %s" % box_color)
            self.last_color = box_color

######################### END #########################################
#######################################################################

# A helper function to evaluate the color based on RGB values
    def evaluate_color(self, r, g, b, a):
        if self.station == 3:
            if a > 1800:
                return "WHITE"
            if b > g and b > r and b > 150:
                return "BLUE"
            elif r > b and r > g and r > 300:
                    return "RED"
            elif g > b and g > r and g > 140:
                    return "GREEN"
            return "no block detected"
        
        else:
            if b > g and b > r and b > 150:
                return "BLUE"
            elif g > b and g > r and g > 200:
                return "GREEN"
            elif r > 300:
                if r > b + g:
                    return "RED"
                else:
                    return "BROWN"
            return "no color detected"


# ROS 2 main function
def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--station", type=int, default=1, help="Robot station # (1, 2, or 3)")

    custom_args, ros_args = parser.parse_known_args()

    rclpy.init(args=ros_args) 

    color_publisher = ColorPublisher(custom_args.station)
    
    try:
        rclpy.spin(color_publisher) 
    finally:
        # Clean up after the node is stopped
        color_publisher.destroy_node()
        rclpy.shutdown()


# Entry point when the script is run directly
if __name__ == '__main__':
    main()

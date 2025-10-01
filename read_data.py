from dynamixel_sdk import *  # Dynamixel SDK
import math
# -------------------------------
# Dynamixel configuration
# -------------------------------
ADDR_PRESENT_CURRENT  = 126   # 2 bytes
ADDR_PRESENT_VELOCITY = 128   # 4 bytes
ADDR_PRESENT_POSITION = 132   # 4 bytes

PROTOCOL_VERSION = 2.0
BAUDRATE = 1000000
DEVICENAME = 'COM6'   # Adjust for your setup
DXL_IDS = [11, 12, 13, 14, 15]    # IDs of your joints


# Constants
TICKS_PER_REV = 4096
TICKS_TO_RAD = (2 * math.pi) / TICKS_PER_REV


# -------------------------------
# Initialize PortHandler and PacketHandler
# -------------------------------
portHandler = PortHandler(DEVICENAME)
packetHandler = PacketHandler(PROTOCOL_VERSION)

if not portHandler.openPort():
    raise Exception("Failed to open port")
if not portHandler.setBaudRate(BAUDRATE):
    raise Exception("Failed to set baudrate")

# -------------------------------
# Read joint states
# -------------------------------
def read_joint_state(dxl_id):
    # Position
    pos, _, _ = packetHandler.read4ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_POSITION)
    # Velocity
    vel, _, _ = packetHandler.read4ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_VELOCITY)
    # Current (proportional to torque)
    cur, _, _ = packetHandler.read2ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_CURRENT)
    
    pos_rad = pos * TICKS_TO_RAD

    return {
        "id": dxl_id,
        "position": pos,
        "pos_rad":pos_rad,

    }

# -------------------------------
# Example usage
# -------------------------------
try:
    while True:
        joint_states = [read_joint_state(dxl_id) for dxl_id in DXL_IDS]
        print(joint_states)

except KeyboardInterrupt:
    portHandler.closePort()
    print("Stopped.")

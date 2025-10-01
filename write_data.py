from dynamixel_sdk import *  # Dynamixel SDK
import math

# -------------------------------
# Dynamixel configuration
# -------------------------------
ADDR_TORQUE_ENABLE  = 64    # 1 byte
ADDR_GOAL_POSITION  = 116   # 4 bytes
TORQUE_ENABLE       = 1
TORQUE_DISABLE      = 0

PROTOCOL_VERSION = 2.0
BAUDRATE = 1000000
DEVICENAME = 'COM6'
DXL_IDS = [11, 12, 13, 14,15]

# Constants
TICKS_PER_REV = 4096
RAD_TO_TICKS = TICKS_PER_REV / (2 * math.pi)

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
# Enable torque for all joints
# -------------------------------
for dxl_id in DXL_IDS:
    dxl_comm_result, dxl_error = packetHandler.write1ByteTxRx(
        portHandler, dxl_id, ADDR_TORQUE_ENABLE, TORQUE_ENABLE
    )
    if dxl_comm_result != COMM_SUCCESS:
        print(f"Comm error on {dxl_id}: {packetHandler.getTxRxResult(dxl_comm_result)}")
    elif dxl_error != 0:
        print(f"Error on {dxl_id}: {packetHandler.getRxPacketError(dxl_error)}")

print("Torque enabled on all joints.")

# -------------------------------
# Write joint command
# -------------------------------
def write_joint_position(dxl_id, pos_rad):
    goal_ticks = int(pos_rad * RAD_TO_TICKS) % TICKS_PER_REV
    packetHandler.write4ByteTxRx(portHandler, dxl_id, ADDR_GOAL_POSITION, goal_ticks)

# -------------------------------
# Example usage (from Groot output)
# -------------------------------
groot_output = {
    11: 6.425845520452951,    # rad
    12: 4.422466611474303,   # rad
    13:4.732330730627203,   # rad
    14: 4.769146269536458,     # rad
    15: 3.0
}

# [{'id': 11, 'position': 4189, 'pos_rad': 6.425845520452951},
# {'id': 12, 'position': 2883, 'pos_rad': 4.422466611474303},
# {'id': 13, 'position': 3085, 'pos_rad': 4.732330730627203}, 
# {'id': 14, 'position': 3109, 'pos_rad': 4.769146269536458}, 
# {'id': 15, 'position': 1252, 'pos_rad': 1.9205439464328227}]

for dxl_id, pos_rad in groot_output.items():
    write_joint_position(dxl_id, pos_rad)

print("Commands sent to robot arm!")

# -------------------------------
# Disable torque + cleanup
# -------------------------------
for dxl_id in DXL_IDS:
    packetHandler.write1ByteTxRx(portHandler, dxl_id, ADDR_TORQUE_ENABLE, TORQUE_DISABLE)

portHandler.closePort()
print("Torque disabled and port closed.")

import numpy as np
import time
import socket
import struct
import os

#CAMERA_WIDTH = 1936
CAMERA_WIDTH = 5320
#CAMERA_HEIGHT = 1216
CAMERA_HEIGHT = 3032
BYTES_PER_PX = 2 # 12-bit capture mode requires 16-bit image transfers

# 8 x used to skip the pointing uncertainty bytes as the GUI is not designed to handle this
# we must use something like =, <, > at the beginning, otherwise the calculated size to
# unpack will vary according to the number and order of bytes to unpack:
# https://stackoverflow.com/a/12134822
ASTROMETRY_STRUCT_FMT = "<d d I d d d d d d d d d d d 8x 8x 8x 8x"
CAMERA_PARAMS_STRUCT_FMT = "i i i i i i i i d i d i i i i i i i d"
BLOB_PARAMS_STRUCT_FMT = "i i i i i i i f i i i"
STARCAM_DATA_SIZE_BYTES = struct.calcsize(ASTROMETRY_STRUCT_FMT + CAMERA_PARAMS_STRUCT_FMT + BLOB_PARAMS_STRUCT_FMT)

""" 
Creates and writs information header to the Star Camera data file if it does not already exist. If it does,
the file already includes a header, so the function just returns in that case.
Inputs: None.
Outputs: None. Writes information to the file and closes file.
"""
def prepareBackupFile():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    try:
        data_file = open(script_dir + os.path.sep + "data.txt", "x")
        header = ["C time (sec),GMT,RA (deg),DEC (deg),FR (deg),PS (arcsec/px),IR (deg),ALT (deg),AZ (deg)\n"]
        data_file.writelines(header)
        data_file.close()
    except FileExistsError:
        return

"""
Write telemetry to backup data file for the user.
Inputs: Raw, unpacked Star Camera data.
Outputs: None. Writes information to file and closes.
"""
def backupStarCamData(StarCam_data):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    # write this data to a .txt file (always updating)
    data_file = open(script_dir + os.path.sep + "data.txt", "a+")
    fmt = (
        ASTROMETRY_STRUCT_FMT +
        CAMERA_PARAMS_STRUCT_FMT +
        BLOB_PARAMS_STRUCT_FMT
    )
    unpacked_data = struct.unpack_from(fmt, StarCam_data)
    text = ["%s," % str(unpacked_data[1]), "%s," % str(time.asctime(time.gmtime(unpacked_data[1]))), 
            "%s," % str(unpacked_data[7]), "%s," % str(unpacked_data[8]), "%s," % str(unpacked_data[9]), 
            "%s," % str(unpacked_data[10]), "%s," % str(unpacked_data[11]), "%s," % str(unpacked_data[12]),
            "%s\n" % str(unpacked_data[13])]
    data_file.writelines(text)
    data_file.close()

"""
Create a socket with the Star Camera server on which to receive telemetry and send commands.
Inputs: Known IP address of Star Camera computer.
Outputs: The Star Camera socket, the Star Camera IP, and the Star Camera port.
"""
def establishStarCamSocket(StarCam_IP, user_port):
    # establish port with Star Camera
    server_addr = (StarCam_IP, user_port)
    # TCP socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(server_addr)
    print("Connected to %s" % repr(server_addr))
    return (s, StarCam_IP, user_port)

"""
Receive telemetry and camera settings from Star Camera.
Inputs: The socket to communicate with the camera.
Outputs: Raw, unpacked Star Camera data.
"""
def getStarCamData(client_socket):
    # number of expected bytes is hard-coded
    try: 
        (StarCam_data, _) = client_socket.recvfrom(STARCAM_DATA_SIZE_BYTES)
        backupStarCamData(StarCam_data)
        print("Received Star Camera data.")
        return StarCam_data
    except ConnectionResetError as e:
        print('getStarCamera handled ConnectionResetError exception:', e)
        return None
    except struct.error as e:
        print('getStarCamera handled struct.error exception:', e)
        return None

"""
Receive image bytes from camera.
Inputs: The socket to communicate with the camera.
Outputs: Raw image bytes.
"""
def getStarCamImage(client_socket):
    image_bytes = bytearray()
    # image dimensions
    n = CAMERA_WIDTH * CAMERA_HEIGHT * BYTES_PER_PX
    while (len(image_bytes) < n):
        packet = client_socket.recv(n - len(image_bytes)) 
        if not packet:
            return None
        image_bytes.extend(packet)
    print("Received Star Camera image bytes. Total number is bytes is:", 
          len(image_bytes))
    return image_bytes
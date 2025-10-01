#!/usr/bin/env python3
import argparse
import struct

from telnetlib_receive_all import Telnet
from Rigol_functions import *
import time
from PIL import Image
import io
import sys
import os
import platform
import logging

__version__ = 'v2.0.0'
__author__ = 'RoGeorge'

#
# TODO: Write all SCPI commands in their short name, with capitals
# TODO: Add ignore instrument model switch instead of asking
#
# TODO: Detect if the scope is in RUN or in STOP mode (looking at the length of data extracted)
# TODO: Add logic for 1200/mdep points to avoid displaying the 'Invalid Input!' message
# TODO: Add message for csv data points: mdep (all) or 1200 (screen), depending on RUN/STOP state, MATH and WAV:MODE
# TODO: Add STOP scope switch
#
# TODO: Add debug switch
# TODO: Clarify info, warning, error, debug and print messages
#
# TODO: Add automated version increase
#
# TODO: Extract all memory datapoints. For the moment, CSV is limited to the displayed 1200 datapoints.
# TODO: Use arrays instead of strings and lists for csv mode.
#
# TODO: variables/functions name refactoring
# TODO: Fine tune maximum chunk size request
# TODO: Investigate scaling. Sometimes 3.0e-008 instead of expected 3.0e-000
# TODO: Add timestamp and mark the trigger point as t0
# TODO: Use channels label instead of chan1, chan2, chan3, chan4, math
# TODO: Add command line parameters file path
# TODO: Speed-up the transfer, try to replace Telnet with direct TCP
# TODO: Add GUI
# TODO: Add browse and custom filename selection
# TODO: Create executable distributions
#

# Set the desired logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
logger = logging.getLogger()  # Root logger
log_filename = os.path.basename(sys.argv[0]) + '.log'
# Do not create the log file unless there is someting to write to this file (delay=True)
handler = logging.FileHandler(log_filename, mode='w', delay=True)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.ERROR)

logging.info("***** New run started...")
logging.info("OS Platform: " + str(platform.uname()))
log_running_python_versions()

# Rigol/LXI specific constants
port = 5555

big_wait = 10
smallWait = 1

company = 0
model = 1
serial = 2

# Check command line parameters
script_name = os.path.basename(sys.argv[0])


def copy_image_to_clipboard(image: Image):
    if platform.system() == "Windows":
        import win32clipboard

        # Convert image to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Get image dimensions
        width, height = image.size

        # Convert RGB to BGR for Windows DIB
        # Use NumPy to swap R and B channels
        # Get the pixel data as a list of (R, G, B) tuples
        rgb_pixels = list(image.getdata())

        # Convert to bytes in BGR format
        gbr_bytes = bytes(comp for pixel in rgb_pixels for comp in (pixel[2], pixel[1], pixel[0]))

        # Create BITMAPINFOHEADER for DIB
        bmi_header = struct.pack(
            '<LllHHLLllLL',
            40,  # biSize (size of header)
            width,  # biWidth
            -height,  # biHeight (negative for top-down DIB)
            1,  # biPlanes
            24,  # biBitCount (24 bits for RGB)
            0,  # biCompression (BI_RGB = uncompressed)
            len(gbr_bytes),  # biSizeImage
            0,  # biXPelsPerMeter
            0,  # biYPelsPerMeter
            0,  # biClrUsed
            0  # biClrImportant
        )

        # Combine header and pixel data for DIB
        dib_data = bmi_header + gbr_bytes

        # Copy to clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
        win32clipboard.CloseClipboard()
        print("Copied to clipboard")
    else:
        print(f"Copying screen shots to the clipboard on {platform.system()} is not supported yet.")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Capture waveform or screen from Rigol DS1000Z series oscilloscope using LXI protocol over LAN",
    )
    parser.add_argument(
        '-f', '--format',
        choices=['png', 'bmp', 'csv', 'clip'],
        default='clip',
        help=f'File format to save capture. \'clip\' just copies the image data to the clipboard. Default: \'%(default)s\''
    )
    parser.add_argument(
        '-i', '--ip',
        default='192.168.1.60',
        help=f'Oscilloscope IP address. Default: \'%(default)s\''
    )
    parser.add_argument(
        '-p', '--path',
        default='captures',
        help=f'Path to save captures. Only relevant for PNG, BMP or CSV exports.  Default: \'%(default)s\''
    )
    args = parser.parse_args()
    return args.format.lower(), args.ip, args.path


# Parse command-line arguments
file_format, IP_DS1104Z, path_to_save = parse_arguments()
path_to_save = os.path.normpath(path_to_save)
file_format = file_format.lower()

# Open a modified telnet session
# The default telnetlib drops 0x00 characters,
#   so a modified library 'telnetlib_receive_all' is used instead
tn = Telnet(IP_DS1104Z, port)
instrument_id = command(tn, "*IDN?")  # ask for instrument ID

# Check if instrument is set to accept LAN commands
if instrument_id == "command error":
    print("Instrument reply:", instrument_id)
    print("Check the oscilloscope settings.")
    print("Utility -> IO Setting -> RemoteIO -> LAN must be ON")
    sys.exit("ERROR")

# Check if instrument is indeed a Rigol DS1000Z series
id_fields = instrument_id.split(",")
if (id_fields[company] != "RIGOL TECHNOLOGIES") or \
        (id_fields[model][:2] != "DS"):
    print("Found instrument model", "'" + id_fields[model] + "'", "from", "'" + id_fields[company] + "'")
    print("WARNING: No Rigol from series DS1000Z found at", IP_DS1104Z)
    sys.exit('Nothing done. Bye!')

print("Instrument ID:", instrument_id)

# generate the output file name - we will not use it if we copy to the clipboard only.
timestamp = time.strftime("%Y-%m-%d_%H.%M.%S", time.localtime())
filename = os.path.join(path_to_save,
                        f"{id_fields[model].replace(" ", "_")}_{id_fields[serial]}_{timestamp}.{file_format}")

if file_format in ["png", "bmp", "clip"]:
    # Ask for an oscilloscope display print screen
    print("Receiving screen capture...")
    buff = command_bin(tn, ":DISP:DATA?")

    expectedBuffLen = expected_buff_bytes(buff)
    # Just in case the transfer did not complete in the expected time, read the remaining 'buff' chunks
    while len(buff) < expectedBuffLen:
        logging.warning("Received LESS data then expected! (" +
                        str(len(buff)) + " out of " + str(expectedBuffLen) + " expected 'buff' bytes.)")
        tmp = tn.read_until(b"\n", smallWait)
        if len(tmp) == 0:
            break
        buff += tmp
        logging.warning(str(len(tmp)) + " leftover bytes added to 'buff'.")

    if len(buff) < expectedBuffLen:
        logging.error("After reading all data chunks, 'buff' is still shorter then expected! (" +
                      str(len(buff)) + " out of " + str(expectedBuffLen) + " expected 'buff' bytes.)")
        sys.exit("ERROR")

    # Strip TMC Blockheader and keep only the data
    tmcHeaderLen = tmc_header_bytes(buff)
    expectedDataLen = expected_data_bytes(buff)
    buff = buff[tmcHeaderLen: tmcHeaderLen + expectedDataLen]

    # Save as PNG or BMP according to file_format
    im = Image.open(io.BytesIO(buff))
    if file_format in ["png", "bmp"]:
        os.makedirs(path_to_save, exist_ok=True)
        # Prepare filename as MODEL_SERIAL_YYYY-MM-DD_HH.MM.SS
        im.save(filename)

        print(f"Saved file: '{filename}'")
    else:
        copy_image_to_clipboard(im)

# TODO: Change WAV:FORM from ASC to BYTE
elif file_format == "csv":
    # Put the scope in STOP mode - for the moment, deal with it by manually stopping the scope
    # TODO: Add command line switch and code logic for 1200 vs ALL memory data points
    # tn.write("stop")
    # response = tn.read_until(b"\n", 1)

    # Scan for displayed channels
    chanList = []
    for channel in ["CHAN1", "CHAN2", "CHAN3", "CHAN4", "MATH"]:
        response = command(tn, ":" + channel + ":DISP?")

        # If channel is active
        if response == '1\n':
            chanList += [channel]

    # the meaning of 'max' is   - will read only the displayed data when the scope is in RUN mode,
    #                             or when the MATH channel is selected
    #                           - will read all the acquired data points when the scope is in STOP mode
    # TODO: Change mode to MAX
    # TODO: Add command line switch for MAX/NORM
    command(tn, ":WAV:MODE NORM")
    command(tn, ":WAV:STAR 0")
    command(tn, ":WAV:MODE NORM")

    csv_buff = ""

    # for each active channel
    for channel in chanList:
        print()

        # Set WAVE parameters
        command(tn, ":WAV:SOUR " + channel)
        command(tn, ":WAV:FORM ASC")

        # MATH channel does not allow START and STOP to be set. They are always 0 and 1200
        if channel != "MATH":
            command(tn, ":WAV:STAR 1")
            command(tn, ":WAV:STOP 1200")

        print("Data from channel '" + str(channel) + "', points " + str(1) + "-" + str(1200) + ": Receiving...")
        buffChunk = command(tn, ":WAV:DATA?")

        # Just in case the transfer did not complete in the expected time
        while buffChunk[-1] != "\n":
            logging.warning("The data transfer did not complete in the expected time of " +
                            str(smallWait) + " second(s).")

            tmp = tn.read_until(b"\n", smallWait)
            if len(tmp) == 0:
                break
            buffChunk += tmp
            logging.warning(str(len(tmp)) + " leftover bytes added to 'buff_chunks'.")

        # Append data chunks
        # Strip TMC Blockheader and terminator bytes
        buff = buffChunk[tmc_header_bytes(buffChunk):-1].rstrip()

        # Process data
        buff_list = buff.split(",")
        buff_rows = len(buff_list)

        # Put read data into csv_buff
        csv_buff_list = csv_buff.split(os.linesep)
        csv_rows = len(csv_buff_list)

        current_row = 0
        if csv_buff == "":
            csv_first_column = True
            csv_buff = str(channel) + os.linesep
        else:
            csv_first_column = False
            csv_buff = str(csv_buff_list[current_row]) + "," + str(channel) + os.linesep

        for point in buff_list:
            current_row += 1
            if csv_first_column:
                csv_buff += str(point) + os.linesep
            else:
                if current_row < csv_rows:
                    csv_buff += str(csv_buff_list[current_row]) + "," + str(point) + os.linesep
                else:
                    csv_buff += "," + str(point) + os.linesep

    # Save data as CSV
    os.makedirs(path_to_save, exist_ok=True)
    scr_file = open(filename + "." + file_format, "wb")
    scr_file.write(csv_buff.encode())
    scr_file.close()

    print(f"Saved file: '{filename}'")

tn.close()

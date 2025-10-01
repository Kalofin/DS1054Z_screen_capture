import sys
import logging

__author__ = 'RoGeorge'


def log_running_python_versions():
    logging.info("Python version: " + str(sys.version) + ", " + str(sys.version_info))  # () required in Python 3.

def command(tn, scpi):
    logging.info("SCPI to be sent: " + scpi)
    answer_wait_s = 1
    response = ""
    while response != "1\n":
        tn.write(b"*OPC?\n")  # previous operation(s) has completed ?
        logging.info("Send SCPI: *OPC? # May I send a command? 1==yes")
        response = tn.read_until(b"\n", 1).decode()  # wait max 1s for an answer
        logging.info("Received response: " + response)

    tn.write(scpi.encode() + b"\n")
    logging.info("Sent SCPI: " + scpi)
    response = tn.read_until(b"\n", answer_wait_s).decode()
    logging.info("Received response: " + response)
    return response


def command_bin(tn, scpi):
    logging.info("SCPI to be sent: " + scpi)
    answer_wait_s = 1
    response = b""
    while response != b"1\n":
        tn.write(b"*OPC?\n")  # previous operation(s) has completed ?
        logging.info("Send SCPI: *OPC? # May I send a command? 1==yes")
        response = tn.read_until(b"\n", 1)  # wait max 1s for an answer
        logging.info("Received response: " + repr(response))

    tn.write(scpi.encode() + b"\n")
    logging.info("Sent SCPI: " + scpi)
    response = tn.read_until(b"\n", answer_wait_s)
    logging.info("Received response: " + repr(response))
    return response


# first TMC byte is '#'
# second is '0'..'9', and tells how many of the next ASCII chars
#   should be converted into an integer.
#   The integer will be the length of the data stream (in bytes)
# after all the data bytes, the last char is '\n'
def tmc_header_bytes(buff):
    # we either receive a string or bytes. Handle then accordingly.
    if isinstance(buff, bytes):
        return 2 + int(buff[1:2].decode())
    else:
        return 2 + int(buff[1])


def expected_data_bytes(buff):
    return int(buff[2:tmc_header_bytes(buff)].decode())


def expected_buff_bytes(buff):
    return tmc_header_bytes(buff) + expected_data_bytes(buff) + 1


def get_memory_depth(tn):
    # Define number of horizontal grid divisions for DS1054Z
    h_grid = 12

    # ACQuire:MDEPth
    mdep = command(tn, ":ACQ:MDEP?")

    # if mdep is "AUTO"
    if mdep == "AUTO\n":
        # ACQuire:SRATe
        srate = command(tn, ":ACQ:SRAT?")

        # TIMebase[:MAIN]:SCALe
        scal = command(tn, ":TIM:SCAL?")

        # mdep = h_grid * scal * srate
        mdep = h_grid * float(scal) * float(srate)

    # return mdep
    return int(mdep)

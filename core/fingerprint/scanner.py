import serial
import serial.tools.list_ports
import time

from pathlib import Path
from datetime import datetime

from PIL import Image, ImageEnhance, ImageFilter


# ============================================================
# CONFIGURATION
# ============================================================

# Preferred ESP8266 port.
# The scanner will try this port first.
PREFERRED_PORT = "COM7"

# PC <-> ESP8266 baudrate
BAUDRATE = 115200

# ESP8266 identification command
SCAN_COMMAND = b"SCAN\n"

# ESP8266 response after receiving SCAN
READY_RESPONSE = b"READY"

# Image transmission marker
MAGIC = b"RAWF"


# ============================================================
# AS608 IMAGE
# ============================================================

# AS608 uploaded image:
#
# Width  = 256
# Height = 288
# 4-bit grayscale
#
# 2 pixels per byte
#
# 256 * 288 / 2
# = 36864 bytes

WIDTH = 256
HEIGHT = 288

EXPECTED_IMAGE_BYTES = (
    WIDTH * HEIGHT
) // 2


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

CAPTURE_DIR = (
    BASE_DIR
    / "captures"
)

CAPTURE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LIST SERIAL PORTS
# ============================================================

def list_serial_ports():

    ports = list(
        serial.tools.list_ports.comports()
    )

    if not ports:

        print()
        print(
            "No serial ports detected."
        )
        print()

        return []

    print()
    print(
        "Available serial ports:"
    )
    print(
        "----------------------------------------"
    )

    for port in ports:

        print(
            f"Port        : {port.device}"
        )

        print(
            f"Description : {port.description}"
        )

        if port.manufacturer:

            print(
                f"Manufacturer: {port.manufacturer}"
            )

        if port.hwid:

            print(
                f"Hardware ID : {port.hwid}"
            )

        print(
            "----------------------------------------"
        )

    return ports


# ============================================================
# OPEN SERIAL
# ============================================================

def open_serial(port):

    print()
    print(
        "Opening serial port..."
    )

    print(
        f"PORT     : {port}"
    )

    print(
        f"BAUDRATE : {BAUDRATE}"
    )

    ser = serial.Serial(
        port=port,
        baudrate=BAUDRATE,
        timeout=0.1
    )

    # ESP8266 can reset when the serial
    # port is opened because of DTR/RTS.
    time.sleep(2.0)

    # Clear old serial data.
    ser.reset_input_buffer()
    ser.reset_output_buffer()

    print(
        "Serial connected."
    )

    return ser


# ============================================================
# READ LINE WITH TIMEOUT
# ============================================================

def read_line_timeout(
    ser,
    timeout=1.0
):

    start_time = time.time()

    buffer = bytearray()

    while (
        time.time() - start_time
        < timeout
    ):

        data = ser.read(
            ser.in_waiting or 1
        )

        if data:

            buffer.extend(
                data
            )

            if b"\n" in buffer:

                line = bytes(
                    buffer
                )

                return line.strip()

        else:

            time.sleep(0.01)

    return None


# ============================================================
# SEND SCAN COMMAND
# ============================================================

def send_scan_command(
    ser
):

    print()
    print(
        "Sending SCAN command..."
    )

    # Clear anything left in buffer.
    ser.reset_input_buffer()

    # Send command.
    ser.write(
        SCAN_COMMAND
    )

    ser.flush()

    # Wait for READY.
    deadline = (
        time.time()
        + 4
    )

    received = bytearray()

    while time.time() < deadline:

        data = ser.read(
            ser.in_waiting or 1
        )

        if data:

            received.extend(
                data
            )

            # ------------------------------------------------
            # READY
            # ------------------------------------------------

            if READY_RESPONSE in received:

                print(
                    "ESP8266 READY"
                )

                return True

            # ------------------------------------------------
            # Keep buffer reasonable.
            # ------------------------------------------------

            if len(received) > 128:

                received = received[
                    -64:
                ]

        else:

            time.sleep(0.01)

    print(
        "No READY response."
    )

    if received:

        print(
            "Received:"
        )

        print(
            repr(bytes(received))
        )

    return False


# ============================================================
# DETECT ESP8266
# ============================================================

def detect_esp32_port():

    print()
    print(
        "========================================"
    )

    print(
        "SCANNING FOR ESP8266"
    )

    print(
        "========================================"
    )

    ports = list(
        serial.tools.list_ports.comports()
    )

    if not ports:

        print()
        print(
            "ERROR: No serial ports detected."
        )

        return None


    # ========================================================
    # PUT PREFERRED PORT FIRST
    # ========================================================

    ordered_ports = []

    preferred = None

    for port in ports:

        if (
            port.device.upper()
            ==
            PREFERRED_PORT.upper()
        ):

            preferred = port

            break


    if preferred:

        ordered_ports.append(
            preferred
        )


    for port in ports:

        if preferred:

            if (
                port.device
                ==
                preferred.device
            ):

                continue

        ordered_ports.append(
            port
        )


    # ========================================================
    # TEST PORTS
    # ========================================================

    for port_info in ordered_ports:

        port = port_info.device

        print()
        print(
            "----------------------------------------"
        )

        print(
            f"Testing port: {port}"
        )

        print(
            f"Description : "
            f"{port_info.description}"
        )

        ser = None

        try:

            # ------------------------------------------------
            # OPEN PORT
            # ------------------------------------------------

            ser = serial.Serial(
                port=port,
                baudrate=BAUDRATE,
                timeout=0.1
            )

            # ------------------------------------------------
            # Allow ESP8266 to initialize.
            # ------------------------------------------------

            time.sleep(2.0)

            # ------------------------------------------------
            # Clear buffers.
            # ------------------------------------------------

            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # ------------------------------------------------
            # Send SCAN.
            # ------------------------------------------------

            detected = send_scan_command(
                ser
            )

            if detected:

                print()
                print(
                    "========================================"
                )

                print(
                    "ESP8266 DETECTED"
                )

                print(
                    f"Port: {port}"
                )

                print(
                    "========================================"
                )

                return ser


            print(
                f"No ESP8266 response on {port}."
            )


        except Exception as e:

            print(
                f"Cannot use {port}: {e}"
            )


        if ser is not None:

            try:

                if ser.is_open:

                    ser.close()

            except Exception:

                pass


    # ========================================================
    # NOT FOUND
    # ========================================================

    print()
    print(
        "========================================"
    )

    print(
        "ESP8266 NOT FOUND"
    )

    print(
        "========================================"
    )

    return None


# ============================================================
# FIND RAWF
# ============================================================

def find_magic(
    ser,
    timeout=None
):

    print()
    print(
        "Waiting for ESP8266 RAWF signal..."
    )

    print(
        "Place your finger on the AS608."
    )

    print()

    buffer = bytearray()

    start_time = time.time()

    while True:

        # ----------------------------------------------------
        # Optional timeout.
        # None = wait forever.
        # ----------------------------------------------------

        if timeout is not None:

            if (
                time.time()
                -
                start_time
                >= timeout
            ):

                return False


        byte = ser.read(1)

        if not byte:

            continue


        buffer.extend(
            byte
        )


        if len(buffer) > len(MAGIC):

            buffer = buffer[
                -len(MAGIC):
            ]


        if bytes(buffer) == MAGIC:

            print()
            print(
                "RAWF DETECTED"
            )

            return True


# ============================================================
# FIND AS608 PACKET HEADER
# ============================================================

def find_packet_header(
    ser
):

    buffer = bytearray()

    while True:

        byte = ser.read(1)

        if not byte:

            continue


        buffer.extend(
            byte
        )


        if len(buffer) > 2:

            buffer = buffer[
                -2:
            ]


        if bytes(buffer) == b"\xEF\x01":

            return b"\xEF\x01"


# ============================================================
# READ EXACT BYTES
# ============================================================

def read_exact(
    ser,
    size
):

    data = bytearray()

    while len(data) < size:

        chunk = ser.read(
            size - len(data)
        )

        if not chunk:

            continue

        data.extend(
            chunk
        )

    return bytes(data)


# ============================================================
# READ AS608 PACKET
# ============================================================

def read_as608_packet(
    ser
):

    # --------------------------------------------------------
    # Start code
    # --------------------------------------------------------

    start = find_packet_header(
        ser
    )


    # --------------------------------------------------------
    # Address
    # --------------------------------------------------------

    address = read_exact(
        ser,
        4
    )


    # --------------------------------------------------------
    # Packet type
    # --------------------------------------------------------

    packet_type = read_exact(
        ser,
        1
    )[0]


    # --------------------------------------------------------
    # Length
    # --------------------------------------------------------

    length_bytes = read_exact(
        ser,
        2
    )


    length = int.from_bytes(
        length_bytes,
        byteorder="big"
    )


    # --------------------------------------------------------
    # Validate length.
    # --------------------------------------------------------

    if length < 2:

        raise ValueError(
            f"Invalid AS608 packet length: {length}"
        )


    if length > 256:

        raise ValueError(
            f"AS608 packet too large: {length}"
        )


    # --------------------------------------------------------
    # Payload + checksum
    # --------------------------------------------------------

    payload_and_checksum = read_exact(
        ser,
        length
    )


    packet = (
        start
        +
        address
        +
        bytes([packet_type])
        +
        length_bytes
        +
        payload_and_checksum
    )


    return (
        packet,
        packet_type,
        length,
        payload_and_checksum
    )


# ============================================================
# CAPTURE FINGERPRINT
# ============================================================

def capture_fingerprint():

    ser = None

    image_bytes = bytearray()

    packet_stream = bytearray()


    try:

        # ====================================================
        # DETECT ESP8266
        # ====================================================

        ser = detect_esp32_port()


        if ser is None:

            print()
            print(
                "Fingerprint scanner could not "
                "be detected."
            )

            return None


        # ====================================================
        # WAIT FOR RAWF
        # ====================================================

        if not find_magic(
            ser
        ):

            print(
                "RAWF timeout."
            )

            return None


        print()
        print(
            "Waiting for AS608 image packets..."
        )


        packet_number = 0


        # ====================================================
        # RECEIVE AS608 PACKETS
        # ====================================================

        while True:

            (
                packet,
                packet_type,
                length,
                payload_and_checksum
            ) = read_as608_packet(
                ser
            )


            packet_number += 1


            packet_stream.extend(
                packet
            )


            # ------------------------------------------------
            # AS608 packet length includes checksum.
            # ------------------------------------------------

            if length < 2:

                print(
                    f"Packet {packet_number}: "
                    f"invalid length={length}"
                )

                continue


            # ------------------------------------------------
            # Remove 2-byte checksum.
            # ------------------------------------------------

            payload = (
                payload_and_checksum[:-2]
            )


            print(
                f"Packet {packet_number}: "
                f"type=0x{packet_type:02X}, "
                f"length={length}, "
                f"image={len(payload)}"
            )


            # ------------------------------------------------
            # DATA PACKET
            # ------------------------------------------------

            if packet_type == 0x02:

                image_bytes.extend(
                    payload
                )


            # ------------------------------------------------
            # END PACKET
            # ------------------------------------------------

            elif packet_type == 0x08:

                image_bytes.extend(
                    payload
                )

                print()
                print(
                    "AS608 image transmission "
                    "complete."
                )

                break


            # ------------------------------------------------
            # OTHER PACKET
            # ------------------------------------------------

            else:

                print(
                    f"Warning: unexpected "
                    f"packet type "
                    f"0x{packet_type:02X}"
                )


        # ====================================================
        # IMAGE SIZE
        # ====================================================

        print()
        print(
            "========================================"
        )

        print(
            f"Received image bytes : "
            f"{len(image_bytes)}"
        )

        print(
            f"Expected image bytes : "
            f"{EXPECTED_IMAGE_BYTES}"
        )

        print(
            "========================================"
        )


        # ====================================================
        # TIMESTAMP
        # ====================================================

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )


        # ====================================================
        # SAVE RAW PACKET STREAM
        # ====================================================

        bin_path = (
            CAPTURE_DIR
            /
            f"fingerprint_{timestamp}.bin"
        )


        with open(
            bin_path,
            "wb"
        ) as f:

            f.write(
                packet_stream
            )


        print()
        print(
            "Packet stream saved:"
        )

        print(
            bin_path
        )


        # ====================================================
        # VALIDATE IMAGE SIZE
        # ====================================================

        if (
            len(image_bytes)
            !=
            EXPECTED_IMAGE_BYTES
        ):

            print()
            print(
                "ERROR:"
            )

            print(
                "Image byte count does not "
                "match the expected size."
            )

            return None


        # ====================================================
        # PNG
        # ====================================================

        print()
        print(
            "Starting PNG conversion..."
        )


        png_path = decode_and_save_png(
            bytes(image_bytes),
            timestamp
        )


        return png_path


    except Exception as e:

        print()
        print(
            "========================================"
        )

        print(
            "ERROR"
        )

        print(
            "========================================"
        )

        print(
            str(e)
        )


        import traceback

        traceback.print_exc()


        return None


    finally:

        if (
            ser is not None
            and
            ser.is_open
        ):

            ser.close()

            print()
            print(
                "Serial connection closed."
            )


# ============================================================
# DECODE 4-BIT FINGERPRINT IMAGE
# ============================================================

def decode_fingerprint_image(
    image_bytes
):

    if (
        len(image_bytes)
        !=
        EXPECTED_IMAGE_BYTES
    ):

        raise ValueError(
            f"Invalid image size. "
            f"Received {len(image_bytes)}, "
            f"expected "
            f"{EXPECTED_IMAGE_BYTES}."
        )


    # ========================================================
    # TWO PIXELS PER BYTE
    # ========================================================

    pixels = bytearray(
        WIDTH * HEIGHT
    )


    pixel_index = 0


    for value in image_bytes:

        high_nibble = (
            value >> 4
        ) & 0x0F


        low_nibble = (
            value
            &
            0x0F
        )


        # ----------------------------------------------------
        # High nibble
        # ----------------------------------------------------

        pixels[pixel_index] = (
            high_nibble * 17
        )

        pixel_index += 1


        # ----------------------------------------------------
        # Low nibble
        # ----------------------------------------------------

        pixels[pixel_index] = (
            low_nibble * 17
        )

        pixel_index += 1


    image = Image.frombytes(
        "L",
        (
            WIDTH,
            HEIGHT
        ),
        bytes(pixels)
    )


    return image


# ============================================================
# ENHANCE FINGERPRINT
# ============================================================

def enhance_fingerprint(
    image
):

    # --------------------------------------------------------
    # Grayscale
    # --------------------------------------------------------

    image = image.convert(
        "L"
    )


    # --------------------------------------------------------
    # Increase contrast
    # --------------------------------------------------------

    contrast = ImageEnhance.Contrast(
        image
    )

    image = contrast.enhance(
        2.0
    )


    # --------------------------------------------------------
    # Sharpen
    # --------------------------------------------------------

    image = image.filter(
        ImageFilter.SHARPEN
    )


    return image


# ============================================================
# SAVE PNG
# ============================================================

def decode_and_save_png(
    image_bytes,
    timestamp
):

    print()
    print(
        "Decoding fingerprint image..."
    )


    # ========================================================
    # DECODE
    # ========================================================

    image = decode_fingerprint_image(
        image_bytes
    )


    print(
        f"Decoded image size: "
        f"{image.width} x {image.height}"
    )


    # ========================================================
    # ENHANCE
    # ========================================================

    image = enhance_fingerprint(
        image
    )


    # ========================================================
    # PATH
    # ========================================================

    png_path = (
        CAPTURE_DIR
        /
        f"fingerprint_{timestamp}.png"
    )


    # ========================================================
    # SAVE
    # ========================================================

    image.save(
        png_path,
        format="PNG"
    )


    # ========================================================
    # VERIFY
    # ========================================================

    if not png_path.exists():

        raise RuntimeError(
            "PNG file was not created."
        )


    file_size = (
        png_path.stat().st_size
    )


    if file_size <= 0:

        raise RuntimeError(
            "PNG file was created "
            "but is empty."
        )


    print()
    print(
        "========================================"
    )

    print(
        "PNG CREATED SUCCESSFULLY"
    )

    print(
        "========================================"
    )

    print(
        f"PNG path : {png_path}"
    )

    print(
        f"PNG size : {file_size:,} bytes"
    )

    print(
        f"Image    : "
        f"{image.width} x {image.height}"
    )

    print(
        "========================================"
    )

    print()


    return png_path


# ============================================================
# LEFT FINGER
# ============================================================

def capture_left_finger():

    return capture_fingerprint()


# ============================================================
# RIGHT FINGER
# ============================================================

def capture_right_finger():

    return capture_fingerprint()


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    png_path = capture_fingerprint()


    if png_path:

        print()
        print(
            "Fingerprint capture completed."
        )

        print()
        print(
            "Open this PNG:"
        )

        print(
            png_path
        )


    else:

        print()
        print(
            "Fingerprint capture failed."
        )
#include <Arduino.h>
#include <Adafruit_Fingerprint.h>

HardwareSerial FingerSerial(2);

#define AS608_RX 16
#define AS608_TX 17

Adafruit_Fingerprint finger(&FingerSerial);

#define PACKET_COMMAND  0x01
#define PACKET_DATA     0x02
#define PACKET_ACK      0x07
#define PACKET_END      0x08

#define CMD_UPLOAD_IMAGE 0x0A


// =========================================================
// Read exactly N bytes from AS608
// =========================================================

bool readExact(
    uint8_t *buffer,
    size_t length,
    uint32_t timeoutMs
)
{
    size_t received = 0;

    uint32_t lastData = millis();

    while (received < length)
    {
        if (FingerSerial.available())
        {
            buffer[received++] =
                FingerSerial.read();

            lastData = millis();
        }

        if (millis() - lastData > timeoutMs)
        {
            return false;
        }
    }

    return true;
}


// =========================================================
// Send UPLOAD IMAGE command
// =========================================================

void sendUploadImage()
{
    uint8_t packet[] =
    {
        0xEF,
        0x01,

        0xFF,
        0xFF,
        0xFF,
        0xFF,

        0x01,

        0x00,
        0x03,

        0x0A,

        0x00,
        0x0E
    };

    FingerSerial.write(
        packet,
        sizeof(packet)
    );

    FingerSerial.flush();
}


// =========================================================
// Read ACK packet
// =========================================================

bool readAck()
{
    uint8_t header[9];

    if (!readExact(
        header,
        9,
        3000
    ))
    {
        return false;
    }

    if (header[0] != 0xEF ||
        header[1] != 0x01)
    {
        return false;
    }

    if (header[6] != PACKET_ACK)
    {
        return false;
    }

    uint16_t length =
        ((uint16_t)header[7] << 8) |
        header[8];

    if (length < 3)
    {
        return false;
    }

    /*
       length includes:

       confirmation code
       checksum high
       checksum low
    */

    uint16_t remaining = length;

    uint8_t buffer[260];

    if (remaining > sizeof(buffer))
    {
        return false;
    }

    if (!readExact(
        buffer,
        remaining,
        3000
    ))
    {
        return false;
    }

    if (buffer[0] != 0x00)
    {
        return false;
    }

    return true;
}


// =========================================================
// Read one complete AS608 data packet
//
// Returns the complete packet:
//
// EF 01
// ADDRESS
// TYPE
// LENGTH
// DATA
// CHECKSUM
// =========================================================

bool readCompletePacket(
    uint8_t *packet,
    size_t &packetSize,
    uint8_t &packetType
)
{
    // -----------------------------------------------------
    // Find EF 01
    // -----------------------------------------------------

    uint8_t byte;

    bool foundHeader = false;

    while (!foundHeader)
    {
        if (!readExact(
            &byte,
            1,
            5000
        ))
        {
            return false;
        }

        if (byte != 0xEF)
        {
            continue;
        }

        uint8_t second;

        if (!readExact(
            &second,
            1,
            1000
        ))
        {
            return false;
        }

        if (second == 0x01)
        {
            packet[0] = 0xEF;
            packet[1] = 0x01;

            foundHeader = true;
        }
    }


    // -----------------------------------------------------
    // Address
    // -----------------------------------------------------

    if (!readExact(
        &packet[2],
        4,
        1000
    ))
    {
        return false;
    }


    // -----------------------------------------------------
    // Packet type
    // -----------------------------------------------------

    if (!readExact(
        &packet[6],
        1,
        1000
    ))
    {
        return false;
    }

    packetType = packet[6];


    // -----------------------------------------------------
    // Length
    // -----------------------------------------------------

    if (!readExact(
        &packet[7],
        2,
        1000
    ))
    {
        return false;
    }

    uint16_t length =
        ((uint16_t)packet[7] << 8) |
        packet[8];


    /*
       length includes:

       payload
       + checksum
    */

    if (length < 2)
    {
        return false;
    }


    // -----------------------------------------------------
    // Payload + checksum
    // -----------------------------------------------------

    if (length > 256)
    {
        return false;
    }

    if (!readExact(
        &packet[9],
        length,
        5000
    ))
    {
        return false;
    }


    packetSize =
        9 + length;


    return true;
}


// =========================================================
// Dump image packets
// =========================================================

bool dumpImage()
{
    // -----------------------------------------------------
    // Send upload command
    // -----------------------------------------------------

    sendUploadImage();


    // -----------------------------------------------------
    // Wait for ACK
    // -----------------------------------------------------

    if (!readAck())
    {
        return false;
    }


    // -----------------------------------------------------
    // Tell Python that RAW capture starts
    // -----------------------------------------------------

    Serial.write('R');
    Serial.write('A');
    Serial.write('W');
    Serial.write('F');

    Serial.flush();


    // -----------------------------------------------------
    // Read AS608 packets
    // -----------------------------------------------------

    uint8_t packet[265];

    size_t packetSize;

    uint8_t packetType;

    uint32_t packetCount = 0;


    while (true)
    {
        if (!readCompletePacket(
            packet,
            packetSize,
            packetType
        ))
        {
            return false;
        }


        // -------------------------------------------------
        // Send complete packet unchanged
        // -------------------------------------------------

        Serial.write(
            packet,
            packetSize
        );

        Serial.flush();


        packetCount++;


        // -------------------------------------------------
        // End packet
        // -------------------------------------------------

        if (packetType == PACKET_END)
        {
            break;
        }


        // -------------------------------------------------
        // Only image data packets are expected
        // -------------------------------------------------

        if (packetType != PACKET_DATA)
        {
            return false;
        }
    }


    Serial.flush();

    return true;
}


// =========================================================
// Setup
// =========================================================

void setup()
{
    Serial.begin(115200);

    FingerSerial.begin(
        57600,
        SERIAL_8N1,
        AS608_RX,
        AS608_TX
    );

    delay(1000);

    finger.begin(57600);

    if (!finger.verifyPassword())
    {
        while (true)
        {
            delay(1000);
        }
    }
}


// =========================================================
// Main loop
// =========================================================

void loop()
{
    uint8_t result =
        finger.getImage();


    if (result == FINGERPRINT_OK)
    {
        bool success =
            dumpImage();


        // Wait until finger removed

        while (
            finger.getImage()
            == FINGERPRINT_OK
        )
        {
            delay(100);
        }
    }


    delay(100);
}
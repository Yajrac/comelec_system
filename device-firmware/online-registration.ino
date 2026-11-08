#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <WiFiManager.h>
#include <ArduinoJson.h>
#include <Adafruit_Fingerprint.h>
#include <LiquidCrystal_I2C.h>
#include <Wire.h>
#include <vector>
#include <cstring>

// =========================================================
// LCD CONFIGURATION
// =========================================================

#define LCD_SDA       21
#define LCD_SCL       22
#define LCD_ADDRESS   0x27
#define LCD_COLUMNS   16
#define LCD_ROWS      2

LiquidCrystal_I2C lcd(LCD_ADDRESS, LCD_COLUMNS, LCD_ROWS);

void showStatus(String line1, String line2 = "") {
  if (line1.length() > LCD_COLUMNS) {
    line1 = line1.substring(0, LCD_COLUMNS);
  }

  if (line2.length() > LCD_COLUMNS) {
    line2 = line2.substring(0, LCD_COLUMNS);
  }

  lcd.setCursor(0, 0);
  lcd.print("                ");
  lcd.setCursor(0, 0);
  lcd.print(line1);

  lcd.setCursor(0, 1);
  lcd.print("                ");
  lcd.setCursor(0, 1);
  lcd.print(line2);
}

void initializeLCD() {
  Wire.begin(LCD_SDA, LCD_SCL);
  lcd.init();
  lcd.backlight();
  lcd.clear();

  showStatus("Pio Duran", "Starting device");
  delay(1500);
}

// =========================================================
// WIFIMANAGER
// =========================================================

WiFiManager wifiManager;

const char* PORTAL_NAME = "PioDuran-AS608-Setup";

bool connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  showStatus("WiFi setup", "Connect portal");

  Serial.println();
  Serial.println("Starting WiFiManager portal...");
  Serial.printf("Portal name: %s\n", PORTAL_NAME);

  WiFi.mode(WIFI_STA);

  wifiManager.setConnectTimeout(30);
  wifiManager.setConfigPortalTimeout(180);

  bool connected = wifiManager.autoConnect(PORTAL_NAME);

  if (!connected || WiFi.status() != WL_CONNECTED) {
    Serial.println("ERROR: Wi-Fi connection failed.");
    showStatus("WiFi failed", "Restart device");
    return false;
  }

  Serial.println("Wi-Fi connected.");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());

  Serial.print("Gateway: ");
  Serial.println(WiFi.gatewayIP());

  showStatus("WiFi connected", WiFi.localIP().toString());
  delay(1500);

  return true;
}

// =========================================================
// DJANGO API CONFIGURATION
// =========================================================

const char* IMAGE_API_BASE =
  "https://pioduranvoterregistration.com/comelec/api/";

const char* DEVICE_API_BASE =
  "https://pioduranvoterregistration.com/comelec/api/device/";

// Leave empty if authentication is not required.
// If using DRF TokenAuthentication, provide the token here.
const char* DEVICE_TOKEN = "";

// =========================================================
// AS608 SENSOR
//
// AS608 TX -> ESP32 GPIO16 (RX2)
// AS608 RX -> ESP32 GPIO17 (TX2)
// GND      -> ESP32 GND
// =========================================================

const int RX_PIN = 16;
const int TX_PIN = 17;

const uint32_t SENSOR_BAUD = 19200;

HardwareSerial fingerSerial(2);
Adafruit_Fingerprint finger(&fingerSerial);

bool sensorReady = false;

// =========================================================
// SENSOR PACKET CONFIGURATION
// =========================================================

#define PACKET_COMMAND 0x01
#define PACKET_DATA    0x02
#define PACKET_ACK     0x07
#define PACKET_END     0x08

#define CMD_UPLOAD_CHAR  0x08
#define CMD_UPLOAD_IMAGE 0x0A

const uint8_t SENSOR_ADDRESS[4] = {
  0xFF, 0xFF, 0xFF, 0xFF
};

const uint32_t PACKET_TIMEOUT_MS = 7000;
const size_t MAX_PACKET_LENGTH = 256;
const size_t MAX_TEMPLATE_SIZE = 1024;

const size_t IMAGE_WIDTH = 256;
const size_t IMAGE_HEIGHT = 288;
const size_t RAW_IMAGE_SIZE =
  IMAGE_WIDTH * IMAGE_HEIGHT / 2;

uint8_t rawImage[RAW_IMAGE_SIZE];

// =========================================================
// HTTP HELPERS
// =========================================================

// Testing configuration.
// Replace setInsecure() with certificate validation for production.
bool beginHttpRequest(
  HTTPClient& http,
  WiFiClientSecure& client,
  const String& url
) {
  client.setInsecure();
  client.setTimeout(60000);

  http.setConnectTimeout(15000);
  http.setTimeout(60000);
  http.setReuse(false);

  Serial.println("Request URL: " + url);

  if (!http.begin(client, url)) {
    Serial.println("ERROR: HTTP begin failed.");
    return false;
  }

  return true;
}

void addAuthHeader(HTTPClient& http) {
  if (strlen(DEVICE_TOKEN) > 0) {
    http.addHeader(
      "Authorization",
      String("Token ") + DEVICE_TOKEN
    );
  }
}

void printHttpError(int status) {
  if (status < 0) {
    Serial.print("HTTP error: ");
    Serial.println(HTTPClient::errorToString(status));
  }
}

// =========================================================
// SENSOR PACKET READER
// =========================================================

bool readSensorPacket(
  uint8_t& packetType,
  uint8_t* payload,
  size_t payloadCapacity,
  size_t& payloadLength,
  uint32_t timeoutMs = PACKET_TIMEOUT_MS
) {
  payloadLength = 0;

  unsigned long started = millis();
  uint8_t headerState = 0;

  // Find packet header EF 01.
  while (millis() - started < timeoutMs) {
    if (!fingerSerial.available()) {
      delay(1);
      continue;
    }

    uint8_t value = fingerSerial.read();

    if (headerState == 0) {
      if (value == 0xEF) {
        headerState = 1;
      }
    } else if (value == 0x01) {
      headerState = 2;
      break;
    } else {
      headerState = (value == 0xEF) ? 1 : 0;
    }
  }

  if (headerState != 2) {
    Serial.println("ERROR: Sensor packet header timeout.");
    return false;
  }

  // Address[4], packet type, length[2].
  uint8_t header[7];
  size_t headerRead = 0;

  while (
    headerRead < sizeof(header) &&
    millis() - started < timeoutMs
  ) {
    if (fingerSerial.available()) {
      header[headerRead++] = fingerSerial.read();
    } else {
      delay(1);
    }
  }

  if (headerRead != sizeof(header)) {
    Serial.println("ERROR: Incomplete packet header.");
    return false;
  }

  packetType = header[4];

  uint16_t packetLength =
    ((uint16_t)header[5] << 8) | header[6];

  if (
    packetLength < 2 ||
    packetLength > MAX_PACKET_LENGTH - 9
  ) {
    Serial.printf(
      "ERROR: Invalid packet length: %u\n",
      packetLength
    );
    return false;
  }

  size_t dataLength = packetLength - 2;

  if (dataLength > payloadCapacity) {
    Serial.println("ERROR: Payload exceeds buffer.");
    return false;
  }

  uint16_t checksum =
    packetType + header[5] + header[6];

  size_t received = 0;

  while (
    received < dataLength &&
    millis() - started < timeoutMs
  ) {
    if (fingerSerial.available()) {
      uint8_t value = fingerSerial.read();
      payload[received++] = value;
      checksum += value;
    } else {
      delay(1);
    }
  }

  if (received != dataLength) {
    Serial.println("ERROR: Sensor payload timeout.");
    return false;
  }

  uint8_t checksumBytes[2];
  size_t checksumRead = 0;

  while (
    checksumRead < 2 &&
    millis() - started < timeoutMs
  ) {
    if (fingerSerial.available()) {
      checksumBytes[checksumRead++] = fingerSerial.read();
    } else {
      delay(1);
    }
  }

  if (checksumRead != 2) {
    Serial.println("ERROR: Missing sensor checksum.");
    return false;
  }

  uint16_t receivedChecksum =
    ((uint16_t)checksumBytes[0] << 8) |
    checksumBytes[1];

  if (checksum != receivedChecksum) {
    Serial.printf(
      "ERROR: Checksum mismatch: calculated=%04X received=%04X\n",
      checksum,
      receivedChecksum
    );
    return false;
  }

  payloadLength = dataLength;
  return true;
}

// =========================================================
// SEND SENSOR COMMAND
// =========================================================

bool sendCommand(
  uint8_t command,
  const uint8_t* parameters,
  size_t parameterLength
) {
  if (parameterLength > 32) {
    return false;
  }

  uint8_t packet[48];
  size_t index = 0;

  packet[index++] = 0xEF;
  packet[index++] = 0x01;

  for (int i = 0; i < 4; i++) {
    packet[index++] = SENSOR_ADDRESS[i];
  }

  packet[index++] = PACKET_COMMAND;

  uint16_t length = parameterLength + 3;

  packet[index++] = length >> 8;
  packet[index++] = length & 0xFF;
  packet[index++] = command;

  uint16_t checksum =
    PACKET_COMMAND +
    (length >> 8) +
    (length & 0xFF) +
    command;

  for (size_t i = 0; i < parameterLength; i++) {
    packet[index++] = parameters[i];
    checksum += parameters[i];
  }

  packet[index++] = checksum >> 8;
  packet[index++] = checksum & 0xFF;

  while (fingerSerial.available()) {
    fingerSerial.read();
  }

  size_t written = fingerSerial.write(packet, index);
  fingerSerial.flush();

  return written == index;
}

// =========================================================
// SENSOR ACKNOWLEDGMENT
// =========================================================

bool readAck(uint8_t& confirmationCode) {
  uint8_t payload[32];
  size_t length = 0;
  uint8_t type = 0;

  if (!readSensorPacket(
        type,
        payload,
        sizeof(payload),
        length
      )) {
    return false;
  }

  if (type != PACKET_ACK || length < 1) {
    Serial.printf(
      "ERROR: Expected ACK, received 0x%02X\n",
      type
    );
    return false;
  }

  confirmationCode = payload[0];

  Serial.printf(
    "Sensor confirmation: 0x%02X\n",
    confirmationCode
  );

  return confirmationCode == 0;
}

// =========================================================
// RECEIVE RAW FINGERPRINT IMAGE
// =========================================================

bool receiveFingerprintImage(size_t& receivedBytes) {
  receivedBytes = 0;
  memset(rawImage, 0, sizeof(rawImage));

  Serial.println("Requesting raw fingerprint image...");
  showStatus("Reading image", "Please wait...");

  if (!sendCommand(CMD_UPLOAD_IMAGE, nullptr, 0)) {
    return false;
  }

  uint8_t confirmationCode = 0;

  if (!readAck(confirmationCode)) {
    Serial.println("ERROR: Image command rejected.");
    return false;
  }

  unsigned long started = millis();
  size_t packets = 0;
  bool endReceived = false;

  while (millis() - started < 60000) {
    uint8_t type = 0;
    uint8_t payload[MAX_PACKET_LENGTH];
    size_t length = 0;

    if (!readSensorPacket(
          type,
          payload,
          sizeof(payload),
          length
        )) {
      Serial.println("ERROR: Failed to read image packet.");
      return false;
    }

    if (type != PACKET_DATA && type != PACKET_END) {
      Serial.printf(
        "Unexpected image packet: 0x%02X\n",
        type
      );
      return false;
    }

    if (receivedBytes + length > sizeof(rawImage)) {
      Serial.println("ERROR: Image exceeds buffer size.");
      return false;
    }

    memcpy(rawImage + receivedBytes, payload, length);
    receivedBytes += length;
    packets++;

    if (packets % 20 == 0) {
      Serial.printf(
        "Image progress: %u / %u bytes\n",
        (unsigned)receivedBytes,
        (unsigned)RAW_IMAGE_SIZE
      );
    }

    if (type == PACKET_END) {
      endReceived = true;
      break;
    }
  }

  Serial.printf(
    "Image transfer: %u bytes in %u packets\n",
    (unsigned)receivedBytes,
    (unsigned)packets
  );

  if (
    !endReceived ||
    receivedBytes != RAW_IMAGE_SIZE
  ) {
    Serial.println("ERROR: Incomplete raw fingerprint image.");
    return false;
  }

  return true;
}

// =========================================================
// BMP HELPERS
// =========================================================

void putLE16(uint8_t* p, uint16_t value) {
  p[0] = value & 0xFF;
  p[1] = (value >> 8) & 0xFF;
}

void putLE32(uint8_t* p, uint32_t value) {
  p[0] = value & 0xFF;
  p[1] = (value >> 8) & 0xFF;
  p[2] = (value >> 16) & 0xFF;
  p[3] = (value >> 24) & 0xFF;
}

bool createFingerprintBMP(std::vector<uint8_t>& bmp) {
  const size_t headerSize = 14 + 40 + 256 * 4;
  const size_t rowSize = IMAGE_WIDTH;
  const size_t pixelSize = rowSize * IMAGE_HEIGHT;
  const size_t totalSize = headerSize + pixelSize;

  Serial.printf(
    "Free heap before BMP generation: %u bytes\n",
    (unsigned)ESP.getFreeHeap()
  );

  bmp.clear();

  if (ESP.getFreeHeap() < totalSize + 20000) {
    Serial.println("ERROR: Insufficient heap for BMP.");
    showStatus("Memory error", "BMP creation");
    return false;
  }

  bmp.resize(totalSize, 0);

  // BMP file header.
  bmp[0] = 'B';
  bmp[1] = 'M';
  putLE32(&bmp[2], totalSize);
  putLE32(&bmp[10], headerSize);

  // BITMAPINFOHEADER.
  putLE32(&bmp[14], 40);
  putLE32(&bmp[18], IMAGE_WIDTH);
  putLE32(&bmp[22], IMAGE_HEIGHT);
  putLE16(&bmp[26], 1);
  putLE16(&bmp[28], 8);
  putLE32(&bmp[30], 0);
  putLE32(&bmp[34], pixelSize);
  putLE32(&bmp[38], 2835);
  putLE32(&bmp[42], 2835);
  putLE32(&bmp[46], 256);
  putLE32(&bmp[50], 256);

  // Grayscale palette.
  for (uint16_t i = 0; i < 256; i++) {
    size_t pos = 54 + i * 4;

    bmp[pos] = i;
    bmp[pos + 1] = i;
    bmp[pos + 2] = i;
    bmp[pos + 3] = 0;
  }

  // Expand packed 4-bit pixels into 8-bit grayscale.
  for (size_t y = 0; y < IMAGE_HEIGHT; y++) {
    size_t sourceY = IMAGE_HEIGHT - 1 - y;
    size_t destinationRow = headerSize + y * rowSize;

    for (size_t x = 0; x < IMAGE_WIDTH; x++) {
      size_t pixelIndex = sourceY * IMAGE_WIDTH + x;
      uint8_t packed = rawImage[pixelIndex / 2];

      uint8_t pixel4 = (pixelIndex & 1)
        ? (packed & 0x0F)
        : ((packed >> 4) & 0x0F);

      bmp[destinationRow + x] = pixel4 * 17;
    }
  }

  Serial.printf(
    "BMP generated: %u bytes (%u x %u)\n",
    (unsigned)bmp.size(),
    (unsigned)IMAGE_WIDTH,
    (unsigned)IMAGE_HEIGHT
  );

  return true;
}

// =========================================================
// STREAM BMP IMAGE TO DJANGO
// Avoids creating a second complete multipart body in RAM.
// =========================================================

bool uploadFingerprintImage(
  int applicantId,
  const String& fingerName
) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("ERROR: Wi-Fi is disconnected.");
    return false;
  }

  std::vector<uint8_t> bmp;

  if (!createFingerprintBMP(bmp)) {
    return false;
  }

  const char* host =
  "pioduranvoterregistration.com";

  const uint16_t port = 443;

  String boundary =
    "----ESP32Boundary" + String(millis());

  String filename =
    "applicant_" + String(applicantId) +
    "_" + fingerName + "_fingerprint.bmp";

  String path =
    "/comelec/api/applicants/" +
    String(applicantId) +
    "/fingerprint/";

  String partHeader =
    "--" + boundary + "\r\n"
    "Content-Disposition: form-data; name=\"finger\"\r\n\r\n" +
    fingerName + "\r\n" +
    "--" + boundary + "\r\n"
    "Content-Disposition: form-data; name=\"fingerprint\"; filename=\"" +
    filename + "\"\r\n"
    "Content-Type: image/bmp\r\n\r\n";

  String partFooter =
    "\r\n--" + boundary + "--\r\n";

  size_t contentLength =
    partHeader.length() +
    bmp.size() +
    partFooter.length();

  Serial.println();
  Serial.println("======================================");
  Serial.println("STREAMING FINGERPRINT IMAGE");
  Serial.println("======================================");
  Serial.println("Path: " + path);
  Serial.printf("BMP bytes: %u\n", (unsigned)bmp.size());
  Serial.printf(
    "Multipart bytes: %u\n",
    (unsigned)contentLength
  );

  WiFiClientSecure client;
  client.setInsecure();  // Testing only; validate TLS in production.
  client.setTimeout(60000);

  if (!client.connect(host, port)) {
    Serial.println("ERROR: HTTPS connection failed.");
    bmp.clear();
    std::vector<uint8_t>().swap(bmp);
    showStatus("HTTPS failed", "Check connection");
    return false;
  }

  // Send HTTP request headers.
  client.print("POST ");
  client.print(path);
  client.print(" HTTP/1.1\r\n");

  client.print("Host: ");
  client.print(host);
  client.print("\r\n");

  client.print("Content-Type: multipart/form-data; boundary=");
  client.print(boundary);
  client.print("\r\n");

  client.print("Content-Length: ");
  client.print(String((unsigned long)contentLength));
  client.print("\r\n");

  client.print("Connection: close\r\n");

  if (strlen(DEVICE_TOKEN) > 0) {
    client.print("Authorization: Token ");
    client.print(DEVICE_TOKEN);
    client.print("\r\n");
  }

  client.print("\r\n");

  showStatus("Uploading image", "Please wait...");

  if (client.print(partHeader) != partHeader.length()) {
    Serial.println("ERROR: Could not send multipart header.");
    client.stop();
    bmp.clear();
    std::vector<uint8_t>().swap(bmp);
    return false;
  }

  // Send the BMP in chunks.
  size_t offset = 0;
  const size_t CHUNK_SIZE = 1024;
  bool writeSuccess = true;

  while (offset < bmp.size()) {
    size_t chunkSize = bmp.size() - offset;

    if (chunkSize > CHUNK_SIZE) {
      chunkSize = CHUNK_SIZE;
    }

    size_t written = client.write(
      bmp.data() + offset,
      chunkSize
    );

    if (written == 0) {
      Serial.println("ERROR: Image streaming stopped.");
      writeSuccess = false;
      break;
    }

    offset += written;

    if (offset % 10240 < CHUNK_SIZE) {
      Serial.printf(
        "Upload progress: %u / %u bytes\n",
        (unsigned)offset,
        (unsigned)bmp.size()
      );
    }

    delay(1);
  }

  if (writeSuccess) {
    if (client.print(partFooter) != partFooter.length()) {
      Serial.println("ERROR: Multipart footer incomplete.");
      writeSuccess = false;
    }
  }

  bmp.clear();
  std::vector<uint8_t>().swap(bmp);

  Serial.printf(
    "Free heap after sending image: %u bytes\n",
    (unsigned)ESP.getFreeHeap()
  );

  if (!writeSuccess) {
    client.stop();
    showStatus("Upload interrupted", "Retry capture");
    return false;
  }

  // Read HTTP status line.
  unsigned long responseStarted = millis();

  while (
    client.connected() &&
    !client.available() &&
    millis() - responseStarted < 60000
  ) {
    delay(10);
  }

  if (!client.available()) {
    Serial.println("ERROR: Django did not return a response.");
    client.stop();
    showStatus("No server reply", "Check connection");
    return false;
  }

  String statusLine = client.readStringUntil('\n');
  statusLine.trim();

  Serial.println("Image response: " + statusLine);

  int statusCode = 0;
  int firstSpace = statusLine.indexOf(' ');

  if (firstSpace >= 0) {
    statusCode = statusLine.substring(firstSpace + 1).toInt();
  }

  // Consume response headers.
  while (client.connected() || client.available()) {
    String headerLine = client.readStringUntil('\n');

    if (headerLine == "\r" || headerLine.length() == 0) {
      break;
    }
  }

  String response;
  response.reserve(512);

  unsigned long bodyStarted = millis();

  while (millis() - bodyStarted < 10000) {
    while (client.available()) {
      char ch = (char)client.read();

      if (response.length() < 2000) {
        response += ch;
      }

      bodyStarted = millis();
    }

    if (!client.connected() && !client.available()) {
      break;
    }

    delay(5);
  }

  Serial.printf("Image HTTP status: %d\n", statusCode);
  Serial.println("Image response body:");
  Serial.println(response);

  client.stop();

  bool success = statusCode >= 200 && statusCode < 300;

  showStatus(
    success ? "Image uploaded" : "Image upload fail",
    success ? "Django saved" : "Check server"
  );

  return success;
}

// =========================================================
// RECEIVE FINGERPRINT TEMPLATE
// =========================================================

bool receiveFingerprintTemplate(
  uint8_t* output,
  size_t capacity,
  size_t& outputLength
) {
  outputLength = 0;

  const uint8_t parameters[] = { 0x01 };

  Serial.println("Requesting fingerprint template...");
  showStatus("Reading template", "Please wait...");

  if (!sendCommand(
        CMD_UPLOAD_CHAR,
        parameters,
        sizeof(parameters)
      )) {
    return false;
  }

  uint8_t confirmationCode = 0;

  if (!readAck(confirmationCode)) {
    Serial.println("Template upload command rejected.");
    return false;
  }

  unsigned long started = millis();

  while (millis() - started < 20000) {
    uint8_t type = 0;
    uint8_t payload[MAX_PACKET_LENGTH];
    size_t length = 0;

    if (!readSensorPacket(
          type,
          payload,
          sizeof(payload),
          length
        )) {
      return false;
    }

    if (type != PACKET_DATA && type != PACKET_END) {
      Serial.printf(
        "Unexpected template packet: 0x%02X\n",
        type
      );
      return false;
    }

    if (outputLength + length > capacity) {
      Serial.println("ERROR: Template exceeds buffer capacity.");
      return false;
    }

    memcpy(output + outputLength, payload, length);
    outputLength += length;

    if (type == PACKET_END) {
      Serial.printf(
        "Template received: %u bytes\n",
        (unsigned)outputLength
      );

      return outputLength > 0;
    }
  }

  Serial.println("ERROR: Template transfer timeout.");
  return false;
}

// =========================================================
// BASE64 ENCODING
// =========================================================

const char BASE64_TABLE[] =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
  "abcdefghijklmnopqrstuvwxyz"
  "0123456789+/";

String encodeBase64(
  const uint8_t* data,
  size_t length
) {
  String output;
  output.reserve(((length + 2) / 3) * 4);

  for (size_t i = 0; i < length; i += 3) {
    uint32_t value = (uint32_t)data[i] << 16;

    if (i + 1 < length) {
      value |= (uint32_t)data[i + 1] << 8;
    }

    if (i + 2 < length) {
      value |= data[i + 2];
    }

    output += BASE64_TABLE[(value >> 18) & 0x3F];
    output += BASE64_TABLE[(value >> 12) & 0x3F];

    output += i + 1 < length
      ? BASE64_TABLE[(value >> 6) & 0x3F]
      : '=';

    output += i + 2 < length
      ? BASE64_TABLE[value & 0x3F]
      : '=';
  }

  return output;
}

// =========================================================
// UPLOAD TEMPLATE TO DJANGO
// =========================================================

bool uploadFingerprintTemplate(
  int applicantId,
  const String& fingerName,
  const uint8_t* data,
  size_t length
) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  String url =
    String(DEVICE_API_BASE) +
    "applicants/" + String(applicantId) +
    "/fingerprint/";

  WiFiClientSecure client;
  HTTPClient http;

  if (!beginHttpRequest(http, client, url)) {
    return false;
  }

  addAuthHeader(http);
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["finger"] = fingerName;
  doc["template"] = encodeBase64(data, length);

  String body;
  serializeJson(doc, body);

  showStatus("Uploading template", "Please wait...");

  Serial.printf(
    "Uploading template: %u bytes\n",
    (unsigned)length
  );

  int status = http.POST(body);
  String response = http.getString();

  Serial.printf("Template HTTP status: %d\n", status);
  Serial.println(response);

  if (status < 0) {
    printHttpError(status);
  }

  http.end();

  bool success = status >= 200 && status < 300;

  showStatus(
    success ? "Template saved" : "Template failed",
    success ? "Django saved" : "Check API"
  );

  return success;
}

// =========================================================
// CAPTURE IMAGE AND TEMPLATE
// =========================================================

bool captureFingerprintTemplate(
  int applicantId,
  const String& fingerName
) {
  Serial.println();
  Serial.println("======================================");
  Serial.printf("Applicant ID: %d\n", applicantId);
  Serial.printf("Finger: %s\n", fingerName.c_str());
  Serial.println("Place your finger on the sensor.");
  Serial.println("======================================");

  showStatus(
    "Applicant " + String(applicantId),
    fingerName + " finger"
  );

  delay(1000);

  showStatus("Place your finger", "Hold it steady");

  unsigned long started = millis();
  uint8_t imageResult = FINGERPRINT_NOFINGER;

  while (millis() - started < 20000) {
    imageResult = finger.getImage();

    if (imageResult == FINGERPRINT_OK) {
      Serial.println("Fingerprint image captured.");
      break;
    }

    if (
      imageResult != FINGERPRINT_NOFINGER &&
      imageResult != FINGERPRINT_PACKETRECIEVEERR
    ) {
      Serial.printf(
        "getImage error: 0x%02X\n",
        imageResult
      );
    }

    delay(200);
  }

  if (imageResult != FINGERPRINT_OK) {
    Serial.println("ERROR: Fingerprint capture timed out.");
    showStatus("No finger detected", "Try again");
    return false;
  }

  showStatus("Finger detected", "Reading image");

  size_t receivedBytes = 0;

  bool imageReceived =
    receiveFingerprintImage(receivedBytes);

  bool imageSaved = false;

  if (imageReceived) {
    imageSaved = uploadFingerprintImage(
      applicantId,
      fingerName
    );
  } else {
    Serial.println("ERROR: Could not retrieve raw image.");
    showStatus("Image read failed", "Check sensor");
  }

  // Convert the captured fingerprint into character data.
  uint8_t conversionResult = finger.image2Tz(1);

  if (conversionResult != FINGERPRINT_OK) {
    Serial.printf(
      "ERROR: image2Tz failed: 0x%02X\n",
      conversionResult
    );

    showStatus("Feature error", "Try again");
    return false;
  }

  uint8_t templateData[MAX_TEMPLATE_SIZE];
  size_t templateLength = 0;

  bool templateReceived = receiveFingerprintTemplate(
    templateData,
    sizeof(templateData),
    templateLength
  );

  bool templateSaved = false;

  if (templateReceived) {
    templateSaved = uploadFingerprintTemplate(
      applicantId,
      fingerName,
      templateData,
      templateLength
    );
  } else {
    Serial.println("ERROR: Could not retrieve template.");
    showStatus("Template error", "Check sensor");
  }

  Serial.println();
  Serial.println("----------- CAPTURE RESULTS -----------");
  Serial.printf(
    "Raw image bytes: %u\n",
    (unsigned)receivedBytes
  );
  Serial.printf(
    "BMP uploaded: %s\n",
    imageSaved ? "YES" : "NO"
  );
  Serial.printf(
    "Template uploaded: %s\n",
    templateSaved ? "YES" : "NO"
  );
  Serial.println("---------------------------------------");

  bool success = imageSaved && templateSaved;

  if (success) {
    showStatus("Capture complete", "Upload successful");
  } else {
    showStatus("Capture failed", "Check Serial");
  }

  delay(1500);

  return success;
}

// =========================================================
// POLL DJANGO FOR A CAPTURE REQUEST
// =========================================================

bool getNextCaptureRequest(
  int& requestId,
  int& applicantId,
  String& fingerName
) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  String url =
    String(DEVICE_API_BASE) + "fingerprint/next/";

  WiFiClientSecure client;
  HTTPClient http;

  if (!beginHttpRequest(http, client, url)) {
    return false;
  }

  addAuthHeader(http);

  int status = http.GET();

  if (status != 200) {
    if (status != 204) {
      Serial.printf("Poll HTTP status: %d\n", status);

      if (status < 0) {
        printHttpError(status);
      } else {
        Serial.println(http.getString());
      }
    }

    http.end();
    return false;
  }

  String response = http.getString();
  http.end();

  Serial.println("Poll response: " + response);

  JsonDocument doc;
  DeserializationError error =
    deserializeJson(doc, response);

  if (error) {
    Serial.print("Poll JSON error: ");
    Serial.println(error.c_str());
    return false;
  }

  String command = doc["command"] | "";

  if (command.isEmpty()) {
    return false;
  }

  if (
    command != "capture" ||
    doc["request_id"].isNull() ||
    doc["applicant_id"].isNull() ||
    doc["finger"].isNull()
  ) {
    Serial.println("ERROR: Invalid capture request.");
    return false;
  }

  requestId = doc["request_id"].as<int>();
  applicantId = doc["applicant_id"].as<int>();
  fingerName = doc["finger"].as<String>();
  fingerName.toLowerCase();

  return requestId > 0 &&
         applicantId > 0 &&
         (fingerName == "left" || fingerName == "right");
}

// =========================================================
// REPORT COMPLETION TO DJANGO
// =========================================================

void reportCaptureCompletion(
  int requestId,
  bool success,
  const String& message
) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(
      "ERROR: Cannot report completion; Wi-Fi disconnected."
    );
    showStatus("No WiFi", "Result not sent");
    return;
  }

  String url =
    String(DEVICE_API_BASE) + "fingerprint/complete/";

  WiFiClientSecure client;
  HTTPClient http;

  if (!beginHttpRequest(http, client, url)) {
    return;
  }

  addAuthHeader(http);
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["request_id"] = requestId;
  doc["success"] = success;
  doc["message"] = message;

  String body;
  serializeJson(doc, body);

  showStatus("Reporting result", "To Django");

  int status = http.POST(body);
  String response = http.getString();

  Serial.printf(
    "Completion HTTP status: %d\n",
    status
  );
  Serial.println(response);

  if (status < 0) {
    printHttpError(status);
  }

  http.end();

  if (status >= 200 && status < 300) {
    showStatus(
      "Result reported",
      success ? "Success" : "Failed"
    );
  } else {
    showStatus("Report failed", "Check server");
  }

  delay(1000);
}

// =========================================================
// SETUP
// =========================================================

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("======================================");
  Serial.println("Pio Duran Registration");
  Serial.println("ESP32 + AS608 + LCD");
  Serial.println("======================================");

  initializeLCD();

  // Start AS608 UART2.
  showStatus("Checking AS608", "Please wait...");

  fingerSerial.begin(
    SENSOR_BAUD,
    SERIAL_8N1,
    RX_PIN,
    TX_PIN
  );

  finger.begin(SENSOR_BAUD);
  delay(500);

  if (finger.verifyPassword()) {
    sensorReady = true;

    Serial.println("AS608 fingerprint sensor detected.");
    showStatus("AS608 connected", "Sensor ready");
  } else {
    sensorReady = false;

    Serial.println("ERROR: Fingerprint sensor not detected.");
    Serial.println(
      "Check sensor power, TX/RX wiring and baud rate."
    );

    showStatus("AS608 ERROR", "Check UART/baud");
  }

  delay(1500);

  connectWiFi();

  if (!sensorReady) {
    showStatus("AS608 ERROR", "Fix sensor first");
  } else if (WiFi.status() == WL_CONNECTED) {
    showStatus("Pio Duran", "Waiting for task");
  }
}

// =========================================================
// MAIN LOOP
// =========================================================

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    showStatus("WiFi disconnected", "Reconnecting...");
    Serial.println("Wi-Fi disconnected. Reconnecting...");

    connectWiFi();
    delay(1000);
    return;
  }

  if (!sensorReady) {
    showStatus("AS608 ERROR", "Check sensor");
    delay(3000);
    return;
  }

  int requestId = 0;
  int applicantId = 0;
  String fingerName;

  if (!getNextCaptureRequest(
        requestId,
        applicantId,
        fingerName
      )) {
    showStatus("Pio Duran", "Waiting for task");
    delay(3000);
    return;
  }

  Serial.println();
  Serial.println("======================================");
  Serial.println("NEW FINGERPRINT REQUEST");
  Serial.printf("Request ID: %d\n", requestId);
  Serial.printf("Applicant ID: %d\n", applicantId);
  Serial.printf("Finger: %s\n", fingerName.c_str());
  Serial.println("======================================");

  showStatus(
    "Applicant " + String(applicantId),
    fingerName + " finger"
  );

  bool success = captureFingerprintTemplate(
    applicantId,
    fingerName
  );

  String message = success
    ? "Fingerprint image and template uploaded."
    : "Fingerprint image or template upload failed.";

  reportCaptureCompletion(
    requestId,
    success,
    message
  );

  showStatus("Pio Duran", "Waiting for task");
  delay(2000);
}
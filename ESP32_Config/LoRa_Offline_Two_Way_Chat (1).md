# LoRa Offline Two-Way Messaging System

### (ESP32 + SX1278 + Wired Mobile Connection)

------------------------------------------------------------------------

## 📌 Project Overview

This project implements a **fully offline two-way messaging system**
using:

-   ESP32 microcontrollers\
-   SX1278 (RA-01) LoRa modules (433 MHz)\
-   Android mobile devices\
-   USB OTG wired serial communication

No WiFi, No Bluetooth, No Internet required.

------------------------------------------------------------------------

## 🏗 System Architecture

    Phone 1
       │ USB (OTG)
    ESP32 + SX1278  ←────── LoRa 433MHz ──────→  ESP32 + SX1278
       │ USB (OTG)
    Phone 2

------------------------------------------------------------------------

## 🔁 Communication Flow

### Sending from Device 1 → Device 2

1.  User types message on Phone 1
2.  Message sent via USB Serial to ESP32 Node 1
3.  Node 1 transmits message via LoRa
4.  Node 2 receives LoRa message
5.  Node 2 sends message via USB Serial
6.  Phone 2 displays the message

### Sending from Device 2 → Device 1

Same process in reverse direction.

------------------------------------------------------------------------

## 🧰 Hardware Requirements (Per Node)

-   ESP32 development board
-   SX1278 (RA-01) LoRa module
-   Antenna (must be attached)
-   USB cable
-   USB OTG adapter (for phone)
-   Stable 3.3V power supply

------------------------------------------------------------------------

## 🔌 SX1278 to ESP32 Wiring

  SX1278 Pin   ESP32 Pin
  ------------ -----------
  VCC          3.3V
  GND          GND
  SCK          GPIO18
  MISO         GPIO19
  MOSI         GPIO23
  NSS          GPIO5
  RST          GPIO14
  DIO0         GPIO2

⚠️ Important:\
- Use **3.3V only**\
- Never connect to 5V\
- Always attach antenna before transmitting

------------------------------------------------------------------------

## 📡 LoRa Configuration

-   Frequency: `433E6`
-   Mode: Half-Duplex
-   Same configuration required on both nodes

------------------------------------------------------------------------

## 💻 ESP32 Firmware (Upload to BOTH Boards)

``` cpp
#include <SPI.h>
#include <LoRa.h>

#define SS 5
#define RST 14
#define DIO0 2

void setup() {
  Serial.begin(115200);   // USB Serial to phone

  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(433E6)) {
    while (1);
  }
}

void loop() {

  // If message comes from phone via USB
  if (Serial.available()) {
    String message = Serial.readStringUntil('\n');

    LoRa.beginPacket();
    LoRa.print(message);
    LoRa.endPacket();
  }

  // If message comes from LoRa
  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String incoming = "";

    while (LoRa.available()) {
      incoming += (char)LoRa.read();
    }

    Serial.println(incoming);  // Send to phone
  }
}
```

------------------------------------------------------------------------

## 📱 Mobile Application Requirements

The Android app must:

-   Detect USB device
-   Open serial port (115200 baud)
-   Send text ending with newline `\n`
-   Continuously listen for incoming serial data
-   Display received messages

Recommended library (Android Studio):

-   usb-serial-for-android

------------------------------------------------------------------------

## ⚙️ Operating Procedure

### Setup

1.  Wire SX1278 to ESP32
2.  Upload firmware to both ESP32 boards
3.  Connect each ESP32 to a phone using USB OTG
4.  Open mobile app on both devices
5.  Connect to USB serial device

### Testing

1.  Type message on Phone 1
2.  Press Send
3.  Verify message appears on Phone 2
4.  Repeat in reverse direction

------------------------------------------------------------------------

## 📏 Expected Performance

  -----------------------------------------------------------------------
  Feature                        Description
  ------------------------------ ----------------------------------------
  Range                          Up to several kilometers (depending on
                                 antenna and environment)

  Internet Required              No

  Bluetooth Required             No

  Communication Type             Two-way

  LoRa Mode                      Half-duplex

  Power Consumption              Low
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## ⚠️ Important Notes

-   Both nodes must use same LoRa frequency
-   Use proper antenna for long range
-   Ensure stable power supply
-   Phone must support USB OTG
-   Test at short distance before long-range deployment

------------------------------------------------------------------------

## 🚀 Future Improvements

-   Add sender ID tagging
-   Add message acknowledgment
-   Add AES encryption
-   Add message timestamps
-   Add channel filtering
-   Implement full chat UI with message history

------------------------------------------------------------------------

## 📚 Summary

This system provides:

-   Fully offline communication
-   Long-range wireless transmission
-   Wired stable phone interface
-   Two-way messaging capability
-   Simple and scalable architecture

------------------------------------------------------------------------

**Project Type:** Offline LoRa Chat System\
**Frequency:** 433 MHz\
**Microcontroller:** ESP32\
**Radio Module:** SX1278 (RA-01)

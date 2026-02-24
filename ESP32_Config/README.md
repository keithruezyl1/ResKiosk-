# LoRa Offline Two-Way Chat System

A fully offline two-way messaging system using ESP32 microcontrollers and SX1278 LoRa modules. Communicate between two phones without WiFi or Internet, using either USB OTG or Bluetooth Classic (SPP).

## System Architecture

```
Phone 1                                            Phone 2
   │                                                  │
   │ USB OTG or Bluetooth SPP        USB OTG or Bluetooth SPP
   ▼                                                  ▼
┌─────────────────┐             LoRa 433MHz        ┌─────────────────┐
│ ESP32 + SX1278  │ ◄────────────────────────────► │ ESP32 + SX1278  │
│    (Node 1)     │                                │    (Node 2)     │
└─────────────────┘                                └─────────────────┘
```

## Hardware Requirements (Per Node)

| Component | Description |
|-----------|-------------|
| ESP32 | Development board (e.g., ESP32-DevKitC) |
| SX1278 | RA-01 LoRa module (433 MHz) |
| Antenna | 433 MHz antenna (MUST be attached before powering on) |
| USB Cable | For programming and phone connection |
| USB OTG Adapter | To connect ESP32 to Android phone |

## Wiring Diagram

Connect the SX1278 module to your ESP32:

| SX1278 Pin | ESP32 Pin |
|------------|-----------|
| VCC | 3.3V |
| GND | GND |
| SCK | GPIO18 |
| MISO | GPIO19 |
| MOSI | GPIO23 |
| NSS | GPIO5 |
| RST | GPIO14 |
| DIO0 | GPIO2 |

> **Warning**: Use 3.3V only. Never connect VCC to 5V or you will damage the module.

> **Warning**: Always attach the antenna before powering on the module.

## Firmware Setup

### Prerequisites

- [PlatformIO](https://platformio.org/) installed (VS Code extension or CLI)

### Build and Upload

1. Clone or download this project
2. Open the project folder in VS Code with PlatformIO
3. Connect your ESP32 via USB
4. Build and upload:

```bash
pio run --target upload
```

5. Verify the upload by opening the serial monitor:

```bash
pio device monitor
```

You should see:
```
LoRa Two-Way Chat
Initializing...
LoRa initialized successfully!
Ready to send and receive messages.
-----------------------------------
```

6. **Repeat for the second ESP32 board**

## Mobile App Setup (Android)

You can connect to the ESP32 in two ways:
- USB Serial (via OTG cable)
- Bluetooth Classic Serial (SPP)

### Recommended App

**Serial USB Terminal** by Kai Morich (Free on Google Play Store)

[Download from Play Store](https://play.google.com/store/apps/details?id=de.kai_morich.serial_usb_terminal)

### App Configuration

1. Install the app on your Android phone
2. Open the app
3. Go to **Settings** (three dots menu → Settings)
4. Configure the following:
   - **Baud rate**: `115200`
   - **Data bits**: `8`
   - **Parity**: `None`
   - **Stop bits**: `1`
   - **Newline**: `CR+LF` or `LF` (send newline after each message)

### Alternative Apps

- **USB Serial Console** by Felipe Herranz
- **Serial Monitor** by DevTools
- **Serial Bluetooth Terminal** by Kai Morich (for Bluetooth SPP mode)

## Step-by-Step Usage Guide

### Initial Setup (Both Devices)

1. **Wire the hardware**: Connect SX1278 to ESP32 according to the wiring diagram
2. **Upload firmware**: Flash the firmware to both ESP32 boards
3. **Attach antenna**: Ensure 433 MHz antenna is connected to each SX1278

### Connecting Phone to ESP32 (USB OTG)

1. Connect the ESP32 to your Android phone using a **USB OTG adapter**
2. When prompted, allow the Serial USB Terminal app to access the USB device
3. Open the Serial USB Terminal app
4. Tap the **Connect** icon (plug symbol) in the toolbar
5. You should see the ESP32's startup messages

### Connecting Phone to ESP32 (Bluetooth)

1. Power the ESP32
2. On your phone, enable Bluetooth
3. Pair with device name: **`LoRa-ESP32-Chat`**
4. Open a Bluetooth serial terminal app (SPP-compatible)
5. Connect to the paired device
6. You should see the ESP32 startup messages

### Sending a Message

1. Type your message in the input field at the bottom of the app
2. Tap **Send** (or press Enter)
3. Your message will appear with `[TX]` prefix, indicating it was transmitted via LoRa

### Receiving a Message

1. When the other node sends a message, it appears automatically
2. Received messages are prefixed with `[RX]`

## Message Format

| Prefix | Meaning |
|--------|---------|
| `[TX]` | Message you sent (transmitted via LoRa) |
| `[RX]` | Message received from the other node |

### Example Conversation

**Phone 1 Screen:**
```
LoRa Two-Way Chat
Initializing...
LoRa initialized successfully!
Ready to send and receive messages.
-----------------------------------
[TX] Hello from Node 1!
[RX] Hi! This is Node 2 responding.
[TX] Message received loud and clear!
```

**Phone 2 Screen:**
```
LoRa Two-Way Chat
Initializing...
LoRa initialized successfully!
Ready to send and receive messages.
-----------------------------------
[RX] Hello from Node 1!
[TX] Hi! This is Node 2 responding.
[RX] Message received loud and clear!
```

## Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SENDING A MESSAGE                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  1. User types message      2. ESP32 receives       3. LoRa transmits   │
│     on Phone 1                 via USB Serial          over the air     │
│                                                                         │
│  ┌─────────┐               ┌─────────────────┐     ┌─────────────────┐  │
│  │ Phone 1 │ ──USB OTG──►  │ ESP32 (Node 1)  │ ──► │ SX1278 (433MHz) │  │
│  │  "Hi!"  │               │ Serial.read()   │     │ LoRa.send()     │  │
│  └─────────┘               └─────────────────┘     └────────┬────────┘  │
│                                                              │          │
│                              ◄── LoRa Radio Waves ──────────►│          │
│                                                              │          │
│  ┌─────────┐               ┌─────────────────┐     ┌────────▼────────┐  │
│  │ Phone 2 │ ◄──USB OTG──  │ ESP32 (Node 2)  │ ◄── │ SX1278 (433MHz) │  │
│  │ "[RX]   │               │ Serial.print()  │     │ LoRa.receive()  │  │
│  │  Hi!"   │               └─────────────────┘     └─────────────────┘  │
│  └─────────┘                                                            │
│                                                                         │
│  4. LoRa receives          5. ESP32 forwards       6. Phone 2 displays  │
│     the packet                to USB Serial           the message       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### "ERROR: LoRa init failed!"

- Check wiring connections between SX1278 and ESP32
- Verify VCC is connected to 3.3V (not 5V)
- Ensure antenna is attached
- Try resetting the ESP32

### No Messages Received

- Verify both nodes are using the same frequency (433 MHz)
- Check that antennas are attached to both modules
- Reduce distance between nodes for initial testing
- Ensure both ESP32 boards have the same firmware

### Phone Not Detecting ESP32

- Try a different USB cable (some cables are charge-only)
- Ensure USB OTG adapter is working
- Check that the ESP32's USB-to-Serial chip driver is recognized
- Try rebooting the phone

### Messages Corrupted or Incomplete

- Reduce distance between nodes
- Check for interference from other 433 MHz devices
- Ensure stable power supply to ESP32

## Specifications

| Feature | Value |
|---------|-------|
| Frequency | 433 MHz |
| Communication Mode | Half-duplex |
| Serial Baud Rate | 115200 |
| Range | Up to several kilometers (line of sight with good antenna) |
| Internet Required | No |
| WiFi Required | No |
| Bluetooth Required | Optional (for wireless phone-to-ESP32 link) |

## Project Structure

```
ESP32_LoRaModule/
├── src/
│   └── main.cpp          # Main firmware code
├── platformio.ini        # PlatformIO configuration
└── README.md             # This file
```

## License

This project is open source and available for educational and personal use.

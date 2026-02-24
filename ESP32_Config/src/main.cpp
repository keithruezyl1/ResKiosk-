/*
 * LoRa Offline Two-Way Messaging System
 * ESP32 + SX1278 (RA-01) 433MHz
 * 
 * Wiring:
 *   SX1278 Pin -> ESP32 Pin
 *   VCC        -> 3.3V
 *   GND        -> GND
 *   SCK        -> GPIO18
 *   MISO       -> GPIO19
 *   MOSI       -> GPIO23
 *   NSS        -> GPIO5
 *   RST        -> GPIO14
 *   DIO0       -> GPIO2
 *   
 *   Buzzer     -> GPIO25 (GPIO34 is input-only, cannot use for output)
 */

#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include "BluetoothSerial.h"

#define LORA_SS    5
#define LORA_RST   14
#define LORA_DIO0  2

#define BUZZER_PIN 25

#define LORA_FREQUENCY 433E6
#define SERIAL_BAUD    115200
#define BT_DEVICE_NAME "Sting_Node_2"

void buzzerBeep(int duration = 100, int count = 2);
void printToAll(const String &message);
void sendLoRaMessage(const String &message, const char *sourceTag);

BluetoothSerial SerialBT;

void setup() {
  Serial.begin(SERIAL_BAUD);
  SerialBT.begin(BT_DEVICE_NAME);

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  printToAll("LoRa Two-Way Chat");
  printToAll("Initializing...");
  printToAll(String("Bluetooth device name: ") + BT_DEVICE_NAME);

  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQUENCY)) {
    printToAll("ERROR: LoRa init failed!");
    while (1) {
      delay(1000);
    }
  }

  printToAll("LoRa initialized successfully!");
  printToAll("Ready to send and receive messages.");
  printToAll("Input channels: USB Serial + Bluetooth Serial");
  printToAll("-----------------------------------");
  
  buzzerBeep(100, 1);
}

void loop() {
  if (Serial.available()) {
    String message = Serial.readStringUntil('\n');
    message.trim();
    
    if (message.length() > 0) {
      sendLoRaMessage(message, "USB");
    }
  }

  if (SerialBT.available()) {
    String message = SerialBT.readStringUntil('\n');
    message.trim();
    
    if (message.length() > 0) {
      sendLoRaMessage(message, "BT");
    }
  }

  int packetSize = LoRa.parsePacket();
  if (packetSize) {
    String incoming = "";
    
    while (LoRa.available()) {
      incoming += (char)LoRa.read();
    }
    
    printToAll(String("[RX] ") + incoming);
    
    buzzerBeep(100, 2);
  }
}

void sendLoRaMessage(const String &message, const char *sourceTag) {
  printToAll(String("[TX ") + sourceTag + "] " + message);

  LoRa.beginPacket();
  LoRa.print(message);
  LoRa.endPacket();
}

void printToAll(const String &message) {
  Serial.println(message);
  SerialBT.println(message);
}

void buzzerBeep(int duration, int count) {
  for (int i = 0; i < count; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(duration);
    digitalWrite(BUZZER_PIN, LOW);
    if (i < count - 1) {
      delay(duration);
    }
  }
}
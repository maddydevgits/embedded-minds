# ESP32 Smart Comb Setup Guide

## Hardware Requirements

- ESP32 Development Board
- DS18B20 Temperature Sensor (OneWire)
- Analog Light Sensor (photoresistor/LDR)
- Analog Moisture Sensor
- Digital IR Sensor (for combing detection)
- Resistors as needed for sensors
- Breadboard and jumper wires

## Wiring Diagram

### DS18B20 Temperature Sensor
- VCC → 3.3V (with 4.7kΩ pull-up resistor to data line)
- GND → GND
- DATA → GPIO 4

### Light Sensor (Analog)
- VCC → 3.3V
- GND → GND
- Signal → GPIO 34 (ADC1_CH6)

### Moisture Sensor (Analog)
- VCC → 3.3V
- GND → GND
- Signal → GPIO 35 (ADC1_CH7)

### IR Sensor (Digital)
- VCC → 3.3V
- GND → GND
- Signal → GPIO 2

**Note**: Adjust pin numbers in the code based on your actual wiring.

## Software Setup

### 1. Install Required Libraries

Open Arduino IDE and install these libraries via Library Manager:

1. **WiFi** (usually included with ESP32 board support)
2. **PubSubClient** by Nick O'Leary
   - Go to: Sketch → Include Library → Manage Libraries
   - Search for "PubSubClient"
   - Install version 2.8.0 or later
3. **OneWire** by Paul Stoffregen
4. **DallasTemperature** by Miles Burton

### 2. Install ESP32 Board Support

1. Go to: File → Preferences
2. Add this URL to "Additional Board Manager URLs":
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
3. Go to: Tools → Board → Boards Manager
4. Search for "ESP32" and install "esp32 by Espressif Systems"
5. Select your ESP32 board: Tools → Board → ESP32 Arduino → Your Board Model

### 3. Configure the Code

Open `esp32_smart_comb.ino` and update these values:

```cpp
// WiFi Credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// User ID - Get this from your dashboard after logging in
const char* user_id = "YOUR_USER_ID_HERE";

// Sensor Pins - Adjust based on your wiring
#define ONE_WIRE_BUS 4          // DS18B20 data pin
#define LIGHT_SENSOR_PIN 34     // Analog light sensor
#define MOISTURE_SENSOR_PIN 35  // Analog moisture sensor
#define IR_SENSOR_PIN 2         // Digital IR sensor
```

### 4. Upload the Code

1. Connect your ESP32 via USB
2. Select the correct port: Tools → Port → (your ESP32 port)
3. Click Upload button
4. Open Serial Monitor (Tools → Serial Monitor) at 115200 baud to see debug output

## How It Works

1. **Role Selection**: When you select a role (mother/father/child) on the website dashboard, it sends the role to the ESP32 via MQTT topic `smartcomb/role`.

2. **Sensor Reading**: The ESP32 continuously reads sensors every 2 seconds.

3. **Combing Detection**: The IR sensor detects when combing is happening. Only when `isCombing = true`, the ESP32 publishes sensor data.

4. **Data Publishing**: Sensor data is published to MQTT topic `smartcomb/sensors` with the current role.

5. **Data Storage**: The Flask application receives the data and stores it in MongoDB with the role.

6. **Recommendations**: Based on the selected role and sensor data, AI recommendations are generated.

## Testing

1. Upload the code to ESP32
2. Open Serial Monitor to verify WiFi and MQTT connection
3. Log in to the web dashboard
4. Select a role (mother/father/child)
5. The ESP32 should receive the role and start publishing sensor data when combing is detected
6. Check the dashboard to see sensor readings appear

## Troubleshooting

### WiFi Connection Issues
- Verify SSID and password are correct
- Check WiFi signal strength
- Ensure 2.4GHz network (ESP32 doesn't support 5GHz)

### MQTT Connection Issues
- Verify broker.hivemq.com is accessible
- Check firewall settings
- Try using a different MQTT broker if needed

### Sensor Reading Issues
- Verify wiring connections
- Check sensor power supply (3.3V)
- For DS18B20, ensure pull-up resistor (4.7kΩ) is connected
- Test sensors individually using Serial Monitor output

### No Data on Dashboard
- Verify user_id in code matches your dashboard user_id
- Check that role is being selected on dashboard
- Verify MQTT topics match between ESP32 and Flask app
- Check Serial Monitor for error messages

## Sensor Calibration

You may need to calibrate your analog sensors:

```cpp
// In readAndPublishSensors() function, adjust these:
float lightPercent = (lightValue / 4095.0) * 100.0;  // Adjust based on your sensor
float moisturePercent = (moistureValue / 4095.0) * 100.0;  // Adjust based on your sensor
```

Test your sensors and adjust the calculations to match your sensor characteristics.

## IR Sensor Logic

The IR sensor logic may need adjustment based on your specific sensor:

```cpp
bool irReading = digitalRead(IR_SENSOR_PIN);
isCombing = (irReading == HIGH);  // Change to LOW if your sensor logic is inverted
```

Test your IR sensor and adjust the logic accordingly.


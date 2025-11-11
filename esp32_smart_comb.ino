/*
 * Smart Comb - ESP32 Arduino Code
 * 
 * Sensors:
 * - DS18B20 Temperature Sensor (OneWire)
 * - Analog Light Sensor (GPIO)
 * - Analog Moisture Sensor (GPIO)
 * - Digital IR Sensor (GPIO)
 * 
 * Features:
 * - WiFi Connection
 * - MQTT Communication
 * - Receives role selection from website
 * - Publishes sensor data only when combing is detected
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// WiFi Credentials - UPDATE THESE
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT Configuration
const char* mqtt_broker = "broker.hivemq.com";
const int mqtt_port = 1883;
const char* mqtt_topic_sensors = "smartcomb/sensors";
const char* mqtt_topic_ir = "smartcomb/sensors/ir";
const char* mqtt_topic_role = "smartcomb/role";  // Subscribe to role changes
const char* mqtt_topic_vibration = "smartcomb/vibration";  // Subscribe to vibration motor control

// User ID - UPDATE THIS with your user_id from the dashboard
const char* user_id = "YOUR_USER_ID_HERE";

// Sensor Pins - UPDATE THESE based on your wiring
#define ONE_WIRE_BUS 4          // DS18B20 data pin
#define LIGHT_SENSOR_PIN 34     // Analog light sensor (ADC1)
#define MOISTURE_SENSOR_PIN 35  // Analog moisture sensor (ADC1)
#define IR_SENSOR_PIN 2         // Digital IR sensor
#define VIBRATION_MOTOR_PIN 5   // Vibration motor control pin (PWM capable)

// OneWire and DallasTemperature setup
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// WiFi and MQTT clients
WiFiClient espClient;
PubSubClient client(espClient);

// Current role (set by website)
String currentRole = "mother";  // Default role
bool isCombing = false;
bool vibrationMotorOn = false;  // Vibration motor state
unsigned long lastSensorRead = 0;
const unsigned long sensorInterval = 2000;  // Read sensors every 2 seconds

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Initialize sensors
  pinMode(IR_SENSOR_PIN, INPUT);
  pinMode(LIGHT_SENSOR_PIN, INPUT);
  pinMode(MOISTURE_SENSOR_PIN, INPUT);
  
  // Initialize vibration motor
  pinMode(VIBRATION_MOTOR_PIN, OUTPUT);
  digitalWrite(VIBRATION_MOTOR_PIN, LOW);  // Start with motor off
  ledcSetup(0, 5000, 8);  // Setup PWM channel 0, 5kHz, 8-bit resolution
  ledcAttachPin(VIBRATION_MOTOR_PIN, 0);  // Attach pin to channel 0
  
  // Initialize DS18B20
  sensors.begin();
  
  // Connect to WiFi
  setup_wifi();
  
  // Setup MQTT
  client.setServer(mqtt_broker, mqtt_port);
  client.setCallback(mqtt_callback);
  
  Serial.println("Smart Comb initialized!");
}

void loop() {
  // Reconnect MQTT if disconnected
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop();
  
  // Read sensors at intervals
  unsigned long currentMillis = millis();
  if (currentMillis - lastSensorRead >= sensorInterval) {
    readAndPublishSensors();
    lastSensorRead = currentMillis;
  }
  
  delay(100);
}

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("");
  Serial.println("WiFi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    // Create unique client ID
    String clientId = "SmartComb-";
    clientId += String(random(0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println(" connected!");
      
      // Subscribe to role topic
      bool subResult = client.subscribe(mqtt_topic_role);
      Serial.print("Subscribed to role topic: ");
      Serial.println(mqtt_topic_role);
      Serial.print("Subscription result: ");
      Serial.println(subResult ? "SUCCESS" : "FAILED");
      
      // Subscribe to vibration motor control topic
      bool vibSubResult = client.subscribe(mqtt_topic_vibration);
      Serial.print("Subscribed to vibration topic: ");
      Serial.println(mqtt_topic_vibration);
      Serial.print("Subscription result: ");
      Serial.println(vibSubResult ? "SUCCESS" : "FAILED");
      
      Serial.print("Current role: ");
      Serial.println(currentRole);
      
    } else {
      Serial.print(" failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("MQTT message received on topic: ");
  Serial.println(topic);
  Serial.print("Payload length: ");
  Serial.println(length);
  
  String topicStr = String(topic);
  String payloadStr = "";
  for (int i = 0; i < length; i++) {
    payloadStr += (char)payload[i];
  }
  
  // Handle role change from website
  if (topicStr == String(mqtt_topic_role)) {
    Serial.print("Received role: '");
    Serial.print(payloadStr);
    Serial.println("'");
    
    // Validate role
    if (payloadStr == "mother" || payloadStr == "father" || payloadStr == "child") {
      currentRole = payloadStr;
      Serial.print("✓ Role updated to: ");
      Serial.println(currentRole);
    } else {
      Serial.print("✗ Invalid role received: '");
      Serial.print(payloadStr);
      Serial.println("'");
      Serial.println("Expected: mother, father, or child");
    }
  }
  // Handle vibration motor control
  else if (topicStr == String(mqtt_topic_vibration)) {
    Serial.print("Received vibration command: '");
    Serial.print(payloadStr);
    Serial.println("'");
    
    if (payloadStr == "on" || payloadStr == "1" || payloadStr == "true") {
      vibrationMotorOn = true;
      ledcWrite(0, 255);  // Set PWM to maximum (255 = 100% duty cycle)
      Serial.println("✓ Vibration motor: ON");
    } else if (payloadStr == "off" || payloadStr == "0" || payloadStr == "false") {
      vibrationMotorOn = false;
      ledcWrite(0, 0);  // Set PWM to 0 (motor off)
      Serial.println("✓ Vibration motor: OFF");
    } else {
      Serial.print("✗ Invalid vibration command: '");
      Serial.print(payloadStr);
      Serial.println("'");
      Serial.println("Expected: on, off, 1, 0, true, or false");
    }
  } else {
    Serial.print("Unknown topic: ");
    Serial.println(topic);
  }
}

void readAndPublishSensors() {
  // Read IR sensor (combing detection)
  bool irReading = digitalRead(IR_SENSOR_PIN);
  isCombing = (irReading == HIGH);  // Adjust based on your sensor logic
  
  // Publish IR sensor status
  String irPayload = "{\"value\":" + String(isCombing ? 1 : 0) + "}";
  client.publish(mqtt_topic_ir, irPayload.c_str());
  
  // Only read and publish other sensors when combing is detected
  if (isCombing) {
    // Read DS18B20 temperature
    sensors.requestTemperatures();
    float temperature = sensors.getTempCByIndex(0);
    
    // Check if temperature reading is valid
    if (temperature == DEVICE_DISCONNECTED_C) {
      Serial.println("Error: Could not read temperature");
      temperature = 0.0;
    }
    
    // Read analog sensors
    int lightValue = analogRead(LIGHT_SENSOR_PIN);
    int moistureValue = analogRead(MOISTURE_SENSOR_PIN);
    
    // Convert analog readings (0-4095) to percentage (0-100) if needed
    // Adjust these calculations based on your sensor characteristics
    float lightPercent = (lightValue / 4095.0) * 100.0;
    float moisturePercent = (moistureValue / 4095.0) * 100.0;
    
    // Create JSON payload
    String payload = "{";
    payload += "\"user_id\":\"" + String(user_id) + "\",";
    payload += "\"role\":\"" + currentRole + "\",";
    payload += "\"temperature\":" + String(temperature, 1) + ",";
    payload += "\"light\":" + String(lightValue) + ",";  // Raw ADC value or percentage
    payload += "\"moisture\":" + String(moistureValue) + ",";  // Raw ADC value or percentage
    payload += "\"ir\":" + String(isCombing ? 1 : 0);
    payload += "}";
    
    // Publish sensor data
    client.publish(mqtt_topic_sensors, payload.c_str());
    
    // Serial output for debugging
    Serial.println("=== Sensor Readings ===");
    Serial.print("Role: ");
    Serial.println(currentRole);
    Serial.print("Temperature: ");
    Serial.print(temperature);
    Serial.println("°C");
    Serial.print("Light: ");
    Serial.println(lightValue);
    Serial.print("Moisture: ");
    Serial.println(moistureValue);
    Serial.print("Combing: ");
    Serial.println(isCombing ? "Yes" : "No");
    Serial.println("======================");
  } else {
    Serial.println("Not combing - sensors not read");
  }
}


import paho.mqtt.client as mqtt
import json
from datetime import datetime
from flask import Flask

class MQTTClient:
    def __init__(self, app: Flask, mongo):
        self.app = app
        self.mongo = mongo
        self.client = None
        self.broker = app.config['MQTT_BROKER']
        self.port = app.config['MQTT_PORT']
        self.topic = app.config['MQTT_TOPIC']
        self.is_combing = False
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"Connected to MQTT Broker: {self.broker}")
            client.subscribe(self.topic)
            client.subscribe(f"{self.topic}/ir")  # IR sensor topic
        else:
            print(f"Failed to connect, return code {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            
            topic = msg.topic
            
            # Check IR sensor to determine if combing
            if topic.endswith('/ir'):
                self.is_combing = data.get('value', 0) == 1
                print(f"IR Sensor: Combing = {self.is_combing}")
                return
            
            # Only process other sensors if combing is detected
            if not self.is_combing:
                print("Not combing, ignoring sensor data")
                return
            
            # Process sensor data
            with self.app.app_context():
                # Get raw values
                light_raw = data.get('light', 0)
                moisture_raw = data.get('moisture', 0)
                
                # Convert to percentages if needed (handle both raw ADC and percentage values)
                light_value = self._convert_light_value(light_raw)
                # For moisture, use the same inverted conversion logic
                if moisture_raw > 100:
                    moisture_value = ((4095.0 - moisture_raw) / 4095.0) * 100.0
                else:
                    moisture_value = moisture_raw
                moisture_value = max(0, min(100, moisture_value))
                
                sensor_data = {
                    'user_id': data.get('user_id', 'anonymous'),
                    'role': data.get('role', 'user'),
                    'temperature': data.get('temperature', 0),
                    'light': light_value,  # Store as percentage (0-100)
                    'moisture': moisture_value,  # Store as percentage (0-100)
                    'moisture_status': self._determine_moisture_status(moisture_raw),
                    'ir_sensor': data.get('ir', 0),
                    'timestamp': datetime.utcnow()
                }
                
                self.mongo.db.sensor_data.insert_one(sensor_data)
                print(f"[MQTT] Saved sensor data - User: {sensor_data['user_id']}, Role: {sensor_data['role']}, Temp: {sensor_data['temperature']}°C")
                
        except Exception as e:
            print(f"Error processing MQTT message: {e}")
    
    def _determine_moisture_status(self, moisture_value):
        """Determine moisture status based on analog value
        Note: moisture_value can be raw ADC (0-4095) or percentage (0-100)
        If it's ADC, convert to percentage first (inverted: 4095 = dry, 0 = wet)
        """
        # If value is > 100, assume it's raw ADC and convert to percentage (inverted)
        if moisture_value > 100:
            # Inverted conversion: 4095 = dry (0%), 0 = wet (100%)
            moisture_percent = ((4095.0 - moisture_value) / 4095.0) * 100.0
        else:
            moisture_percent = moisture_value
        
        # Clamp to 0-100 range
        moisture_percent = max(0, min(100, moisture_percent))
        
        if moisture_percent < 30:
            return 'dry'
        elif moisture_percent > 70:
            return 'oily'
        else:
            return 'normal'
    
    def _convert_light_value(self, light_value):
        """Convert light sensor value to percentage
        Note: light_value can be raw ADC (0-4095) or percentage (0-100)
        If it's ADC, convert to percentage (inverted: 4095 = no light, 0 = full light)
        """
        # If value is > 100, assume it's raw ADC and convert to percentage (inverted)
        if light_value > 100:
            # Inverted conversion: 4095 = no light (0%), 0 = full light (100%)
            light_percent = ((4095.0 - light_value) / 4095.0) * 100.0
        else:
            light_percent = light_value
        
        # Clamp to 0-100 range
        return max(0, min(100, light_percent))
    
    def start(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_forever()
        except Exception as e:
            print(f"MQTT connection error: {e}")


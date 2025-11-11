"""
Test MQTT Publisher Script
This script simulates sensor data being sent to the MQTT broker.
It subscribes to role updates from the website, just like the ESP32.

Run this to test the Smart Comb system.
"""

import paho.mqtt.client as mqtt
import json
import time
import random

# MQTT Configuration
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_SENSORS = "smartcomb/sensors"
TOPIC_IR = "smartcomb/sensors/ir"
TOPIC_ROLE = "smartcomb/sensors/role"  # Subscribe to role updates

# Test user ID (replace with actual user_id from your database)
# Run: python get_user_id.py <username> to get your user_id
# Or get it from the dashboard after logging in
USER_ID = "6912bf7e2662f139fcd0db53"  # UPDATE THIS with your actual user_id

# Current role (will be updated via MQTT from website)
current_role = "mother"  # Default role, will be updated when website sends role

def publish_sensor_data(client):
    """Publish simulated sensor data"""
    global current_role
    
    # Simulate IR sensor detecting combing (1 = combing, 0 = not combing)
    # For testing, we'll simulate combing most of the time
    ir_value = 1  # Set to 1 to simulate combing, 0 to simulate not combing
    
    # Publish IR sensor status
    ir_payload = json.dumps({"value": ir_value})
    client.publish(TOPIC_IR, ir_payload)
    
    if ir_value == 1:
        # Only publish other sensors when combing is detected
        sensor_data = {
            "user_id": USER_ID,
            "role": current_role,  # Use current role (updated from website)
            "temperature": round(random.uniform(20.0, 35.0), 1),  # DS18B20 temperature
            "light": random.randint(200, 800),  # Analog light sensor (hair density)
            "moisture": random.randint(20, 90),  # Analog moisture sensor
            "ir": ir_value
        }
        
        payload = json.dumps(sensor_data)
        client.publish(TOPIC_SENSORS, payload)
        
        print(f"[{time.strftime('%H:%M:%S')}] Published sensor data:")
        print(f"  Role: {current_role}")
        print(f"  Temperature: {sensor_data['temperature']}°C")
        print(f"  Light: {sensor_data['light']}")
        print(f"  Moisture: {sensor_data['moisture']}")
        print(f"  Combing: {'Yes' if ir_value == 1 else 'No'}")
    else:
        print(f"[{time.strftime('%H:%M:%S')}] Not combing - skipping sensor data")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✓ Connected to MQTT Broker: {BROKER}")
        # Subscribe to role topic to receive role updates from website
        client.subscribe(TOPIC_ROLE)
        print(f"✓ Subscribed to role topic: {TOPIC_ROLE}")
        print(f"  Current role: {current_role}")
        print(f"  Waiting for role updates from website...")
    else:
        print(f"✗ Failed to connect, return code {rc}")

def on_message(client, userdata, msg):
    """Handle incoming MQTT messages (role updates)"""
    global current_role
    
    # Handle both string and bytes types (for different paho-mqtt versions)
    if isinstance(msg.topic, bytes):
        topic = msg.topic.decode('utf-8')
    else:
        topic = msg.topic
    
    if isinstance(msg.payload, bytes):
        payload = msg.payload.decode('utf-8')
    else:
        payload = msg.payload
    
    if topic == TOPIC_ROLE:
        # Validate role
        if payload in ["mother", "father", "child"]:
            current_role = payload
            print(f"\n✓ Role updated to: {current_role}")
            print(f"  All future sensor data will be tagged with role: {current_role}\n")
        else:
            print(f"\n✗ Invalid role received: '{payload}'")
            print(f"  Expected: mother, father, or child\n")
    else:
        print(f"Received message on unknown topic: {topic}")

def main():
    global current_role
    
    print("=" * 60)
    print("Smart Comb - MQTT Test Publisher")
    print("=" * 60)
    print(f"User ID: {USER_ID}")
    print(f"Initial Role: {current_role}")
    print(f"Broker: {BROKER}:{PORT}")
    print("=" * 60)
    print("\nInstructions:")
    print("1. Make sure USER_ID is set to your actual user_id from dashboard")
    print("2. Select a role (mother/father/child) on the website dashboard")
    print("3. This script will receive the role update and publish data with that role")
    print("4. Press Ctrl+C to stop\n")
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message  # Handle incoming messages (role updates)
    
    try:
        print("Connecting to MQTT broker...")
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        
        # Wait a moment for connection to establish
        time.sleep(2)
        
        print("\n" + "=" * 60)
        print("Starting sensor data simulation...")
        print("=" * 60)
        print("Press Ctrl+C to stop\n")
        
        # Publish data every 5 seconds
        while True:
            publish_sensor_data(client)
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\nStopping publisher...")
        client.loop_stop()
        client.disconnect()
        print("Disconnected from MQTT broker")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()


# Smart Comb - Hair Monitoring System

A Flask-based web application for monitoring hair health using IoT sensors and providing AI-powered product recommendations.

## Features

- **ESP32 Integration**: Complete Arduino code for ESP32 with sensor support
- **Sensor Integration**: Temperature (DS18B20), Light (analog), Moisture (analog), and IR (digital) sensors
- **MQTT Data Collection**: Real-time sensor data via MQTT protocol
- **Dynamic Role Selection**: Select who is combing on the website - role is sent to ESP32 via MQTT
- **User Authentication**: Signup and login system
- **Role-based Monitoring**: Track different family members (mother, father, child) with one device
- **AI Recommendations**: OpenAI-powered product recommendations based on sensor data and role
- **Data Visualization**: Real-time charts showing sensor readings over time
- **Chatbot**: AI assistant for hair health questions
- **Modern UI**: Beautiful interface built with Tailwind CSS

## Prerequisites

- Python 3.8+
- ESP32 Development Board
- Sensors: DS18B20, Light sensor, Moisture sensor, IR sensor
- MongoDB Atlas account (or local MongoDB)
- OpenAI API key
- MQTT broker access (default: broker.hivemq.com)
- Arduino IDE with ESP32 board support

## Installation

1. Clone the repository:
```bash
cd embedded-minds
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file from `.env.example`:
```bash
cp .env.example .env
```

5. Edit `.env` and add your credentials:
- `SECRET_KEY`: A random secret key for Flask sessions
- `MONGODB_URI`: Your MongoDB Atlas connection string
- `OPENAI_API_KEY`: Your OpenAI API key
- `MQTT_BROKER`: MQTT broker address (default: broker.hivemq.com)
- `MQTT_PORT`: MQTT port (default: 1883)
- `MQTT_TOPIC`: MQTT topic for sensor data (default: smartcomb/sensors)

## Running the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

## MQTT Data Format

The application expects sensor data in the following JSON format:

**Main Sensor Data** (topic: `smartcomb/sensors`):
```json
{
  "user_id": "user_id_here",
  "role": "mother|father|child",
  "temperature": 25.5,
  "light": 450,
  "moisture": 65,
  "ir": 1
}
```

**IR Sensor** (topic: `smartcomb/sensors/ir`) - Detects if combing is active:
```json
{
  "value": 1
}
```
- `value: 1` = Combing detected (other sensors will be read)
- `value: 0` = Not combing (other sensor data will be ignored)

**Note**: The IR sensor must publish `value: 1` before other sensors publish data. The system only processes sensor readings when combing is detected.

### Testing MQTT

1. First, get your user_id after signing up:
```bash
python get_user_id.py <your_username>
# Or list all users:
python get_user_id.py --list
```

2. Update `USER_ID` in `test_mqtt_publisher.py` with your actual user_id

3. Run the test publisher to simulate sensor data:
```bash
python test_mqtt_publisher.py
```

## Project Structure

```
embedded-minds/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── mqtt_client.py        # MQTT client for sensor data
├── openai_service.py     # OpenAI integration for recommendations
├── esp32_smart_comb.ino  # ESP32 Arduino code
├── ESP32_SETUP.md        # ESP32 setup guide
├── requirements.txt      # Python dependencies
├── templates/            # HTML templates
│   ├── base.html
│   ├── login.html
│   ├── signup.html
│   └── dashboard.html
├── test_mqtt_publisher.py # Test script for MQTT
├── get_user_id.py        # Helper script to get user ID
└── README.md
```

## Usage

### ESP32 Setup

1. **Install Libraries**: Install required Arduino libraries (see ESP32_SETUP.md)
2. **Configure Code**: Update WiFi credentials, user_id, and sensor pins in `esp32_smart_comb.ino`
3. **Upload Code**: Upload to ESP32 and verify connection via Serial Monitor
4. **Get User ID**: Log in to dashboard and copy your User ID from the dashboard
5. **Update ESP32**: Replace `YOUR_USER_ID_HERE` in the ESP32 code with your actual user_id

### Web Application

1. **Sign Up**: Create a new account at `/signup`
2. **Login**: Access your dashboard at `/login`
3. **Select Role**: Choose who is using the comb (mother/father/child) on the dashboard
   - This sends the role to your ESP32 device via MQTT
   - The ESP32 will tag all sensor data with this role
4. **View Data**: Monitor real-time sensor readings and historical charts
5. **Get Recommendations**: Click "Get Recommendations" to receive AI-powered product suggestions based on sensor data and selected role
6. **Chat**: Use the Hair Health Assistant chatbot to ask questions about hair health and monitoring

### How Role Selection Works

- When you select a role (mother/father/child) on the dashboard, it's sent to the ESP32 via MQTT topic `smartcomb/role`
- The ESP32 receives this and stores it as the current role
- All sensor data published by the ESP32 includes this role
- Data is stored in MongoDB with the role, allowing separate tracking for each family member
- Recommendations are generated based on both the sensor data AND the selected role

## Testing

1. Start the Flask application:
```bash
python app.py
```

2. In another terminal, run the MQTT test publisher (after updating USER_ID):
```bash
python test_mqtt_publisher.py
```

3. Open your browser and navigate to `http://localhost:5000`
4. Sign up for an account
5. After logging in, you should see sensor data appearing on the dashboard

## Sensor Interpretation

- **Temperature**: Indicates scalp heat/irritation level
- **Light Sensor**: Measures hair density (higher values = denser hair)
- **Moisture Sensor**: Detects hair moisture level (dry/normal/oily)
- **IR Sensor**: Detects when combing is active (only then other sensors read data)

## License

This project is for educational purposes.


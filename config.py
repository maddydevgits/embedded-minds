import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    # Flask-PyMongo looks for MONGO_URI
    MONGO_URI = os.environ.get('MONGODB_URI') or 'mongodb://localhost:27017/smartcomb'
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY') or ''
    MQTT_BROKER = os.environ.get('MQTT_BROKER') or 'broker.hivemq.com'
    MQTT_PORT = int(os.environ.get('MQTT_PORT') or 1883)
    MQTT_TOPIC = os.environ.get('MQTT_TOPIC') or 'smartcomb/sensors'


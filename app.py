from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
from config import Config
from mqtt_client import MQTTClient
from openai_service import OpenAIService
import threading
import paho.mqtt.publish as mqtt_publish

app = Flask(__name__)
app.config.from_object(Config)

# Initialize MongoDB
mongo = PyMongo(app)

# Initialize services
mqtt_client = MQTTClient(app, mongo)
openai_service = OpenAIService()

# Start MQTT client in background thread
mqtt_thread = threading.Thread(target=mqtt_client.start, daemon=True)
mqtt_thread.start()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400
        
        # Check if user exists
        if mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]}):
            return jsonify({'error': 'User already exists'}), 400
        
        # Create user
        user = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'created_at': datetime.utcnow()
        }
        mongo.db.users.insert_one(user)
        
        session['user_id'] = str(user['_id'])
        session['username'] = username
        
        return jsonify({'success': True, 'redirect': url_for('dashboard')}), 200
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400
        
        user = mongo.db.users.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['username'] = username
            return jsonify({'success': True, 'redirect': url_for('dashboard')}), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get recent sensor data
    recent_data = list(mongo.db.sensor_data.find(
        {'user_id': session['user_id']}
    ).sort('timestamp', -1).limit(10))
    
    # Convert ObjectId to string for JSON serialization
    for data in recent_data:
        data['_id'] = str(data['_id'])
        if 'timestamp' in data:
            data['timestamp'] = data['timestamp'].isoformat()
    
    return render_template('dashboard.html', recent_data=recent_data)

@app.route('/api/sensor-data', methods=['GET'])
def get_sensor_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    role = request.args.get('role', 'user')
    limit = int(request.args.get('limit', 100))
    
    query = {'user_id': user_id}
    if role != 'all':
        query['role'] = role
    
    data = list(mongo.db.sensor_data.find(query).sort('timestamp', -1).limit(limit))
    
    # Debug logging
    print(f"[API] Sensor data query - User ID: {user_id}, Role: {role}")
    print(f"[API] MongoDB query: {query}")
    print(f"[API] Found {len(data)} records")
    if len(data) > 0:
        print(f"[API] First record role: {data[0].get('role', 'N/A')}, timestamp: {data[0].get('timestamp', 'N/A')}")
    else:
        # Check if there's data for this user with different roles
        all_user_data = list(mongo.db.sensor_data.find({'user_id': user_id}).limit(5))
        if all_user_data:
            roles_found = [d.get('role', 'N/A') for d in all_user_data]
            print(f"[API] No data for role '{role}', but found data with roles: {set(roles_found)}")
    
    for item in data:
        item['_id'] = str(item['_id'])
        if 'timestamp' in item:
            item['timestamp'] = item['timestamp'].isoformat()
    
    return jsonify(data)

@app.route('/api/age-config', methods=['GET', 'POST'])
def age_config():
    """Get or save age configuration for roles"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    
    if request.method == 'GET':
        # Get age configuration
        config = mongo.db.user_settings.find_one({'user_id': user_id})
        if config and 'ages' in config:
            return jsonify(config['ages'])
        return jsonify({'mother': None, 'father': None, 'child': None})
    
    elif request.method == 'POST':
        # Save age configuration
        data = request.get_json()
        ages = {
            'mother': data.get('mother'),
            'father': data.get('father'),
            'child': data.get('child')
        }
        
        # Validate ages
        for role, age in ages.items():
            if age is not None:
                try:
                    age = int(age)
                    if age < 1 or age > 120:
                        return jsonify({'error': f'Invalid age for {role}. Age must be between 1 and 120.'}), 400
                    ages[role] = age
                except (ValueError, TypeError):
                    return jsonify({'error': f'Invalid age for {role}. Please enter a valid number.'}), 400
        
        # Update or insert user settings
        mongo.db.user_settings.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'ages': ages,
                    'updated_at': datetime.utcnow()
                }
            },
            upsert=True
        )
        
        return jsonify({'success': True, 'ages': ages})

@app.route('/api/recommendations', methods=['POST'])
def get_recommendations():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    role = data.get('role', 'user')
    
    # Get latest sensor data for this user and role
    latest_data = mongo.db.sensor_data.find_one(
        {'user_id': session['user_id'], 'role': role},
        sort=[('timestamp', -1)]
    )
    
    if not latest_data:
        return jsonify({'error': 'No sensor data available'}), 404
    
    # Get age configuration
    user_settings = mongo.db.user_settings.find_one({'user_id': session['user_id']})
    age = None
    if user_settings and 'ages' in user_settings:
        age = user_settings['ages'].get(role)
    
    # Generate recommendations using OpenAI
    recommendations = openai_service.get_recommendations(
        temperature=latest_data.get('temperature', 0),
        light=latest_data.get('light', 0),
        moisture=latest_data.get('moisture', 0),
        moisture_status=latest_data.get('moisture_status', 'normal'),
        role=role,
        age=age
    )
    
    # Store recommendation
    recommendation_doc = {
        'user_id': session['user_id'],
        'role': role,
        'age': age,
        'recommendations': recommendations,
        'sensor_data_id': str(latest_data['_id']),
        'created_at': datetime.utcnow()
    }
    mongo.db.recommendations.insert_one(recommendation_doc)
    
    return jsonify(recommendations)

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    message = data.get('message', '')
    
    if not message:
        return jsonify({'error': 'Message is required'}), 400
    
    # Get user's recent sensor data for context
    recent_data = mongo.db.sensor_data.find_one(
        {'user_id': session['user_id']},
        sort=[('timestamp', -1)]
    )
    
    response = openai_service.chat(message, recent_data)
    
    return jsonify({'response': response})

@app.route('/api/user-id', methods=['GET'])
def get_user_id():
    """Get the current logged-in user's ID for MQTT testing"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    return jsonify({
        'user_id': session['user_id'],
        'username': session.get('username', '')
    })

@app.route('/api/set-role', methods=['POST'])
def set_role():
    """Send role selection to ESP32 via MQTT"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    role = data.get('role', '')
    
    if role not in ['mother', 'father', 'child']:
        return jsonify({'error': 'Invalid role. Must be mother, father, or child'}), 400
    
    try:
        topic = app.config['MQTT_TOPIC'] + '/role'
        print(f"[API] Publishing role '{role}' to topic: {topic}")
        
        # Publish role to MQTT topic that ESP32 subscribes to
        mqtt_publish.single(
            topic,
            role,
            hostname=app.config['MQTT_BROKER'],
            port=app.config['MQTT_PORT']
        )
        
        print(f"[API] Role '{role}' successfully published to MQTT")
        
        return jsonify({
            'success': True,
            'message': f'Role "{role}" sent to device',
            'role': role,
            'topic': topic
        })
    except Exception as e:
        print(f"[API] Error publishing role: {str(e)}")
        return jsonify({
            'error': f'Failed to send role to device: {str(e)}'
        }), 500

@app.route('/api/vibration', methods=['POST'])
def control_vibration():
    """Send vibration motor control command to ESP32 via MQTT"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    command = data.get('command', '').lower()
    
    if command not in ['on', 'off', '1', '0', 'true', 'false']:
        return jsonify({'error': 'Invalid command. Must be on, off, 1, 0, true, or false'}), 400
    
    try:
        topic = app.config['MQTT_TOPIC'] + '/vibration'
        print(f"[API] Publishing vibration command '{command}' to topic: {topic}")
        
        # Publish vibration command to MQTT topic that ESP32 subscribes to
        mqtt_publish.single(
            topic,
            command,
            hostname=app.config['MQTT_BROKER'],
            port=app.config['MQTT_PORT']
        )
        
        print(f"[API] Vibration command '{command}' successfully published to MQTT")
        
        return jsonify({
            'success': True,
            'message': f'Vibration motor command "{command}" sent to device',
            'command': command
        })
    except Exception as e:
        print(f"[API] Error publishing vibration command: {str(e)}")
        return jsonify({
            'error': f'Failed to send vibration command to device: {str(e)}'
        }), 500

@app.route('/api/debug-data', methods=['GET'])
def debug_data():
    """Debug endpoint to check what data exists in database"""
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    user_id = session['user_id']
    
    # Get all data for this user
    all_data = list(mongo.db.sensor_data.find({'user_id': user_id}).sort('timestamp', -1).limit(20))
    
    # Group by role
    roles_data = {}
    for item in all_data:
        role = item.get('role', 'unknown')
        if role not in roles_data:
            roles_data[role] = []
        roles_data[role].append({
            'timestamp': item.get('timestamp', '').isoformat() if hasattr(item.get('timestamp', ''), 'isoformat') else str(item.get('timestamp', '')),
            'temperature': item.get('temperature', 0),
            'light': item.get('light', 0),
            'moisture': item.get('moisture', 0)
        })
    
    return jsonify({
        'user_id': user_id,
        'total_records': len(all_data),
        'data_by_role': roles_data,
        'roles_found': list(roles_data.keys())
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4000)


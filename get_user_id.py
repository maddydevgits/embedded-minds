"""
Helper script to get user_id from MongoDB
Run this after creating an account to get your user_id for MQTT testing
"""

from flask import Flask
from flask_pymongo import PyMongo
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
mongo = PyMongo(app)

def get_user_id(username):
    """Get user_id for a given username"""
    user = mongo.db.users.find_one({'username': username})
    if user:
        return str(user['_id'])
    return None

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python get_user_id.py <username>")
        print("\nOr list all users:")
        print("Usage: python get_user_id.py --list")
        sys.exit(1)
    
    if sys.argv[1] == '--list':
        users = mongo.db.users.find({}, {'username': 1, 'email': 1})
        print("\nRegistered Users:")
        print("-" * 50)
        for user in users:
            user_id = str(user['_id'])
            print(f"Username: {user['username']}")
            print(f"Email: {user.get('email', 'N/A')}")
            print(f"User ID: {user_id}")
            print("-" * 50)
    else:
        username = sys.argv[1]
        user_id = get_user_id(username)
        if user_id:
            print(f"\nUser ID for '{username}': {user_id}")
            print(f"\nUpdate this in test_mqtt_publisher.py:")
            print(f'USER_ID = "{user_id}"')
        else:
            print(f"User '{username}' not found")


import json
import os

USERS_FILE = 'users.json'

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

try:
    users = load_users()
    print("Initial users:", users)
    users["test"] = {"password": "pwd", "watchlist": []}
    save_users(users)
    updated = load_users()
    print("Updated users:", updated)
    print("Test passed")
except Exception as e:
    print("Test failed:", e)

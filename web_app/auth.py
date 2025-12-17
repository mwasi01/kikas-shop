import json
import hashlib
import secrets
import os
from datetime import datetime

class UserManager:
    def __init__(self, users_file='users.json'):
        self.users_file = users_file
        self.load_users()
    
    def load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)
        else:
            self.users = {}
            self.initialize_default_users()
    
    def save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def hash_password(self, password):
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${hashed}"
    
    def verify_password(self, stored_password, provided_password):
        if not stored_password or '$' not in stored_password:
            return False
        salt, hashed = stored_password.split('$')
        test_hash = hashlib.sha256((provided_password + salt).encode()).hexdigest()
        return test_hash == hashed
    
    def initialize_default_users(self):
        self.users = {
            "admin": {
                "username": "admin",
                "password_hash": "",
                "role": "admin",
                "email": "",
                "full_name": "System Administrator",
                "created_at": datetime.now().isoformat()
            },
            "kika": {
                "username": "kika",
                "password_hash": "",
                "role": "owner",
                "email": "",
                "full_name": "Kika Shop Owner",
                "created_at": datetime.now().isoformat()
            }
        }
        self.save_users()
    
    def add_worker(self, username, email, full_name):
        if username in self.users:
            return False, "Username already exists"
        
        temp_password = secrets.token_urlsafe(8)
        
        self.users[username] = {
            "username": username,
            "password_hash": self.hash_password(temp_password),
            "role": "worker",
            "email": email,
            "full_name": full_name,
            "created_at": datetime.now().isoformat(),
            "password_changed": False
        }
        self.save_users()
        
        return True, temp_password
    
    def change_password(self, username, new_password):
        if username not in self.users:
            return False
        
        self.users[username]["password_hash"] = self.hash_password(new_password)
        if self.users[username]["role"] == "worker":
            self.users[username]["password_changed"] = True
        self.save_users()
        return True
    
    def authenticate(self, username, password):
        if username not in self.users:
            return False, None
        
        user = self.users[username]
        if self.verify_password(user["password_hash"], password):
            return True, user
        
        return False, None
    
    def get_all_workers(self):
        return {username: data for username, data in self.users.items() 
                if data.get("role") == "worker"}

import json
import hashlib
import secrets
import os
from datetime import datetime

class UserManager:
    def __init__(self, users_file='users.json'):
        self.users_file = users_file
        self.users = self.load_users()
    
    def load_users(self):
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}
    
    def save_users(self):
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            return True
        except Exception:
            return False
    
    def hash_password(self, password):
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}${hashed}"
    
    def verify_password(self, stored, provided):
        if not stored or '$' not in stored:
            return False
        salt, hashed = stored.split('$')
        test = hashlib.sha256((provided + salt).encode()).hexdigest()
        return test == hashed
    
    def authenticate(self, username, password):
        if username not in self.users:
            return False, None
        
        user = self.users[username]
        if self.verify_password(user.get('password_hash', ''), password):
            return True, user
        
        return False, None
    
    def add_worker(self, username, email, full_name):
        if username in self.users:
            return False, "Username exists"
        
        temp_pass = secrets.token_urlsafe(8)
        self.users[username] = {
            "username": username,
            "password_hash": self.hash_password(temp_pass),
            "role": "worker",
            "email": email,
            "full_name": full_name,
            "created_at": datetime.now().isoformat()
        }
        self.save_users()
        return True, temp_pass
    
    def get_all_workers(self):
        return {u: d for u, d in self.users.items() if d.get('role') == 'worker'}

# web_app/auth.py - COMPLETE AUTHENTICATION SYSTEM
import json
import hashlib
import secrets
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class UserManager:
    """Manages user authentication, authorization, and user data"""
    
    def __init__(self, users_file: str = 'users.json'):
        """
        Initialize UserManager with path to users database file
        
        Args:
            users_file: Path to JSON file storing user data
        """
        self.users_file = users_file
        self.users = self._load_users()
        
        # Initialize with default users if file doesn't exist or is empty
        if not self.users or len(self.users) == 0:
            self._initialize_default_users()
    
    def _load_users(self) -> Dict:
        """
        Load users from JSON file
        
        Returns:
            Dictionary of users or empty dict if file doesn't exist
        """
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    users_data = json.load(f)
                    # Ensure we have a dict, not a list
                    if isinstance(users_data, list):
                        # Convert old list format to dict format
                        users_dict = {}
                        for user in users_data:
                            if 'username' in user:
                                users_dict[user['username']] = user
                        return users_dict
                    return users_data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load users file: {e}")
        
        return {}
    
    def save_users(self) -> bool:
        """
        Save users to JSON file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
            
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2, default=str)
            return True
        except (IOError, TypeError) as e:
            print(f"Error saving users file: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password with salt using SHA-256
        
        Args:
            password: Plain text password
            
        Returns:
            Salted hash string in format "salt$hash"
        """
        # Generate random salt
        salt = secrets.token_hex(16)
        
        # Create hash: password + salt
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        
        # Return salt and hash separated by $
        return f"{salt}${hashed}"
    
    def _verify_password(self, stored_password: str, provided_password: str) -> bool:
        """
        Verify if provided password matches stored hash
        
        Args:
            stored_password: Stored salted hash
            provided_password: Password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        if not stored_password or '$' not in stored_password:
            return False
        
        try:
            # Split salt and hash
            salt, hashed = stored_password.split('$', 1)
            
            # Hash provided password with same salt
            test_hash = hashlib.sha256((provided_password + salt).encode()).hexdigest()
            
            # Compare
            return test_hash == hashed
        except (ValueError, AttributeError):
            return False
    
    def _initialize_default_users(self):
        """Create default admin and owner accounts (no passwords set yet)"""
        current_time = datetime.now().isoformat()
        
        self.users = {
            "admin": {
                "username": "admin",
                "password_hash": "",  # Will be set during first-time setup
                "role": "admin",
                "email": "",
                "full_name": "System Administrator",
                "created_at": current_time,
                "last_login": None,
                "active": True,
                "password_changed": False
            },
            "kika": {
                "username": "kika",
                "password_hash": "",  # Will be set during first-time setup
                "role": "owner",
                "email": "",
                "full_name": "Kika Shop Owner",
                "created_at": current_time,
                "last_login": None,
                "active": True,
                "password_changed": False
            }
        }
        
        self.save_users()
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user with username and password
        
        Args:
            username: Username to authenticate
            password: Password to verify
            
        Returns:
            Tuple of (success, user_data) where success is boolean and
            user_data is user dict if successful, None otherwise
        """
        # Normalize username (case-insensitive login)
        username_lower = username.lower()
        
        # Find user (case-insensitive match)
        user_key = None
        for key in self.users.keys():
            if key.lower() == username_lower:
                user_key = key
                break
        
        if not user_key or user_key not in self.users:
            return False, None
        
        user = self.users[user_key]
        
        # Check if user is active
        if not user.get('active', True):
            return False, None
        
        # Check if password is set
        if not user.get('password_hash'):
            return False, None
        
        # Verify password
        if self._verify_password(user['password_hash'], password):
            # Update last login time
            user['last_login'] = datetime.now().isoformat()
            self.save_users()
            
            return True, user
        
        return False, None
    
    def user_exists(self, username: str) -> bool:
        """
        Check if a user exists
        
        Args:
            username: Username to check
            
        Returns:
            True if user exists, False otherwise
        """
        return username in self.users
    
    def add_worker(self, username: str, email: str, full_name: str) -> Tuple[bool, str]:
        """
        Add a new worker account
        
        Args:
            username: Worker's username
            email: Worker's email address
            full_name: Worker's full name
            
        Returns:
            Tuple of (success, message/temp_password)
        """
        # Validate inputs
        if not username or not username.strip():
            return False, "Username is required"
        
        if not email or '@' not in email:
            return False, "Valid email is required"
        
        if not full_name or not full_name.strip():
            return False, "Full name is required"
        
        # Check if username already exists
        if self.user_exists(username):
            return False, "Username already exists"
        
        # Generate temporary password
        temp_password = secrets.token_urlsafe(8)
        
        # Create worker account
        self.users[username] = {
            "username": username,
            "password_hash": self._hash_password(temp_password),
            "role": "worker",
            "email": email,
            "full_name": full_name,
            "created_at": datetime.now().isoformat(),
            "last_login": None,
            "active": True,
            "password_changed": False,
            "permissions": ["view_inventory", "update_inventory"]
        }
        
        if self.save_users():
            return True, temp_password
        else:
            return False, "Failed to save user data"
    
    def change_password(self, username: str, new_password: str) -> bool:
        """
        Change password for any user
        
        Args:
            username: User whose password to change
            new_password: New password
            
        Returns:
            True if successful, False otherwise
        """
        if username not in self.users:
            return False
        
        if len(new_password) < 6:
            return False
        
        # Update password
        self.users[username]["password_hash"] = self._hash_password(new_password)
        
        # Mark that password has been changed (for workers)
        if self.users[username].get("role") == "worker":
            self.users[username]["password_changed"] = True
        
        self.users[username]["last_password_change"] = datetime.now().isoformat()
        
        return self.save_users()
    
    def reset_worker_password(self, username: str) -> Tuple[bool, str]:
        """
        Reset worker password to temporary password (admin function)
        
        Args:
            username: Worker username
            
        Returns:
            Tuple of (success, temp_password)
        """
        if username not in self.users:
            return False, "User not found"
        
        if self.users[username].get("role") != "worker":
            return False, "Can only reset worker passwords"
        
        # Generate new temporary password
        temp_password = secrets.token_urlsafe(8)
        
        # Set temporary password
        self.users[username]["password_hash"] = self._hash_password(temp_password)
        self.users[username]["password_changed"] = False
        self.users[username]["last_password_change"] = datetime.now().isoformat()
        
        if self.save_users():
            return True, temp_password
        else:
            return False, "Failed to save password"
    
    def update_user(self, username: str, updates: Dict) -> bool:
        """
        Update user information
        
        Args:
            username: User to update
            updates: Dictionary of fields to update
            
        Returns:
            True if successful, False otherwise
        """
        if username not in self.users:
            return False
        
        # Don't allow certain fields to be updated via this method
        protected_fields = ["username", "password_hash", "role", "created_at"]
        
        for key, value in updates.items():
            if key not in protected_fields:
                self.users[username][key] = value
        
        return self.save_users()
    
    def delete_user(self, username: str) -> bool:
        """
        Delete a user (only workers can be deleted)
        
        Args:
            username: User to delete
            
        Returns:
            True if successful, False otherwise
        """
        if username not in self.users:
            return False
        
        # Don't allow deletion of admin or owner
        user_role = self.users[username].get("role")
        if user_role in ["admin", "owner"]:
            return False
        
        # Soft delete: mark as inactive
        self.users[username]["active"] = False
        self.users[username]["deleted_at"] = datetime.now().isoformat()
        
        return self.save_users()
    
    def get_user(self, username: str) -> Optional[Dict]:
        """
        Get user data by username
        
        Args:
            username: Username to look up
            
        Returns:
            User data dict or None if not found
        """
        return self.users.get(username)
    
    def get_all_workers(self) -> Dict:
        """
        Get all active worker accounts
        
        Returns:
            Dictionary of worker usernames to their data
        """
        workers = {}
        for username, user_data in self.users.items():
            if user_data.get("role") == "worker" and user_data.get("active", True):
                workers[username] = user_data
        
        return workers
    
    def get_all_users(self) -> Dict:
        """
        Get all users (admin, owner, and workers)
        
        Returns:
            Dictionary of all users
        """
        return self.users.copy()
    
    def count_users(self) -> Dict[str, int]:
        """
        Count users by role
        
        Returns:
            Dictionary with counts by role
        """
        counts = {
            "admin": 0,
            "owner": 0,
            "worker": 0,
            "total": 0
        }
        
        for user_data in self.users.values():
            if user_data.get("active", True):
                role = user_data.get("role", "worker")
                if role in counts:
                    counts[role] += 1
                counts["total"] += 1
        
        return counts
    
    def has_permission(self, username: str, permission: str) -> bool:
        """
        Check if user has specific permission
        
        Args:
            username: User to check
            permission: Permission to verify
            
        Returns:
            True if user has permission, False otherwise
        """
        if username not in self.users:
            return False
        
        user = self.users[username]
        
        # Role-based permissions
        role = user.get("role")
        
        # Admin has all permissions
        if role == "admin":
            return True
        
        # Owner permissions
        if role == "owner":
            owner_permissions = [
                "view_inventory", "view_reports", "view_workers",
                "export_data", "view_analytics"
            ]
            return permission in owner_permissions
        
        # Worker permissions (check individual permissions)
        if role == "worker":
            user_permissions = user.get("permissions", [])
            return permission in user_permissions
        
        return False
    
    def set_user_permissions(self, username: str, permissions: List[str]) -> bool:
        """
        Set permissions for a worker
        
        Args:
            username: Worker username
            permissions: List of permission strings
            
        Returns:
            True if successful, False otherwise
        """
        if username not in self.users:
            return False
        
        if self.users[username].get("role") != "worker":
            return False
        
        self.users[username]["permissions"] = permissions
        return self.save_users()
    
    def validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """
        Validate password strength
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, message)
        """
        if len(password) < 6:
            return False, "Password must be at least 6 characters"
        
        if len(password) > 50:
            return False, "Password too long (max 50 characters)"
        
        # Basic strength checks (optional, can be enhanced)
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not has_letter or not has_digit:
            return True, "Password accepted (consider adding letters and numbers for strength)"
        
        return True, "Password is strong"
    
    def create_backup(self, backup_file: str = None) -> bool:
        """
        Create a backup of user data
        
        Args:
            backup_file: Path to backup file (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not backup_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{self.users_file}.backup_{timestamp}"
        
        try:
            with open(backup_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            return True
        except IOError as e:
            print(f"Error creating backup: {e}")
            return False
    
    def restore_from_backup(self, backup_file: str) -> bool:
        """
        Restore user data from backup
        
        Args:
            backup_file: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)
            
            # Validate backup structure
            if not isinstance(backup_data, dict):
                return False
            
            # Merge with existing users (backup takes precedence)
            self.users.update(backup_data)
            return self.save_users()
            
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error restoring from backup: {e}")
            return False

# Helper function for Flask integration
def login_required(role=None):
    """
    Decorator factory for Flask route protection
    
    Usage:
        @app.route('/admin')
        @login_required(role='admin')
        def admin_page():
            return "Admin page"
    """
    from functools import wraps
    from flask import session, redirect, url_for, flash
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is logged in
            if 'username' not in session:
                flash('Please log in first', 'warning')
                return redirect(url_for('login'))
            
            # If role is specified, check if user has that role
            if role and session.get('role') != role:
                flash('You do not have permission to access this page', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Initialize user manager (singleton pattern)
_user_manager_instance = None

def get_user_manager(users_file='users.json'):
    """
    Get or create UserManager instance (singleton)
    
    Args:
        users_file: Path to users database file
        
    Returns:
        UserManager instance
    """
    global _user_manager_instance
    
    if _user_manager_instance is None:
        _user_manager_instance = UserManager(users_file)
    
    return _user_manager_instance

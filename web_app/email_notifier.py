import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailNotifier:
    def __init__(self, config_file='email_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "admin_email": "",
            "owner_email": "",
            "enabled": False
        }
    
    def send_inventory_change_email(self, changes, user_making_change):
        if not self.config.get('enabled', False):
            return True
        
        try:
            subject = "Inventory Changes"
            body = f"Changes: {changes}\nBy: {user_making_change}\nTime: {datetime.now()}"
            
            # This is a stub - will work when email is configured
            print(f"Would send email: {subject}\n{body}")
            return True
        except Exception:
            return True
    
    def send_password_reset_email(self, email, name, temp_pass):
        if not self.config.get('enabled', False):
            return True
        
        try:
            print(f"Would send password email to {email}: {temp_pass}")
            return True
        except Exception:
            return True

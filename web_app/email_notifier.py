import smtplib
import json
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class EmailNotifier:
    def __init__(self, config_file='email_config.json'):
        """Initialize with config file path"""
        self.config_file = config_file
        self.config = self.load_config()
    
    def load_config(self):
        """Load email configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading email config: {e}")
        
        # Default configuration
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
        """Send email when inventory changes are made"""
        # Check if email is enabled
        if not self.config.get('enabled', False):
            return True  # Return True to not block the app
        
        if not self.config.get('sender_email') or not self.config.get('sender_password'):
            print("Email not configured properly")
            return True
        
        try:
            subject = f"Kika's Shop - Inventory Changes"
            
            changes_html = "<h3>Recent Inventory Changes:</h3><ul>"
            for item_id, new_qty in changes.items():
                changes_html += f"<li>Item ID: {item_id} → New Quantity: {new_qty}</li>"
            changes_html += "</ul>"
            
            body = f"""
            <html>
            <body>
                <h2>📦 Inventory Update</h2>
                <p>Changes were made to Kika's Shop inventory:</p>
                {changes_html}
                <p><b>Changed by:</b> {user_making_change}</p>
                <p><b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p><small>Automated notification from Kika's Shop</small></p>
            </body>
            </html>
            """
            
            recipients = []
            if self.config.get("admin_email"):
                recipients.append(self.config["admin_email"])
            if self.config.get("owner_email"):
                recipients.append(self.config["owner_email"])
            
            for recipient in recipients:
                if recipient:
                    self.send_email(recipient, subject, body)
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return True  # Return True to not break the app
    
    def send_password_reset_email(self, recipient_email, worker_name, temp_password):
        """Send password reset email"""
        if not self.config.get('enabled', False):
            return True
        
        if not self.config.get('sender_email'):
            return True
        
        try:
            subject = "Your Kika's Shop Account"
            
            body = f"""
            <html>
            <body>
                <h2>Account Information</h2>
                <p>Hello {worker_name},</p>
                <p>Your Kika's Shop account has been created/reset.</p>
                <p><b>Temporary Password:</b> {temp_password}</p>
                <p>Please login and change your password immediately.</p>
                <hr>
                <p><small>Automated message from Kika's Shop</small></p>
            </body>
            </html>
            """
            
            return self.send_email(recipient_email, subject, body)
        except Exception as e:
            print(f"Error sending password email: {e}")
            return True
    
    def send_email(self, recipient, subject, body):
        """Send actual email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config["sender_email"]
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["sender_email"], self.config["sender_password"])
                server.send_message(msg)
            
            print(f"Email sent to {recipient}")
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False

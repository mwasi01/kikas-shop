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
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "admin_email": "",
            "owner_email": ""
        }
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def send_inventory_change_email(self, changes, user_making_change):
        if not self.config.get("sender_email") or not self.config.get("sender_password"):
            print("Email not configured")
            return False
        
        subject = f"Inventory Changes - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        changes_html = "<h3>Recent Inventory Changes:</h3><ul>"
        for item_id, new_qty in changes.items():
            changes_html += f"<li>Item ID: {item_id} → New Quantity: {new_qty}</li>"
        changes_html += "</ul>"
        
        body = f"""
        <html>
        <body>
            <h2>Inventory Update Notification</h2>
            <p>Changes were made to Kika's Shop inventory:</p>
            {changes_html}
            <p><b>Changed by:</b> {user_making_change}</p>
            <p><b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <p><small>Automated notification from Kika's Shop System</small></p>
        </body>
        </html>
        """
        
        recipients = []
        if self.config.get("admin_email"):
            recipients.append(self.config["admin_email"])
        if self.config.get("owner_email"):
            recipients.append(self.config["owner_email"])
        
        success = True
        for recipient in recipients:
            if not self.send_email(recipient, subject, body):
                success = False
        
        return success
    
    def send_password_reset_email(self, recipient_email, worker_name, temp_password):
        if not self.config.get("sender_email") or not self.config.get("sender_password"):
            print("Email not configured")
            return False
        
        subject = "Your Kika's Shop Account Password"
        
        body = f"""
        <html>
        <body>
            <h2>Account Information</h2>
            <p>Hello {worker_name},</p>
            <p>Your Kika's Shop account has been created.</p>
            <p><b>Username:</b> {worker_name.split()[0].lower() if ' ' in worker_name else worker_name}</p>
            <p><b>Temporary Password:</b> <code>{temp_password}</code></p>
            <p>Please login and change your password immediately.</p>
            <hr>
            <p><small>Automated message from Kika's Shop Management</small></p>
        </body>
        </html>
        """
        
        return self.send_email(recipient_email, subject, body)
    
    def send_email(self, recipient, subject, body):
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
            
            print(f"✓ Email sent to {recipient}")
            return True
            
        except Exception as e:
            print(f"✗ Failed to send email to {recipient}: {e}")
            return False

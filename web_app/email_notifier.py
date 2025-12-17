# web_app/email_notifier.py - CORRECTED VERSION
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
    
    def save_config(self):
        """Save email configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving email config: {e}")
            return False
    
    def send_inventory_change_email(self, changes, user_making_change):
        """Send email when inventory changes are made"""
        
        # Check if email is enabled and configured
        if not self.config.get('enabled', False):
            print("Email notifications are disabled")
            return False
        
        if not self.config.get('sender_email') or not self.config.get('sender_password'):
            print("Email not configured properly")
            return False
        
        try:
            subject = f"Kika's Shop - Inventory Changes - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            # Format changes
            changes_html = "<h3>Recent Inventory Changes:</h3><ul>"
            for item_id, new_qty in changes.items():
                changes_html += f"<li>Item ID: {item_id} → New Quantity: {new_qty}</li>"
            changes_html += "</ul>"
            
            body = f"""
            <html>
            <body>
                <h2>📦 Inventory Update Notification</h2>
                <p>Changes were made to Kika's Shop inventory system:</p>
                {changes_html}
                <p><b>Changed by:</b> {user_making_change}</p>
                <p><b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p><small>This is an automated notification from Kika's Shop Inventory System</small></p>
            </body>
            </html>
            """
            
            # Send to configured recipients
            recipients = []
            if self.config.get("admin_email"):
                recipients.append(self.config["admin_email"])
            if self.config.get("owner_email"):
                recipients.append(self.config["owner_email"])
            
            success = True
            for recipient in recipients:
                if recipient:  # Only send if email is not empty
                    if not self.send_email(recipient, subject, body):
                        success = False
            
            return success
            
        except Exception as e:
            print(f"Error sending inventory change email: {e}")
            return False
    
    def send_password_reset_email(self, recipient_email, worker_name, temp_password):
        """Send password reset email to worker"""
        
        # Check if email is enabled
        if not self.config.get('enabled', False):
            print("Email notifications are disabled")
            return False
        
        if not self.config.get('sender_email') or not self.config.get('sender_password'):
            print("Email not configured properly")
            return False
        
        try:
            subject = "Your Kika's Shop Account Password"
            
            # Extract username from full name
            username = worker_name.split()[0].lower() if ' ' in worker_name else worker_name.lower()
            
            body = f"""
            <html>
            <body>
                <h2>👤 Account Information</h2>
                <p>Hello {worker_name},</p>
                <p>Your Kika's Shop account has been created/reset.</p>
                <p><b>Username:</b> {username}</p>
                <p><b>Temporary Password:</b> <code>{temp_password}</code></p>
                <p><b>Instructions:</b></p>
                <ol>
                    <li>Go to: [Your Website URL]</li>
                    <li>Login with the username and temporary password above</li>
                    <li>You will be prompted to change your password immediately</li>
                </ol>
                <p><b>Important:</b> Do not share this password with anyone.</p>
                <hr>
                <p><small>This is an automated message from Kika's Shop Management System</small></p>
            </body>
            </html>
            """
            
            return self.send_email(recipient_email, subject, body)
            
        except Exception as e:
            print(f"Error sending password reset email: {e}")
            return False
    
    def send_email(self, recipient, subject, body):
        """Send actual email using SMTP"""
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config["sender_email"]
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Attach HTML body
            msg.attach(MIMEText(body, 'html'))
            
            # Connect to SMTP server
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["sender_email"], self.config["sender_password"])
                server.send_message(msg)
            
            print(f"✓ Email sent successfully to {recipient}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("✗ Email authentication failed. Check your email and app password.")
            return False
        except Exception as e:
            print(f"✗ Failed to send email to {recipient}: {str(e)}")
            return False
    
    def update_config(self, new_config):
        """Update email configuration"""
        self.config.update(new_config)
        return self.save_config()
    
    def test_connection(self):
        """Test email connection"""
        try:
            with smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"]) as server:
                server.starttls()
                server.login(self.config["sender_email"], self.config["sender_password"])
                server.quit()
            return True, "Connection successful"
        except smtplib.SMTPAuthenticationError:
            return False, "Authentication failed. Check email/password."
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

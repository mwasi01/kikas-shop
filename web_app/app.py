from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-123')

# Try to import modules
try:
    from auth import UserManager
    from email_notifier import EmailNotifier
    
    user_manager = UserManager('users.json')
    email_notifier = EmailNotifier('email_config.json')
except ImportError as e:
    print(f"Warning: Could not import modules: {e}")
    # Create dummy classes
    class UserManager:
        def __init__(self, *args): pass
        def authenticate(self, *args): return False, None
        def add_worker(self, *args): return False, "Module not loaded"
        def get_all_workers(self): return {}
    class EmailNotifier:
        def __init__(self, *args): pass
        def send_inventory_change_email(self, *args): return True
    
    user_manager = UserManager()
    email_notifier = EmailNotifier()

# Helper functions
def load_inventory():
    try:
        if os.path.exists('data/inventory.json'):
            with open('data/inventory.json', 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {"items": []}

def save_inventory(data):
    try:
        os.makedirs('data', exist_ok=True)
        with open('data/inventory.json', 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception:
        return False

# Routes
@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Simple hardcoded login for testing
        if username == 'admin' and password == 'admin123':
            session['username'] = 'admin'
            session['role'] = 'admin'
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        elif username == 'kika' and password == 'kika123':
            session['username'] = 'kika'
            session['role'] = 'owner'
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    inventory = load_inventory()
    total_items = sum(item.get('quantity', 0) for item in inventory.get('items', []))
    
    return render_template('dashboard.html',
                         username=session['username'],
                         role=session.get('role', 'worker'),
                         total_items=total_items)

@app.route('/inventory')
def inventory_page():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    data = load_inventory()
    return render_template('inventory.html', items=data.get('items', []))

@app.route('/api/inventory', methods=['POST'])
def update_inventory():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not logged in'})
    
    data = request.json
    changes = data.get('changes', {})
    
    # Update inventory
    inventory = load_inventory()
    for item_id, new_qty in changes.items():
        for item in inventory['items']:
            if str(item.get('id')) == str(item_id):
                item['quantity'] = new_qty
    
    save_inventory(inventory)
    
    # Send email notification
    try:
        email_notifier.send_inventory_change_email(
            changes, 
            f"{session['username']} ({session.get('role', 'worker')})"
        )
    except Exception as e:
        print(f"Email error: {e}")
    
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully')
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

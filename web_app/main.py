# app.py - COMPLETE WORKING VERSION
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit
import json
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = 'kika_shop_inventory_secret_key_2025'
socketio = SocketIO(app)

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('dashboard.html', username=session['user_id'])

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Create users.json if it doesn't exist
        if not os.path.exists('users.json'):
            with open('users.json', 'w') as f:
                json.dump({'admin': 'admin123', 'manager': 'shop123', 'kika': 'kika123'}, f)
        
        # Check credentials
        try:
            with open('users.json', 'r') as f:
                users = json.load(f)
                if username in users and users[username] == password:
                    session['user_id'] = username
                    print(f"DEBUG: Login successful for {username}, redirecting to /")
                    return redirect(url_for('index'))  # This should redirect!
        except Exception as e:
            print(f"DEBUG: Error reading users.json: {e}")
        
        # If we get here, login failed
        return render_template('login.html', error='Invalid username or password')
    
    # GET request - show login form
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# API endpoints for inventory
@app.route('/api/inventory')
@login_required
def get_inventory():
    try:
        # Try to load from shared location with Kivy app
        shared_path = '../shared/inventory.json'
        local_path = 'data/inventory.json'
        
        for path in [shared_path, local_path]:
            try:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        inventory = json.load(f)
                    return jsonify(inventory)
            except:
                continue
        
        # Return empty if no file found
        return jsonify({'items': []})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update_quantity', methods=['POST'])
@login_required
def update_quantity():
    try:
        data = request.json
        item_id = data.get('item_id')
        new_quantity = data.get('quantity')
        
        # Load current inventory
        inventory_path = '../shared/inventory.json'
        if not os.path.exists(inventory_path):
            inventory_path = 'data/inventory.json'
        
        if not os.path.exists(inventory_path):
            return jsonify({'success': False, 'error': 'Inventory file not found'})
        
        with open(inventory_path, 'r') as f:
            inventory = json.load(f)
        
        # Update item
        updated = False
        for item in inventory['items']:
            if item['id'] == item_id:
                item['quantity'] = new_quantity
                item['last_updated'] = datetime.now().isoformat()
                item['updated_by'] = session['user_id']
                updated = True
                break
        
        if updated:
            # Save back
            with open(inventory_path, 'w') as f:
                json.dump(inventory, f, indent=2)
            
            # Also save to other location
            other_path = 'data/inventory.json' if inventory_path == '../shared/inventory.json' else '../shared/inventory.json'
            if os.path.exists(os.path.dirname(other_path)):
                with open(other_path, 'w') as f:
                    json.dump(inventory, f, indent=2)
            
            # Notify via SocketIO
            socketio.emit('inventory_update', inventory)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Item not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/messages')
@login_required
def get_messages():
    try:
        messages_path = '../shared/messages.json'
        if not os.path.exists(messages_path):
            messages_path = 'data/messages.json'
        
        if os.path.exists(messages_path):
            with open(messages_path, 'r') as f:
                messages = json.load(f)
            return jsonify(messages)
        else:
            return jsonify([])
    except:
        return jsonify([])

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    try:
        data = request.json
        message = data.get('message', '').strip()
        
        if not message:
            return jsonify({'success': False, 'error': 'Message cannot be empty'})
        
        msg_data = {
            'sender': session['user_id'],
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to messages file
        messages_path = 'data/messages.json'
        os.makedirs('data', exist_ok=True)
        
        messages = []
        if os.path.exists(messages_path):
            with open(messages_path, 'r') as f:
                try:
                    messages = json.load(f)
                except:
                    messages = []
        
        messages.append(msg_data)
        
        with open(messages_path, 'w') as f:
            json.dump(messages, f, indent=2)
        
        # Also save to shared location
        shared_path = '../shared/messages.json'
        if os.path.exists(os.path.dirname(shared_path)):
            with open(shared_path, 'w') as f:
                json.dump(messages, f, indent=2)
        
        # Broadcast via SocketIO
        socketio.emit('new_message', msg_data)
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# SocketIO events
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    
    # Create default users if not exists
    if not os.path.exists('users.json'):
        with open('users.json', 'w') as f:
            json.dump({
                'admin': 'admin123',
                'manager': 'shop123',
                'kika': 'kika123',
                'worker1': 'worker123',
                'worker2': 'worker456'
            }, f, indent=2)
    
    # Create empty inventory if not exists
    shared_inv = '../shared/inventory.json'
    local_inv = 'data/inventory.json'
    
    if not os.path.exists(shared_inv) and not os.path.exists(local_inv):
        sample_inventory = {
            'items': [
                {
                    'id': 'shirt_001',
                    'name': 'Cotton T-Shirt',
                    'category': 'Shirts',
                    'size': 'M',
                    'color': 'Blue',
                    'price': 25.99,
                    'quantity': 50,
                    'last_updated': datetime.now().isoformat()
                },
                {
                    'id': 'jeans_001',
                    'name': 'Classic Jeans',
                    'category': 'Pants',
                    'size': '32',
                    'color': 'Black',
                    'price': 45.99,
                    'quantity': 30,
                    'last_updated': datetime.now().isoformat()
                }
            ]
        }
        
        # Try shared location first
        if os.path.exists(os.path.dirname(shared_inv)):
            with open(shared_inv, 'w') as f:
                json.dump(sample_inventory, f, indent=2)
        else:
            with open(local_inv, 'w') as f:
                json.dump(sample_inventory, f, indent=2)
    
    print("Starting Kika's Shop Inventory Web App...")
    print("Open http://localhost:5000 in your browser")
    print("Login with: admin / admin123")
    socketio.run(app, debug=True, port=5000)

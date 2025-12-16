# app.py - COMPLETE INVENTORY MANAGEMENT WEB APP
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
                    return redirect(url_for('index'))
        except Exception as e:
            print(f"Error: {e}")
        
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# API endpoints
@app.route('/api/inventory')
@login_required
def get_inventory():
    try:
        inventory = load_inventory()
        return jsonify(inventory)
    except Exception as e:
        return jsonify({'error': str(e), 'items': []}), 500

@app.route('/api/add_item', methods=['POST'])
@login_required
def add_item():
    try:
        data = request.json
        print(f"Adding item: {data}")  # Debug
        
        # Validate required fields
        required = ['name', 'category', 'size', 'color', 'price', 'quantity']
        for field in required:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'})
        
        # Load current inventory
        inventory = load_inventory()
        
        # Create new item
        new_item = {
            'id': f"item_{int(datetime.now().timestamp())}",
            'name': data['name'],
            'category': data['category'],
            'size': data['size'],
            'color': data['color'],
            'price': float(data['price']),
            'quantity': int(data['quantity']),
            'created_by': session['user_id'],
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'updated_by': session['user_id']
        }
        
        # Add to inventory
        inventory['items'].append(new_item)
        
        # Save inventory
        save_inventory(inventory)
        
        # Broadcast update
        socketio.emit('inventory_update', inventory)
        
        return jsonify({'success': True, 'item': new_item})
        
    except Exception as e:
        print(f"Error adding item: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_item', methods=['POST'])
@login_required
def update_item():
    try:
        data = request.json
        item_id = data.get('id')
        
        if not item_id:
            return jsonify({'success': False, 'error': 'Item ID is required'})
        
        inventory = load_inventory()
        
        # Find and update item
        updated = False
        for item in inventory['items']:
            if item['id'] == item_id:
                # Update fields
                item['name'] = data.get('name', item['name'])
                item['category'] = data.get('category', item['category'])
                item['size'] = data.get('size', item['size'])
                item['color'] = data.get('color', item['color'])
                item['price'] = float(data.get('price', item['price']))
                item['quantity'] = int(data.get('quantity', item['quantity']))
                item['last_updated'] = datetime.now().isoformat()
                item['updated_by'] = session['user_id']
                updated = True
                break
        
        if updated:
            save_inventory(inventory)
            socketio.emit('inventory_update', inventory)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Item not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_item', methods=['POST'])
@login_required
def delete_item():
    try:
        data = request.json
        item_id = data.get('id')
        
        if not item_id:
            return jsonify({'success': False, 'error': 'Item ID is required'})
        
        inventory = load_inventory()
        
        # Filter out the item to delete
        original_count = len(inventory['items'])
        inventory['items'] = [item for item in inventory['items'] if item['id'] != item_id]
        
        if len(inventory['items']) < original_count:
            save_inventory(inventory)
            socketio.emit('inventory_update', inventory)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Item not found'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/update_quantity', methods=['POST'])
@login_required
def update_quantity():
    try:
        data = request.json
        item_id = data.get('item_id')
        new_quantity = int(data.get('quantity', 0))
        
        inventory = load_inventory()
        
        for item in inventory['items']:
            if item['id'] == item_id:
                old_quantity = item['quantity']
                item['quantity'] = new_quantity
                item['last_updated'] = datetime.now().isoformat()
                item['updated_by'] = session['user_id']
                
                save_inventory(inventory)
                
                # Calculate discrepancy
                discrepancy = new_quantity - old_quantity
                
                socketio.emit('inventory_update', inventory)
                return jsonify({
                    'success': True, 
                    'discrepancy': discrepancy,
                    'old_quantity': old_quantity
                })
        
        return jsonify({'success': False, 'error': 'Item not found'})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analytics')
@login_required
def get_analytics():
    try:
        inventory = load_inventory()
        
        total_items = 0
        total_value = 0
        category_counts = {}
        
        for item in inventory['items']:
            total_items += item['quantity']
            item_value = item['price'] * item['quantity']
            total_value += item_value
            
            category = item['category']
            if category not in category_counts:
                category_counts[category] = 0
            category_counts[category] += item['quantity']
        
        return jsonify({
            'success': True,
            'total_items': total_items,
            'total_value': total_value,
            'category_counts': category_counts,
            'currency': 'KSH'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Helper functions
def load_inventory():
    """Load inventory from shared or local file"""
    shared_path = '../shared/inventory.json'
    local_path = 'data/inventory.json'
    
    # Try shared location first
    for path in [shared_path, local_path]:
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except:
            continue
    
    # Return empty inventory if no file exists
    return {'items': []}

def save_inventory(inventory):
    """Save inventory to both shared and local locations"""
    # Save to local
    os.makedirs('data', exist_ok=True)
    local_path = 'data/inventory.json'
    with open(local_path, 'w') as f:
        json.dump(inventory, f, indent=2)
    
    # Save to shared location if possible
    shared_path = '../shared/inventory.json'
    if os.path.exists(os.path.dirname(shared_path)):
        with open(shared_path, 'w') as f:
            json.dump(inventory, f, indent=2)

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    
    # Create default users if not exists
    if not os.path.exists('users.json'):
        with open('users.json', 'w') as f:
            json.dump({
                'admin': 'admin123',
                'manager': 'shop123',
                'kika': 'kika123'
            }, f, indent=2)
    
    print("=" * 50)
    print("KIKA'S SHOP - INVENTORY MANAGEMENT SYSTEM")
    print("=" * 50)
    print("Web App running on: http://localhost:5000")
    print("Login credentials:")
    print("  - Username: admin | Password: admin123")
    print("  - Username: manager | Password: shop123")
    print("  - Username: kika | Password: kika123")
    print("=" * 50)
   
    port = int(os.environ.get('PORT', 5000)) 
    socketio.run(app, debug=True, port=5000)

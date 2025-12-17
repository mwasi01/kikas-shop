import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Initialize managers
from auth import UserManager
from email_notifier import EmailNotifier

user_manager = UserManager('users.json')
email_notifier = EmailNotifier('email_config.json')

# ============= HELPER FUNCTIONS =============
def load_inventory():
    try:
        if os.path.exists('data/inventory.json'):
            with open('data/inventory.json', 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading inventory: {e}")
    return {"items": [], "last_updated": datetime.now().isoformat()}

def save_inventory(inventory_data):
    try:
        os.makedirs('data', exist_ok=True)
        inventory_data['last_updated'] = datetime.now().isoformat()
        with open('data/inventory.json', 'w') as f:
            json.dump(inventory_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving inventory: {e}")
        return False

# ============= ROUTES =============
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
        
        authenticated, user = user_manager.authenticate(username, password)
        
        if authenticated:
            session['username'] = username
            session['role'] = user.get('role', 'worker')
            session['full_name'] = user.get('full_name', username)
            
            if session['role'] == 'worker' and not user.get('password_changed', False):
                return redirect(url_for('change_password_first'))
            
            flash(f'Welcome back, {session["full_name"]}!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    inventory = load_inventory()
    total_items = sum(item.get('quantity', 0) for item in inventory.get('items', []))
    total_value = sum(item.get('quantity', 0) * item.get('price', 0) for item in inventory.get('items', []))
    
    return render_template('dashboard.html',
                         username=session['username'],
                         role=session['role'],
                         total_items=total_items,
                         total_value=total_value)

@app.route('/inventory')
def inventory():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    inventory_data = load_inventory()
    return render_template('inventory.html',
                         items=inventory_data.get('items', []),
                         role=session.get('role'))

@app.route('/api/inventory', methods=['GET', 'POST'])
def api_inventory():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    if request.method == 'GET':
        inventory_data = load_inventory()
        return jsonify(inventory_data)
    
    elif request.method == 'POST':
        data = request.json
        action = data.get('action')
        
        if action == 'update':
            changes = data.get('changes', {})
            inventory_data = load_inventory()
            
            for item_id, new_quantity in changes.items():
                for item in inventory_data['items']:
                    if str(item.get('id')) == str(item_id):
                        item['quantity'] = new_quantity
                        item['last_updated'] = datetime.now().isoformat()
                        item['updated_by'] = session['username']
            
            if save_inventory(inventory_data):
                # Send email notification
                try:
                    email_notifier.send_inventory_change_email(
                        changes=changes,
                        user_making_change=f"{session['username']} ({session['role']})"
                    )
                except Exception as e:
                    print(f"Email notification failed: {e}")
                
                return jsonify({'success': True, 'message': 'Inventory updated'})
            else:
                return jsonify({'success': False, 'error': 'Failed to save inventory'})
        
        elif action == 'add_item':
            new_item = data.get('item', {})
            if not new_item.get('name'):
                return jsonify({'success': False, 'error': 'Item name is required'})
            
            inventory_data = load_inventory()
            new_item['id'] = f"item_{int(datetime.now().timestamp())}"
            new_item['created_at'] = datetime.now().isoformat()
            new_item['created_by'] = session['username']
            
            inventory_data['items'].append(new_item)
            
            if save_inventory(inventory_data):
                return jsonify({'success': True, 'message': 'Item added'})
            else:
                return jsonify({'success': False, 'error': 'Failed to save item'})
        
        return jsonify({'success': False, 'error': 'Invalid action'})

@app.route('/manage-workers')
def manage_workers():
    if 'username' not in session or session.get('role') != 'admin':
        flash('Access denied')
        return redirect(url_for('dashboard'))
    
    workers = user_manager.get_all_workers()
    return render_template('manage_workers.html', workers=workers)

@app.route('/api/manage-workers', methods=['POST'])
def api_manage_workers():
    if 'username' not in session or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    action = data.get('action')
    
    if action == 'add':
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        full_name = data.get('full_name', '').strip()
        
        if not username or not email or not full_name:
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        success, result = user_manager.add_worker(username, email, full_name)
        
        if success:
            # Send email
            try:
                email_notifier.send_password_reset_email(email, full_name, result)
            except Exception as e:
                print(f"Failed to send email: {e}")
            
            return jsonify({
                'success': True,
                'temp_password': result,
                'message': f'Worker added. Temp password: {result}'
            })
        else:
            return jsonify({'success': False, 'error': result})
    
    return jsonify({'success': False, 'error': 'Invalid action'})

@app.route('/change-password')
def change_password_first():
    if 'username' not in session or session.get('role') != 'worker':
        return redirect(url_for('dashboard'))
    
    user = user_manager.users.get(session['username'], {})
    if user.get('password_changed', True):
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html', first_time=True)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# web_app/app.py - COMPLETE VERSION FOR RENDER DEPLOYMENT
import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify

# Import our custom modules
try:
    from auth import UserManager
    from email_notifier import EmailNotifier
except ImportError:
    # Create dummy classes if modules don't exist yet
    class UserManager:
        def __init__(self, *args, **kwargs):
            self.users = {}
        def authenticate(self, *args, **kwargs):
            return False, None
        def change_password(self, *args, **kwargs):
            return False
    class EmailNotifier:
        def send_inventory_change_email(self, *args, **kwargs):
            pass

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Initialize managers
user_manager = UserManager('users.json')
email_notifier = EmailNotifier('email_config.json')

# Inventory file path
INVENTORY_FILE = 'data/inventory.json'

# ============= HELPER FUNCTIONS =============
def load_inventory():
    """Load inventory from JSON file"""
    try:
        if os.path.exists(INVENTORY_FILE):
            with open(INVENTORY_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading inventory: {e}")
    return {"items": [], "last_updated": datetime.now().isoformat()}

def save_inventory(inventory_data):
    """Save inventory to JSON file"""
    try:
        os.makedirs(os.path.dirname(INVENTORY_FILE), exist_ok=True)
        inventory_data['last_updated'] = datetime.now().isoformat()
        with open(INVENTORY_FILE, 'w') as f:
            json.dump(inventory_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving inventory: {e}")
        return False

def is_authenticated():
    """Check if user is logged in"""
    return 'username' in session

def requires_role(required_role):
    """Decorator to check user role"""
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not is_authenticated():
                flash('Please login first')
                return redirect(url_for('login'))
            if session.get('role') != required_role and session.get('role') != 'admin':
                flash('You do not have permission to access this page')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ============= ROUTES =============
@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if not is_authenticated():
        return redirect(url_for('login'))
    
    # Check if first-time setup is needed
    if user_manager.users.get('admin', {}).get('password_hash', '') == '':
        return redirect(url_for('setup'))
    
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    # Check if setup is needed
    admin_user = user_manager.users.get('admin', {})
    setup_needed = admin_user.get('password_hash', '') == ''
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        # Handle first-time setup
        if setup_needed and username in ['admin', 'kika']:
            if len(password) < 6:
                flash('Password must be at least 6 characters')
                return render_template('login.html', setup_required=True)
            
            # Set password for admin or owner
            user_manager.change_password(username, password)
            
            # Ask for email on first setup
            if username == 'admin':
                email = request.form.get('email', '').strip()
                if email:
                    user_manager.users[username]['email'] = email
            elif username == 'kika':
                email = request.form.get('email', '').strip()
                if email:
                    user_manager.users[username]['email'] = email
            
            user_manager.save_users()
            flash(f'Password set for {username}. Please login with the new password.')
            return redirect(url_for('login'))
        
        # Normal login authentication
        authenticated, user = user_manager.authenticate(username, password)
        
        if authenticated:
            # Set session data
            session['username'] = username
            session['role'] = user.get('role', 'worker')
            session['full_name'] = user.get('full_name', username)
            session['email'] = user.get('email', '')
            
            # Force password change for workers with temporary passwords
            if session['role'] == 'worker' and not user.get('password_changed', False):
                return redirect(url_for('change_password_first'))
            
            flash(f'Welcome back, {session["full_name"]}!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html', setup_required=setup_needed)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    """First-time setup page for admin and owner"""
    if request.method == 'POST':
        admin_pass = request.form.get('admin_password', '').strip()
        owner_pass = request.form.get('owner_password', '').strip()
        admin_email = request.form.get('admin_email', '').strip()
        owner_email = request.form.get('owner_email', '').strip()
        
        # Validate passwords
        if len(admin_pass) < 6 or len(owner_pass) < 6:
            flash('Passwords must be at least 6 characters long')
            return render_template('setup.html')
        
        # Validate emails
        if '@' not in admin_email or '@' not in owner_email:
            flash('Please enter valid email addresses')
            return render_template('setup.html')
        
        # Set passwords and emails
        user_manager.change_password('admin', admin_pass)
        user_manager.change_password('kika', owner_pass)
        user_manager.users['admin']['email'] = admin_email
        user_manager.users['kika']['email'] = owner_email
        user_manager.save_users()
        
        # Save email configuration
        email_notifier.config['admin_email'] = admin_email
        email_notifier.config['owner_email'] = owner_email
        email_notifier.save_config()
        
        flash('Setup completed successfully! You can now login.')
        return redirect(url_for('login'))
    
    return render_template('setup.html')

@app.route('/dashboard')
def dashboard():
    """Main dashboard after login"""
    if not is_authenticated():
        return redirect(url_for('login'))
    
    # Load inventory data
    inventory = load_inventory()
    
    # Calculate statistics
    total_items = sum(item.get('quantity', 0) for item in inventory.get('items', []))
    total_value = sum(item.get('quantity', 0) * item.get('price', 0) for item in inventory.get('items', []))
    
    return render_template('dashboard.html',
                         username=session['username'],
                         role=session['role'],
                         full_name=session['full_name'],
                         total_items=total_items,
                         total_value=total_value)

@app.route('/inventory')
def inventory():
    """Inventory management page"""
    if not is_authenticated():
        return redirect(url_for('login'))
    
    inventory_data = load_inventory()
    return render_template('inventory.html',
                         items=inventory_data.get('items', []),
                         role=session.get('role'))

@app.route('/api/inventory', methods=['GET', 'POST'])
def api_inventory():
    """API endpoint for inventory operations"""
    if not is_authenticated():
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
            
            # Apply changes
            for item_id, new_quantity in changes.items():
                for item in inventory_data['items']:
                    if str(item.get('id')) == str(item_id):
                        old_quantity = item.get('quantity', 0)
                        item['quantity'] = new_quantity
                        item['last_updated'] = datetime.now().isoformat()
                        item['updated_by'] = session['username']
            
            # Save inventory
            if save_inventory(inventory_data):
                # Send email notification
                try:
                    if changes:
                        email_notifier.send_inventory_change_email(
                            changes=changes,
                            user_making_change=f"{session['full_name']} ({session['role']})"
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
            new_item['last_updated'] = datetime.now().isoformat()
            
            inventory_data['items'].append(new_item)
            
            if save_inventory(inventory_data):
                return jsonify({'success': True, 'message': 'Item added', 'item_id': new_item['id']})
            else:
                return jsonify({'success': False, 'error': 'Failed to save item'})
        
        return jsonify({'success': False, 'error': 'Invalid action'})

@app.route('/change-password-first')
def change_password_first():
    """Force password change for first-time workers"""
    if not is_authenticated() or session.get('role') != 'worker':
        return redirect(url_for('login'))
    
    user = user_manager.users.get(session['username'], {})
    if user.get('password_changed', True):
        return redirect(url_for('dashboard'))
    
    return render_template('change_password.html', first_time=True)

@app.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change password page"""
    if not is_authenticated():
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '').strip()
        new_password = request.form.get('new_password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if new_password != confirm_password:
            flash('New passwords do not match')
            return render_template('change_password.html')
        
        if len(new_password) < 6:
            flash('New password must be at least 6 characters')
            return render_template('change_password.html')
        
        authenticated, _ = user_manager.authenticate(session['username'], current_password)
        if not authenticated:
            flash('Current password is incorrect')
            return render_template('change_password.html')
        
        if user_manager.change_password(session['username'], new_password):
            flash('Password changed successfully')
            if session.get('role') == 'worker':
                session['password_changed'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Failed to change password')
    
    return render_template('change_password.html', first_time=False)

@app.route('/manage-workers')
@requires_role('admin')
def manage_workers():
    """Admin page to manage workers"""
    workers = user_manager.get_all_workers()
    return render_template('manage_workers.html', workers=workers)

@app.route('/api/manage-workers', methods=['POST'])
def api_manage_workers():
    """API for managing workers"""
    if not is_authenticated() or session.get('role') != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.json
    action = data.get('action')
    
    if action == 'add':
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        full_name = data.get('full_name', '').strip()
        
        if not username or not email or not full_name:
            return jsonify({'success': False, 'error': 'All fields are required'})
        
        if '@' not in email:
            return jsonify({'success': False, 'error': 'Invalid email address'})
        
        success, result = user_manager.add_worker(username, email, full_name)
        
        if success:
            try:
                email_notifier.send_password_reset_email(email, full_name, result)
            except Exception as e:
                print(f"Failed to send email: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Worker added. Temporary password: {result}',
                'temp_password': result
            })
        else:
            return jsonify({'success': False, 'error': result})
    
    elif action == 'reset_password':
        username = data.get('username', '').strip()
        
        if username not in user_manager.users:
            return jsonify({'success': False, 'error': 'User not found'})
        
        import secrets
        temp_password = secrets.token_urlsafe(8)
        
        if user_manager.change_password(username, temp_password):
            user_manager.users[username]['password_changed'] = False
            user_manager.save_users()
            
            worker = user_manager.users[username]
            try:
                email_notifier.send_password_reset_email(
                    worker['email'],
                    worker['full_name'],
                    temp_password
                )
            except Exception as e:
                print(f"Failed to send email: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Password reset. New temp password: {temp_password}',
                'temp_password': temp_password
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to reset password'})
    
    elif action == 'delete':
        username = data.get('username', '').strip()
        
        if username not in user_manager.users:
            return jsonify({'success': False, 'error': 'User not found'})
        
        if user_manager.users[username]['role'] != 'worker':
            return jsonify({'success': False, 'error': 'Can only delete worker accounts'})
        
        del user_manager.users[username]
        user_manager.save_users()
        
        return jsonify({'success': True, 'message': 'Worker deleted'})
    
    return jsonify({'success': False, 'error': 'Invalid action'})

@app.route('/profile')
def profile():
    """User profile page"""
    if not is_authenticated():
        return redirect(url_for('login'))
    
    user_data = user_manager.users.get(session['username'], {})
    return render_template('profile.html',
                         user=user_data,
                         username=session['username'],
                         role=session['role'])

@app.route('/reports')
@requires_role('admin')
def reports():
    """Reports page for admin and owner"""
    inventory_data = load_inventory()
    
    category_summary = {}
    size_summary = {}
    color_summary = {}
    
    for item in inventory_data.get('items', []):
        category = item.get('category', 'Unknown')
        category_summary[category] = category_summary.get(category, 0) + item.get('quantity', 0)
        
        size = item.get('size', 'Unknown')
        size_summary[size] = size_summary.get(size, 0) + item.get('quantity', 0)
        
        color = item.get('color', 'Unknown')
        color_summary[color] = color_summary.get(color, 0) + item.get('quantity', 0)
    
    return render_template('reports.html',
                         category_summary=category_summary,
                         size_summary=size_summary,
                         color_summary=color_summary,
                         total_items=sum(item.get('quantity', 0) for item in inventory_data.get('items', [])))

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('You have been logged out successfully')
    return redirect(url_for('login'))

@app.route('/health')
def health():
    """Health check endpoint for deployment"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ============= ERROR HANDLERS =============
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error='Internal server error'), 500

# ============= MAIN ENTRY POINT FOR RENDER =============
if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('data', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    # Get port from environment variable or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)

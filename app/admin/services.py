from datetime import datetime
import secrets
import string
from app.extensions import db
from app.models import User, Employee, UserModule, Module, Notification
from app.utils.audit import log_audit
from app.hr import services as hr_services

# ===========================================================================
# USER MANAGEMENT SERVICES
# ===========================================================================
def generate_readable_password():
    """Generate a readable temporary password like 'Welcome@7842'."""
    digits = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f'Welcome@{digits}'

def create_user_and_employee(data, creator_id):
    """Create a User, assign modules, create Employee profile, and initialize leaves."""
    temp_password = generate_readable_password()
    
    selected_ids = set(data.get('modules', []))
    admin_module = Module.query.filter_by(slug='admin').first()
    is_admin_selected = (admin_module and admin_module.id in selected_ids)
    
    user = User(
        username=data.get('username'), 
        email=data.get('email'),
        full_name=data.get('full_name'), 
        phone=data.get('phone'),
        is_admin=is_admin_selected, 
        must_change_password=True
    )
    user.set_password(temp_password)
    db.session.add(user)
    db.session.flush()
    
    # Assign Employee Module automatically
    emp_module = Module.query.filter_by(slug='employee').first()
    if emp_module:
        selected_ids.add(emp_module.id)
        
    for mod_id in selected_ids:
        db.session.add(UserModule(user_id=user.id, module_id=mod_id))
        
    emp = Employee(user_id=user.id, emp_code=f"EMP{user.id:04d}")
    db.session.add(emp)
    db.session.flush()
    
    hr_services.initialize_leave_balances(emp.id)
    
    log_audit(creator_id, 'CREATE', 'User', user.id, f'Created user {user.username}')
    
    return user, temp_password

def update_user(user, data, updater_id):
    """Update user details and module assignments."""
    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    user.full_name = data.get('full_name', user.full_name)
    user.phone = data.get('phone', user.phone)
    user.is_active_user = data.get('is_active_user', user.is_active_user)
    
    if data.get('password'):
        user.set_password(data['password'])
        
    UserModule.query.filter_by(user_id=user.id).delete()
    selected_ids = set(data.get('modules', []))
    
    admin_module = Module.query.filter_by(slug='admin').first()
    user.is_admin = (admin_module and admin_module.id in selected_ids)
    
    emp_module = Module.query.filter_by(slug='employee').first()
    if emp_module:
        selected_ids.add(emp_module.id)
        
    for mod_id in selected_ids:
        db.session.add(UserModule(user_id=user.id, module_id=mod_id))
        
    log_audit(updater_id, 'UPDATE', 'User', user.id, f'Updated user {user.username}')
    return user

# ===========================================================================
# NOTIFICATION SERVICES
# ===========================================================================
def broadcast_notification(title, message, category, target_str, sender_id):
    """Send a notification to one user or all users."""
    count = 0
    if target_str == 'all':
        users = User.query.filter_by(is_active_user=True).all()
        for u in users:
            n = Notification(user_id=u.id, title=title, message=message, category=category)
            db.session.add(n)
            count += 1
    elif target_str:
        n = Notification(user_id=int(target_str), title=title, message=message, category=category)
        db.session.add(n)
        count = 1
        
    if count > 0:
        log_audit(sender_id, 'SEND', 'Notification', None, f'Sent "{title}" to {count} user(s)')
        
    return count

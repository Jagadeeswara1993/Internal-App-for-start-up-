import re
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db



# ---------------------------------------------------------------------------
# Password complexity validation
# ---------------------------------------------------------------------------
def validate_password_complexity(password):
    """Validate password meets complexity requirements.
    Returns (valid, error_message)."""
    if len(password) < 8:
        return False, 'Password must be at least 8 characters long'
    if not re.search(r'[A-Z]', password):
        return False, 'Password must contain at least one uppercase letter'
    if not re.search(r'[a-z]', password):
        return False, 'Password must contain at least one lowercase letter'
    if not re.search(r'[0-9]', password):
        return False, 'Password must contain at least one number'
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, 'Password must contain at least one special character (!@#$%^&* etc.)'
    return True, 'Password meets complexity requirements'


# ---------------------------------------------------------------------------
# Association table: User ↔ Module (many-to-many)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Association table: User ↔ Module (many-to-many)
# ---------------------------------------------------------------------------
class UserModule(db.Model):
    __tablename__ = 'user_modules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'module_id', name='uq_user_module'),)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), default='')
    is_admin = db.Column(db.Boolean, default=False)
    is_active_user = db.Column(db.Boolean, default=True)
    must_change_password = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    modules = db.relationship('Module', secondary='user_modules', backref=db.backref('users', lazy='dynamic'))
    employee = db.relationship('Employee', backref='user', uselist=False, lazy='joined')
    tasks_assigned = db.relationship('Task', backref='assignee', foreign_keys='Task.assigned_to')
    expenses = db.relationship('Expense', backref='submitter', foreign_keys='Expense.submitted_by')
    projects_created = db.relationship('Project', backref='creator', foreign_keys='Project.created_by')
    login_history = db.relationship('LoginHistory', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        # Legacy bcrypt hashes ($2b$, $2a$, $2y$) from older setup
        if self.password_hash.startswith(('$2b$', '$2a$', '$2y$')):
            try:
                import bcrypt
                valid = bcrypt.checkpw(password.encode('utf-8'),
                                       self.password_hash.encode('utf-8'))
                if valid:
                    # Auto-upgrade to Werkzeug's pbkdf2 format
                    self.password_hash = generate_password_hash(password)
                return valid
            except Exception:
                return False
        return check_password_hash(self.password_hash, password)

    @property
    def is_locked(self):
        """Check if the account is currently locked."""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def record_failed_login(self):
        """Increment failed login counter and lock if threshold exceeded."""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        if self.failed_login_attempts >= 3:
            # Lock for 15 minutes
            from datetime import timedelta
            self.locked_until = datetime.utcnow() + timedelta(minutes=15)

    def reset_failed_logins(self):
        """Reset failed login counter after successful login."""
        self.failed_login_attempts = 0
        self.locked_until = None

    def has_module(self, slug):
        """Check if user has access to a module by slug."""
        return any(m.slug == slug for m in self.modules)

    @property
    def is_active(self):
        return self.is_active_user

    def __repr__(self):
        return f'<User {self.username}>'


# ---------------------------------------------------------------------------
# Module (represents an app module: admin, hr, pm, finance, employee)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Module (represents an app module: admin, hr, pm, finance, employee)
# ---------------------------------------------------------------------------
class Module(db.Model):
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), default='')
    icon = db.Column(db.String(50), default='fas fa-cube')

    def __repr__(self):
        return f'<Module {self.slug}>'




# ---------------------------------------------------------------------------
# AuditLog (tracks changes across the system)
# ---------------------------------------------------------------------------
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)         # CREATE, UPDATE, DELETE, APPROVE, REJECT
    entity_type = db.Column(db.String(50), nullable=False)    # Employee, Leave, Attendance, etc.
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, default='')
    ip_address = db.Column(db.String(45), default='')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.action} {self.entity_type}#{self.entity_id}>'




# ===========================================================================
# LOGIN & SECURITY MODELS
# ===========================================================================

# ---------------------------------------------------------------------------
# LoginHistory — Tracks all login activity for auditing
# ---------------------------------------------------------------------------
class LoginHistory(db.Model):
    __tablename__ = 'login_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    login_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45), default='')
    user_agent = db.Column(db.String(500), default='')         # Browser/device info
    status = db.Column(db.String(20), default='Success')       # Success, Failed, Locked
    details = db.Column(db.String(250), default='')

    def __repr__(self):
        return f'<LoginHistory user#{self.user_id} {self.status} at {self.login_at}>'




# ---------------------------------------------------------------------------
# Notification — NEW (system notifications for PM events)
# ---------------------------------------------------------------------------
class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, default='')
    category = db.Column(db.String(30), default='info')       # info, success, warning, danger
    is_read = db.Column(db.Boolean, default=False)
    link = db.Column(db.String(500), default='')               # optional URL to relevant page
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.title} for user#{self.user_id}>'




# ===========================================================================
# HOLIDAY CALENDAR MODEL
# ===========================================================================

# ---------------------------------------------------------------------------
# Holiday — Company-wide holidays managed by Admin/HR
# ---------------------------------------------------------------------------
class Holiday(db.Model):
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    holiday_name = db.Column(db.String(255), nullable=False)
    holiday_date = db.Column(db.Date, nullable=False)
    holiday_day = db.Column(db.String(50), default='')
    holiday_type = db.Column(db.String(100), default='Public')     # Public, Restricted, Optional
    description = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by])

    __table_args__ = (db.UniqueConstraint('holiday_name', 'holiday_date', name='uq_holiday_name_date'),)

    # Convenience properties so existing code using .name / .date keeps working
    @property
    def name(self):
        return self.holiday_name

    @property
    def date(self):
        return self.holiday_date

    def __repr__(self):
        return f'<Holiday {self.holiday_name} on {self.holiday_date}>'



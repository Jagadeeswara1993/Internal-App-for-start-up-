import re
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db



# ===========================================================================
# ADMIN CONFIG TABLES — Admin defines, HR consumes
# ===========================================================================

# ---------------------------------------------------------------------------
# Department (Admin-managed)
# ---------------------------------------------------------------------------
class Department(db.Model):
    __tablename__ = 'departments'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.String(250), default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    designations = db.relationship('Designation', backref='department', lazy='dynamic')
    employees = db.relationship('Employee', backref='department', lazy='dynamic')

    def __repr__(self):
        return f'<Department {self.code}>'


# ---------------------------------------------------------------------------
# Designation (Admin-managed, linked to Department)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Designation (Admin-managed, linked to Department)
# ---------------------------------------------------------------------------
class Designation(db.Model):
    __tablename__ = 'designations'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), nullable=False)
    level = db.Column(db.Integer, default=1)          # 1=Junior, 2=Mid, 3=Senior, 4=Lead, 5=Head
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship('Employee', backref='designation', lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('title', 'department_id', name='uq_title_dept'),)

    def __repr__(self):
        return f'<Designation {self.title}>'


# ---------------------------------------------------------------------------
# Shift (Admin-managed — Morning, Afternoon, Night, etc.)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Shift (Admin-managed — Morning, Afternoon, Night, etc.)
# ---------------------------------------------------------------------------
class Shift(db.Model):
    __tablename__ = 'shifts'

    id = db.Column(db.Integer, primary_key=True)
    shift_name = db.Column(db.String(50), unique=True, nullable=False)    # Morning, Afternoon, Night
    start_time = db.Column(db.String(5), nullable=False)                  # HH:MM
    end_time = db.Column(db.String(5), nullable=False)
    grace_period_mins = db.Column(db.Integer, default=15)
    min_working_hours = db.Column(db.Float, default=8.0)
    late_mark_after_mins = db.Column(db.Integer, default=15)              # Late after start + this
    overtime_eligible = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employees = db.relationship('Employee', backref='shift', lazy='dynamic')

    def __repr__(self):
        return f'<Shift {self.shift_name} {self.start_time}-{self.end_time}>'


# ---------------------------------------------------------------------------
# LeavePolicy (Admin-managed — defines leave types and quotas)
# Optionally linked to Designation for role-based policies.
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# LeavePolicy (Admin-managed — defines leave types and quotas)
# Optionally linked to Designation for role-based policies.
# ---------------------------------------------------------------------------
class LeavePolicy(db.Model):
    __tablename__ = 'leave_policies'

    id = db.Column(db.Integer, primary_key=True)
    leave_type = db.Column(db.String(50), nullable=False)                 # Casual, Sick, Earned, etc.
    designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)  # NULL = all
    total_days = db.Column(db.Integer, nullable=False, default=12)
    is_calendar_days = db.Column(db.Boolean, default=False)               # True = count calendar days (maternity, paternity); False = exclude weekends/holidays
    is_prorated = db.Column(db.Boolean, default=False)                    # True = auto-prorate for mid-year joiners
    carry_forward = db.Column(db.Boolean, default=False)
    max_carry_days = db.Column(db.Integer, default=0)
    monthly_accrual = db.Column(db.Boolean, default=False)
    encashment_allowed = db.Column(db.Boolean, default=False)
    max_per_request = db.Column(db.Integer, nullable=True)                # Max days per single request
    blackout_dates = db.Column(db.Text, default='')                       # JSON: [{"start":"...","end":"..."}]
    description = db.Column(db.String(250), default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    designation = db.relationship('Designation', backref='leave_policies')

    __table_args__ = (db.UniqueConstraint('leave_type', 'designation_id', name='uq_leave_type_desig'),)

    def __repr__(self):
        desig = self.designation.title if self.designation else 'Global'
        return f'<LeavePolicy {self.leave_type} ({self.total_days}d) [{desig}]>'


# ---------------------------------------------------------------------------
# AttendanceRule (Admin-managed — single config row)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# AttendanceRule (Admin-managed — single config row)
# ---------------------------------------------------------------------------
class AttendanceRule(db.Model):
    __tablename__ = 'attendance_rules'

    id = db.Column(db.Integer, primary_key=True)
    work_start = db.Column(db.String(5), default='09:00')    # HH:MM
    work_end = db.Column(db.String(5), default='18:00')
    late_threshold_mins = db.Column(db.Integer, default=15)   # Minutes after work_start to mark "Late"
    half_day_hours = db.Column(db.Float, default=4.0)         # Min hours for half-day
    full_day_hours = db.Column(db.Float, default=8.0)         # Min hours for full-day
    is_active = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<AttendanceRule {self.work_start}-{self.work_end}>'


# ---------------------------------------------------------------------------
# AuditLog (tracks changes across the system)
# ---------------------------------------------------------------------------



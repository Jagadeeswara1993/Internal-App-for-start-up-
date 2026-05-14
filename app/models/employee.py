import re
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db



# ===========================================================================
# HR MODULE MODELS
# ===========================================================================

# ---------------------------------------------------------------------------
# Employee (extends User with HR-specific fields) — UPGRADED
# ---------------------------------------------------------------------------
class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    emp_code = db.Column(db.String(20), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=True)   # NULL = General Shift
    reporting_manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)  # NULL = no manager (senior / goes direct to HR)
    date_of_birth = db.Column(db.Date, nullable=True)
    date_of_joining = db.Column(db.Date, default=date.today)
    salary = db.Column(db.Float, default=0.0)
    bank_account = db.Column(db.String(30), default='')
    pan_number = db.Column(db.String(15), default='')
    aadhar_number = db.Column(db.String(20), default='')
    location = db.Column(db.String(100), default='')
    is_active = db.Column(db.Boolean, default=True)

    # relationships
    leaves = db.relationship('Leave', backref='employee', lazy='dynamic')
    attendance_records = db.relationship('Attendance', backref='employee', lazy='dynamic')
    salary_records = db.relationship('SalaryRecord', backref='employee', lazy='dynamic')
    leave_balances = db.relationship('LeaveBalance', backref='employee', lazy='dynamic')
    documents = db.relationship('EmployeeDocument', backref='employee', lazy='dynamic')
    payroll_inputs = db.relationship('PayrollInput', backref='employee', lazy='dynamic')
    comp_offs = db.relationship('CompOff', backref='employee', lazy='dynamic')
    shift_swap_requests = db.relationship('ShiftSwapRequest', backref='employee', lazy='dynamic')
    timesheets = db.relationship('Timesheet', backref='employee', lazy='dynamic')

    # Self-referential: Employee → Reporting Manager
    reporting_manager = db.relationship('Employee', remote_side='Employee.id',
                                         backref=db.backref('direct_reports', lazy='dynamic'),
                                         foreign_keys=[reporting_manager_id])

    @property
    def department_name(self):
        return self.department.name if self.department else 'Unassigned'

    @property
    def designation_title(self):
        return self.designation.title if self.designation else 'Unassigned'

    @property
    def shift_name(self):
        return self.shift.shift_name if self.shift else 'General'

    @property
    def manager_name(self):
        """Full name of the reporting manager, or 'None' if not assigned."""
        return self.reporting_manager.user.full_name if self.reporting_manager else 'None'

    @property
    def manager_user_id(self):
        """User ID of the reporting manager (for notifications)."""
        return self.reporting_manager.user_id if self.reporting_manager else None

    def __repr__(self):
        return f'<Employee {self.emp_code}>'


# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Leave
# ---------------------------------------------------------------------------
class Leave(db.Model):
    __tablename__ = 'leaves'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    leave_type = db.Column(db.String(30), nullable=False)          # Casual, Sick, Earned
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    total_days = db.Column(db.Float, default=1)
    is_half_day = db.Column(db.Boolean, default=False)             # True = half-day leave (0.5)
    status = db.Column(db.String(20), default='Pending')           # Pending, Approved, Rejected, Cancelled
    reason = db.Column(db.Text, default='')
    rejection_reason = db.Column(db.Text, default='')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    # Multi-step approval workflow
    manager_status = db.Column(db.String(20), default='Pending')   # Pending, Approved, Rejected, N/A
    manager_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    hr_status = db.Column(db.String(20), default='Pending')        # Pending, Approved, Rejected
    hr_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_urgent = db.Column(db.Boolean, default=False)               # Urgent leaves skip manager, go direct to HR
    # Cancellation fields
    cancelled_at = db.Column(db.DateTime, nullable=True)
    cancelled_reason = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    approver = db.relationship('User', foreign_keys=[approved_by])
    manager_approver = db.relationship('User', foreign_keys=[manager_approved_by])
    hr_approver = db.relationship('User', foreign_keys=[hr_approved_by])

    def calc_days(self, is_calendar_days=False):
        """Calculate number of leave days.
        - is_calendar_days=True: simple (end - start + 1) — for statutory leaves.
        - is_calendar_days=False: excludes weekends and holidays.
        - is_half_day=True: always returns 0.5 (single-day half leave)."""
        if self.is_half_day:
            return 0.5
        if not self.start_date or not self.end_date:
            return 0

        from datetime import timedelta

        # Calendar-days mode: count every day including weekends & holidays
        if is_calendar_days:
            return (self.end_date - self.start_date).days + 1

        # Working-days mode: exclude weekends and holidays
        from app.models.core import Holiday
        holidays_in_range = Holiday.query.filter(
            Holiday.holiday_date >= self.start_date,
            Holiday.holiday_date <= self.end_date
        ).all()
        holiday_dates = {h.holiday_date for h in holidays_in_range}
        
        count = 0
        current = self.start_date
        while current <= self.end_date:
            if current.weekday() < 5 and current not in holiday_dates:  # Mon-Fri and not a holiday
                count += 1
            current += timedelta(days=1)
        return count

    def __repr__(self):
        return f'<Leave {self.id} – {self.status}>'


# ---------------------------------------------------------------------------
# LeaveBalance (per employee per leave type)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# LeaveBalance (per employee per leave type)
# ---------------------------------------------------------------------------
class LeaveBalance(db.Model):
    __tablename__ = 'leave_balances'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    leave_type = db.Column(db.String(50), nullable=False)
    total_allocated = db.Column(db.Float, default=0)
    used = db.Column(db.Float, default=0)
    year = db.Column(db.Integer, nullable=False)

    __table_args__ = (db.UniqueConstraint('employee_id', 'leave_type', 'year', name='uq_emp_leave_year'),)

    @property
    def remaining(self):
        return max(0, self.total_allocated - self.used)

    def __repr__(self):
        return f'<LeaveBalance {self.leave_type}: {self.remaining} left>'


# ---------------------------------------------------------------------------
# Attendance — UPGRADED
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Attendance — UPGRADED
# ---------------------------------------------------------------------------
class Attendance(db.Model):
    __tablename__ = 'attendance'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.String(10), default='')     # stored as HH:MM string for SQLite compat
    check_out = db.Column(db.String(10), default='')
    working_hours = db.Column(db.Float, default=0.0)     # Calculated hours
    status = db.Column(db.String(20), default='Present')  # Present, Absent, Half-Day, Late, On Leave
    notes = db.Column(db.String(250), default='')
    is_overnight = db.Column(db.Boolean, default=False)   # Night shift: checkout is next day

    __table_args__ = (db.UniqueConstraint('employee_id', 'date', name='uq_emp_date'),)

    def calc_working_hours(self):
        """Calculate hours between check_in and check_out.
        Handles night shifts (checkout next day) via is_overnight flag."""
        if not self.check_in or not self.check_out:
            return 0.0
        try:
            h1, m1 = map(int, self.check_in.split(':'))
            h2, m2 = map(int, self.check_out.split(':'))
            total_mins = (h2 * 60 + m2) - (h1 * 60 + m1)
            # Night shift: checkout is next day, so add 24 hours
            if total_mins < 0 or self.is_overnight:
                total_mins += 24 * 60
            return round(max(0, total_mins / 60), 2)
        except (ValueError, AttributeError):
            return 0.0

    def __repr__(self):
        return f'<Attendance {self.employee_id} {self.date}>'




# ===========================================================================
# EMPLOYEE SELF-SERVICE MODELS
# ===========================================================================

# ---------------------------------------------------------------------------
# ProfileUpdateRequest — Employee submits profile changes for HR approval
# ---------------------------------------------------------------------------
class ProfileUpdateRequest(db.Model):
    __tablename__ = 'profile_update_requests'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    field_name = db.Column(db.String(50), nullable=False)       # phone, bank_account, pan_number, emergency_contact
    old_value = db.Column(db.String(250), default='')
    new_value = db.Column(db.String(250), nullable=False)
    status = db.Column(db.String(20), default='Pending')        # Pending, Approved, Rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    employee = db.relationship('Employee', backref=db.backref('profile_update_requests', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def __repr__(self):
        return f'<ProfileUpdateRequest {self.field_name} emp#{self.employee_id} {self.status}>'


# ---------------------------------------------------------------------------
# EmployeeExpense — Employee submits expense/reimbursement claims
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# EmployeeExpense — Employee submits expense/reimbursement claims
# ---------------------------------------------------------------------------
class EmployeeExpense(db.Model):
    __tablename__ = 'employee_expenses'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    category = db.Column(db.String(60), nullable=False)         # Travel, Medical, Software, Food, Other
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
    description = db.Column(db.Text, default='')
    receipt_filename = db.Column(db.String(250), default='')
    receipt_original = db.Column(db.String(250), default='')
    status = db.Column(db.String(20), default='Pending')        # Pending, Approved, Rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref=db.backref('expense_claims', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def __repr__(self):
        return f'<EmployeeExpense {self.category} ₹{self.amount} emp#{self.employee_id}>'




# ===========================================================================
# SHIFT & ATTENDANCE ADVANCED MODELS
# ===========================================================================

# ---------------------------------------------------------------------------
# CompOff — Compensatory off earned from overtime work
# ---------------------------------------------------------------------------
class CompOff(db.Model):
    __tablename__ = 'comp_offs'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    earned_date = db.Column(db.Date, nullable=False)                # Date overtime was worked
    hours_extra = db.Column(db.Float, default=0.0)                  # Extra hours worked
    status = db.Column(db.String(20), default='Earned')             # Earned, Used, Expired
    used_date = db.Column(db.Date, nullable=True)                   # Date the comp-off was consumed
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    approver = db.relationship('User', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<CompOff emp#{self.employee_id} {self.earned_date} {self.status}>'


# ---------------------------------------------------------------------------
# ShiftSwapRequest — Employee requests HR to change their shift
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# ShiftSwapRequest — Employee requests HR to change their shift
# ---------------------------------------------------------------------------
class ShiftSwapRequest(db.Model):
    __tablename__ = 'shift_swap_requests'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    current_shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=True)
    requested_shift_id = db.Column(db.Integer, db.ForeignKey('shifts.id'), nullable=False)
    reason = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Pending')            # Pending, Approved, Rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)

    reviewer = db.relationship('User', foreign_keys=[reviewed_by])
    current_shift = db.relationship('Shift', foreign_keys=[current_shift_id])
    requested_shift = db.relationship('Shift', foreign_keys=[requested_shift_id])

    def __repr__(self):
        return f'<ShiftSwapRequest emp#{self.employee_id} {self.status}>'




# ===========================================================================
# TIMESHEET MODEL
# ===========================================================================

# ---------------------------------------------------------------------------
# Timesheet — Employee logs hours against projects/tasks
# ---------------------------------------------------------------------------
class Timesheet(db.Model):
    __tablename__ = 'timesheets'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True)
    date = db.Column(db.Date, nullable=False)
    hours_worked = db.Column(db.Float, nullable=False, default=0.0)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Pending')           # Pending, Approved, Rejected
    rejection_reason = db.Column(db.Text, default='')
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref=db.backref('timesheets', lazy='dynamic'))
    task = db.relationship('Task', backref=db.backref('timesheets', lazy='dynamic'))
    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_timesheets')

    __table_args__ = (
        db.UniqueConstraint('employee_id', 'project_id', 'task_id', 'date',
                           name='uq_emp_proj_task_date'),
    )

    @property
    def employee_name(self):
        return self.employee.user.full_name if self.employee and self.employee.user else 'Unknown'

    @property
    def project_name(self):
        return self.project.name if self.project else 'Unknown'

    @property
    def task_title(self):
        return self.task.title if self.task else '— General —'

    def __repr__(self):
        return f'<Timesheet #{self.id} emp#{self.employee_id} {self.date} {self.hours_worked}h {self.status}>'




# ===========================================================================
# ATTENDANCE REGULARIZATION MODEL
# ===========================================================================

# ---------------------------------------------------------------------------
# AttendanceRegularization — Employee requests attendance correction
# ---------------------------------------------------------------------------
class AttendanceRegularization(db.Model):
    __tablename__ = 'attendance_regularizations'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    requested_check_in = db.Column(db.String(10), default='')    # HH:MM
    requested_check_out = db.Column(db.String(10), default='')   # HH:MM
    reason = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Pending')         # Pending, Approved, Rejected
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    rejection_reason = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref=db.backref('regularization_requests', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by])

    def __repr__(self):
        return f'<AttendanceRegularization emp#{self.employee_id} {self.date} {self.status}>'




# ---------------------------------------------------------------------------
# EmployeeDocument
# ---------------------------------------------------------------------------
class EmployeeDocument(db.Model):
    __tablename__ = 'employee_documents'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    doc_type = db.Column(db.String(50), nullable=False)      # ID Proof, Offer Letter, Resume, etc.
    filename = db.Column(db.String(250), nullable=False)
    original_name = db.Column(db.String(250), default='')
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader = db.relationship('User', foreign_keys=[uploaded_by])

    def __repr__(self):
        return f'<EmployeeDocument {self.doc_type} for emp#{self.employee_id}>'


# ---------------------------------------------------------------------------
# JobPosting (Recruitment — Batch 2)
# ---------------------------------------------------------------------------



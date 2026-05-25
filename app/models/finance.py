import re
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db



# ===========================================================================
# FINANCE MODELS (unchanged)
# ===========================================================================

# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------
class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(60), nullable=False)      # Travel, Software, Office, Marketing
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
    description = db.Column(db.Text, default='')
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='Pending')     # Pending, Approved, Rejected

    submitter = db.relationship('User', back_populates='expenses', foreign_keys=[submitted_by])

    def __repr__(self):
        return f'<Expense {self.category} ₹{self.amount}>'


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------
class Invoice(db.Model):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(30), unique=True, nullable=False)
    client_name = db.Column(db.String(150), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    issue_date = db.Column(db.Date, default=date.today)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='Unpaid')      # Unpaid, Paid, Overdue, Cancelled
    description = db.Column(db.Text, default='')

    def __repr__(self):
        return f'<Invoice {self.invoice_number}>'


# ---------------------------------------------------------------------------
# SalaryRecord
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# SalaryRecord
# ---------------------------------------------------------------------------
class SalaryRecord(db.Model):
    __tablename__ = 'salary_records'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    month = db.Column(db.String(20), nullable=False)         # e.g. "January"
    year = db.Column(db.Integer, nullable=False)
    basic = db.Column(db.Float, default=0.0)
    hra = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Pending')     # Pending, Processed, Paid

    __table_args__ = (db.UniqueConstraint('employee_id', 'month', 'year', name='uq_emp_month_year'),)

    def __repr__(self):
        return f'<SalaryRecord {self.employee_id} {self.month}/{self.year}>'




# ===========================================================================
# BATCH 2 STUBS (models ready, routes in Batch 2)
# ===========================================================================

# ---------------------------------------------------------------------------
# PayrollInput (HR → Finance bridge)
# ---------------------------------------------------------------------------
class PayrollInput(db.Model):
    __tablename__ = 'payroll_inputs'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    month = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    working_days = db.Column(db.Integer, default=0)
    present_days = db.Column(db.Integer, default=0)
    leaves_taken = db.Column(db.Integer, default=0)
    overtime_hours = db.Column(db.Float, default=0.0)
    bonus = db.Column(db.Float, default=0.0)
    deduction_notes = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Draft')       # Draft, Submitted
    submitted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submitter = db.relationship('User', foreign_keys=[submitted_by])

    __table_args__ = (db.UniqueConstraint('employee_id', 'month', 'year', name='uq_payroll_emp_month_year'),)

    def __repr__(self):
        return f'<PayrollInput {self.employee_id} {self.month}/{self.year}>'


# ---------------------------------------------------------------------------
# EmployeeDocument
# ---------------------------------------------------------------------------



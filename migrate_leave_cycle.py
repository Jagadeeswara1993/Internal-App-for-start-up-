"""
Database migration: Add CompanySettings table and new LeaveBalance columns.
Run this script once after deployment to update the database schema.

Usage:
    python migrate_leave_cycle.py
"""

import sys
import os

# Ensure app directory is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.models import CompanySettings, LeaveBalance

app = create_app()

with app.app_context():
    print("=" * 60)
    print("Leave Cycle Migration — Adding new tables & columns")
    print("=" * 60)

    from sqlalchemy import text

    # --- 1. Create company_settings table ---
    try:
        db.session.execute(text("SELECT 1 FROM company_settings LIMIT 1"))
        print("[OK] company_settings table already exists.")
    except Exception:
        db.session.rollback()
        print("[..] Creating company_settings table...")
        db.session.execute(text("""
            CREATE TABLE company_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                leave_cycle_type VARCHAR(20) NOT NULL DEFAULT 'financial',
                custom_cycle_start_month INTEGER DEFAULT 4,
                custom_cycle_start_day INTEGER DEFAULT 1,
                proration_rounding VARCHAR(10) DEFAULT 'round',
                updated_at DATETIME
            )
        """))
        # Insert default row
        db.session.execute(text("""
            INSERT INTO company_settings (leave_cycle_type, custom_cycle_start_month, custom_cycle_start_day, proration_rounding)
            VALUES ('financial', 4, 1, 'round')
        """))
        print("[OK] company_settings table created with defaults (Financial Year, Apr-Mar).")

    # --- 2. Add new columns to leave_balances ---
    columns_to_add = [
        ("carried_forward", "FLOAT DEFAULT 0"),
        ("cycle_start", "DATE"),
        ("cycle_end", "DATE"),
    ]

    for col_name, col_def in columns_to_add:
        try:
            db.session.execute(text(f"SELECT {col_name} FROM leave_balances LIMIT 1"))
            print(f"[OK] leave_balances.{col_name} already exists.")
        except Exception:
            db.session.rollback()
            print(f"[..] Adding leave_balances.{col_name}...")
            db.session.execute(text(f"ALTER TABLE leave_balances ADD COLUMN {col_name} {col_def}"))
            print(f"[OK] leave_balances.{col_name} added.")

    # --- 3. Initialize leave balances for all existing employees who don't have them ---
    from app.models import Employee
    from app.hr.services import initialize_leave_balances

    employees = Employee.query.filter_by(is_active=True).all()
    initialized_count = 0
    for emp in employees:
        existing = LeaveBalance.query.filter_by(employee_id=emp.id).first()
        if not existing:
            initialize_leave_balances(emp.id)
            initialized_count += 1

    if initialized_count > 0:
        db.session.commit()
        print(f"[OK] Initialized leave balances for {initialized_count} employee(s) who had none.")
    else:
        print("[OK] All employees already have leave balances.")

    db.session.commit()
    print("\n" + "=" * 60)
    print("Migration complete! All changes applied successfully.")
    print("=" * 60)

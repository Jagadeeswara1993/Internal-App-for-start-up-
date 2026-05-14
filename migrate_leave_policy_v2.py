"""Migration script to add new columns for Leave Policy Enhancements:
1. LeavePolicy.is_calendar_days — Calendar days vs working days toggle
2. LeavePolicy.is_prorated     — Auto-prorate for new joiners
3. Leave.is_half_day           — Half-day leave support
4. Leave.total_days            — Changed from INTEGER to REAL (Float)
5. LeaveBalance.total_allocated — Changed from INTEGER to REAL (Float)
6. LeaveBalance.used           — Changed from INTEGER to REAL (Float)

NOTE: SQLite does not natively support ALTER COLUMN type changes.
Since Float ↔ Integer columns in SQLite already store values correctly
(SQLite uses dynamic typing), we only need to add truly new columns.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'enterprise_portal.db')

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- 1. Add is_calendar_days to leave_policies ---
    try:
        cursor.execute("ALTER TABLE leave_policies ADD COLUMN is_calendar_days BOOLEAN DEFAULT 0")
        print("[OK] Added leave_policies.is_calendar_days")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("[SKIP] leave_policies.is_calendar_days already exists")
        else:
            raise

    # --- 2. Add is_prorated to leave_policies ---
    try:
        cursor.execute("ALTER TABLE leave_policies ADD COLUMN is_prorated BOOLEAN DEFAULT 0")
        print("[OK] Added leave_policies.is_prorated")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("[SKIP] leave_policies.is_prorated already exists")
        else:
            raise

    # --- 3. Add is_half_day to leaves ---
    try:
        cursor.execute("ALTER TABLE leaves ADD COLUMN is_half_day BOOLEAN DEFAULT 0")
        print("[OK] Added leaves.is_half_day")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("[SKIP] leaves.is_half_day already exists")
        else:
            raise

    # --- 4. Verify existing data (SQLite dynamic typing handles int->float) ---
    # No ALTER COLUMN needed -- SQLite's affinity system handles this automatically.
    # Integer values read as Float in Python via SQLAlchemy Float column type.
    print("[INFO] SQLite dynamic typing: total_days/total_allocated/used columns "
          "already support float values -- no schema change needed")

    conn.commit()
    conn.close()
    print("\n[DONE] Migration complete!")


if __name__ == '__main__':
    migrate()

"""Migration: Add Epics table and Task hierarchy columns.

Run with:  python migrations/add_epics_and_task_hierarchy.py
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    conn = db.engine.connect()

    # ── 1. Create 'epics' table ──────────────────────────────────────────
    conn.execute(db.text("""
        CREATE TABLE IF NOT EXISTS epics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER NOT NULL,
            title       VARCHAR(200) NOT NULL,
            description TEXT DEFAULT '',
            status      VARCHAR(30) DEFAULT 'To Do',
            color_label VARCHAR(7)  DEFAULT '#6366f1',
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            UNIQUE (project_id, title)
        )
    """))
    print("[OK] Created 'epics' table")

    # ── 2. Add columns to 'tasks' table ──────────────────────────────────
    # Check existing columns to avoid duplicate-add errors
    result = conn.execute(db.text("PRAGMA table_info(tasks)"))
    existing_cols = {row[1] for row in result.fetchall()}

    if 'epic_id' not in existing_cols:
        conn.execute(db.text(
            "ALTER TABLE tasks ADD COLUMN epic_id INTEGER REFERENCES epics(id) ON DELETE SET NULL"
        ))
        print("[OK] Added 'epic_id' column to tasks")
    else:
        print("[SKIP] 'epic_id' already exists")

    if 'parent_task_id' not in existing_cols:
        conn.execute(db.text(
            "ALTER TABLE tasks ADD COLUMN parent_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL"
        ))
        print("[OK] Added 'parent_task_id' column to tasks")
    else:
        print("[SKIP] 'parent_task_id' already exists")

    if 'task_type' not in existing_cols:
        conn.execute(db.text(
            "ALTER TABLE tasks ADD COLUMN task_type VARCHAR(20) DEFAULT 'Task'"
        ))
        print("[OK] Added 'task_type' column to tasks")
    else:
        print("[SKIP] 'task_type' already exists")

    conn.commit()
    conn.close()
    print("\n[DONE] Migration complete - Epics + Task hierarchy ready.")

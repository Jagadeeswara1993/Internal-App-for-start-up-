# Walkthrough: Task Hierarchy Auto-Propagation & Epic Sync Fix

## Problem

When subtasks were marked "Done" by employees (via the Employee portal), the following issues occurred:
1. **Parent task** stayed "In Progress" — requiring manual status change
2. **Epic** showed "0% done" / "To Do" — never auto-updating
3. **Hours** on subtasks didn't aggregate up to parent task
4. **Reverting** a subtask out of Done didn't revert the parent

## Root Cause

The auto-complete cascade logic existed only in the **PM module** (`pm/services.py`) but was **completely missing** from the **Employee module** (`employee/routes/work_routes.py` and `employee/services.py`). Additionally, Epic status never auto-updated anywhere.

## Changes Made

### 1. [pm.py](file:///c:/JGpc/app_at_present/app/models/pm.py) — Model fixes

**Epic.progress** — Now counts ALL tasks in the hierarchy (parents + subtasks), not just direct tasks:
```python
# Before: only counted direct tasks
done = self.tasks.filter_by(status='Done').count()

# After: counts tasks + subtasks via parent_task_id
all_tasks = Task.query.filter(or_(
    Task.epic_id == self.id,
    Task.parent_task_id.in_(direct_task_ids)
)).all()
```

**Epic.check_and_update_status()** — New method that auto-sets epic status:
- All tasks Done → Epic "Done"
- Any task In Progress or Done → Epic "In Progress"  
- Otherwise → Epic "To Do"

**Task.total_estimated_hours / total_actual_hours** — New computed properties that aggregate from subtasks.

---

### 2. [services.py](file:///c:/JGpc/app_at_present/app/pm/services.py) — Cascade logic

Created two reusable helpers:

**`_cascade_status_up(task, updater_id)`** — After any task status change:
1. Aggregates subtask hours to parent
2. Auto-completes parent when ALL subtasks are Done
3. Reverts parent to "In Progress" if a subtask moves OUT of Done
4. Auto-moves parent to "In Progress" when first subtask starts
5. Auto-updates the Epic status

**`_update_epic_for_task(task, updater_id)`** — Updates the epic's status via `check_and_update_status()`.

Both `update_task()` and `update_task_status()` now call `_cascade_status_up()`.

Also: `create_task()` now auto-sets parent to "In Progress" when a subtask is added.

Hours cascade also added to `approve_timesheet()`, `bulk_approve_timesheets()`, and `log_task_hours()`.

---

### 3. [work_routes.py](file:///c:/JGpc/app_at_present/app/employee/routes/work_routes.py) — Employee route fix

The employee `update_task_status` API route now includes full cascade logic — parent auto-complete/revert and epic auto-update — matching the PM module behavior.

---

### 4. [employee/services.py](file:///c:/JGpc/app_at_present/app/employee/services.py) — Employee service fix

The employee services `update_task_status()` function now includes the same cascade logic for parent auto-complete and epic status sync.

## Test Results

Tested against actual database data:

| Check | Before | After Cascade |
|-------|--------|---------------|
| Parent "design login module" status | In Progress | **Done** |
| Epic "user authentication system" progress | 50% | **75%** |
| Epic status | To Do | **In Progress** |
| Parent actual_hours | 0 | **10.0** (5+5 from subtasks) |
| Parent total_estimated_hours | 16.0 | **16.0** (8+8 from subtasks) |

## How to Test Manually

1. Log in as **employee (surya)** → go to **My Tasks**
2. Find a subtask and change its status to "Done"
3. Check the parent task — it should auto-update:
   - If all subtasks Done → parent becomes "Done"
   - If some subtasks Done → parent stays "In Progress"
4. Go to **PM view** → check the Epic panel — progress % and status should reflect the changes
5. Try reverting a subtask from "Done" → "In Progress" — parent should revert to "In Progress"

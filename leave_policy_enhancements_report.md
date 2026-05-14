# Leave Policy Enhancements — Final Report

## Summary of Completed Changes

All three requested enhancements to the HR leave management system have been fully implemented and integrated. 

### 1. Calendar Days vs. Working Days Toggle (High Priority)
*   **Database:** Added `is_calendar_days` boolean flag to the `LeavePolicy` model.
*   **Logic (`app/models/employee.py` & `app/hr/services.py`):** 
    *   Updated `Leave.calc_days()` to accept an `is_calendar_days` parameter.
    *   Updated `validate_leave_request()` to check the policy flag. If `True`, it calculates leaves as `(end_date - start_date) + 1` (including weekends and holidays). If `False`, it maintains the default behavior (excluding weekends/holidays).
*   **UI (`LeavePolicyForm` & Admin Routes):** Added the toggle to the Admin configuration form with a descriptive info card to guide HR admins when setting up statutory leaves (e.g., Maternity Leave). Updated the leave policies list view to show a "Counting" column (Calendar vs. Working).

### 2. Half-Day Leaves Support (Medium Priority)
*   **Database:** 
    *   Changed `Leave.total_days` from `Integer` to `Float`.
    *   Changed `LeaveBalance.total_allocated` and `LeaveBalance.used` from `Integer` to `Float`.
    *   Added `is_half_day` boolean flag to the `Leave` model.
*   **Logic:**
    *   Updated `Leave.calc_days()` and `validate_leave_request()` to immediately return `0.5` days if `is_half_day` is selected, enforcing that start and end dates must be the same.
    *   Updated `submit_leave_request` in `app/employee/services.py` to accept the half-day flag and format notifications dynamically.
*   **UI:**
    *   Added a clearly styled "Half-Day Leave (0.5 day)" checkbox to the Employee Leave Request form.
    *   Added dynamic JavaScript that automatically syncs and locks the `end_date` to match the `start_date` when the half-day checkbox is selected.
    *   Updated all leave history, team leaves, and balance templates across HR, Admin, and Employee portals to correctly format float values using `round(1)` and display a "Half" badge where applicable.

### 3. Automated Proration for New Joiners (Medium Priority)
*   **Database:** Added `is_prorated` boolean flag to the `LeavePolicy` model.
*   **Logic (`app/hr/services.py`):** 
    *   Updated `initialize_leave_balances()` to calculate a prorated allocation based on the employee's `date_of_joining`.
    *   If a policy is marked as prorated, the system calculates the remaining months in the joining year (including the joining month) and allocates a proportional fraction of the total annual days.
*   **UI (`LeavePolicyForm` & Admin Routes):** Added the proration toggle to the Admin configuration form with an explanatory info card. Added a "Prorated" indicator to the Admin leave policies list.

### 4. Database Migration
*   Created and executed the migration script `migrate_leave_policy_v2.py`.
*   Successfully added `is_calendar_days` and `is_prorated` to the `leave_policies` table.
*   Successfully added `is_half_day` to the `leaves` table.
*   Relied on SQLite's dynamic typing affinity to seamlessly handle the transition from Integer to Float for the duration and balance columns without data loss or complex schema alterations.

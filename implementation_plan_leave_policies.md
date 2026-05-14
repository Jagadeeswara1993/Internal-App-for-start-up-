# Leave Policy Enhancements — Implementation Plan

## Feature 1: Calendar Days vs. Working Days Toggle

### Changes:
| File | Change |
|------|--------|
| `app/models/hr.py` | Add `is_calendar_days = db.Column(db.Boolean, default=False)` to `LeavePolicy` |
| `app/models/employee.py` | Update `Leave.calc_days()` to accept an optional `is_calendar_days` param and skip weekend/holiday exclusion when True |
| `app/admin/config_forms.py` | Add `is_calendar_days` BooleanField to `LeavePolicyForm` |
| `app/admin/routes/config_routes.py` | Wire `is_calendar_days` in add/edit handlers |
| `app/hr/services.py` | Update `validate_leave_request()` and `approve_leave()` to respect `is_calendar_days` flag |
| `app/employee/services.py` | Update `submit_leave_request()` to pass calendar-days context |
| `app/templates/admin/leave_policy_form.html` | Add Calendar Days toggle switch |
| `app/templates/admin/leave_policies.html` | Add "Counting" column showing Calendar/Working |

## Feature 2: Half-Day Leave Support

### Changes:
| File | Change |
|------|--------|
| `app/models/employee.py` | Change `Leave.total_days` from `Integer` to `Float` |
| `app/models/employee.py` | Change `LeaveBalance.total_allocated` and `used` from `Integer` to `Float` |
| `app/employee/forms.py` | Add `is_half_day` BooleanField to `LeaveRequestForm` |
| `app/employee/services.py` | Handle half-day logic (0.5 days when checkbox is checked, enforce single-day) |
| `app/hr/services.py` | Update validation/approval to handle float days |
| `app/templates/employee/leave_request.html` | Add half-day checkbox with dynamic JS |
| Templates (balance/leaves) | Format floats nicely (e.g. `1.0` → `1`, `0.5` → `0.5`) |

## Feature 3: Automated Proration for New Joiners

### Changes:
| File | Change |
|------|--------|
| `app/models/hr.py` | Add `is_prorated = db.Column(db.Boolean, default=False)` to `LeavePolicy` |
| `app/admin/config_forms.py` | Add `is_prorated` BooleanField to `LeavePolicyForm` |
| `app/admin/routes/config_routes.py` | Wire `is_prorated` in add/edit handlers |
| `app/hr/services.py` | Update `initialize_leave_balances()` to calculate prorated allocation based on `date_of_joining` |
| `app/templates/admin/leave_policy_form.html` | Add Proration toggle switch |
| `app/templates/admin/leave_policies.html` | Add "Prorated" column |

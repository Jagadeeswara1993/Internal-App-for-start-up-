# Interactive Leave Calendar — Implementation Plan

## Goal

Add a visual **month-grid calendar** to both the **HR module** (organization-wide) and the **Employee module** (manager's team view) that shows at a glance:

- 🟢 Who is present  
- 🔴 Who is on approved leave  
- 🟡 Who is on half-day leave  
- ⬜ Company holidays  
- 🔵 Weekends (Sat/Sun)  
- Click on any day → popup showing the list of absent employees

**No new database models required** — we use existing `Leave`, `Attendance`, `Holiday`, `Employee`, and `Department` tables.

---

## User Review Required

> [!IMPORTANT]
> **Where the calendar will live:**
> - **HR Module** → New sidebar link: `HR → Leave Calendar` at `/hr/leave-calendar`  
>   - Shows **all employees** across the organization  
>   - Filter dropdown: by **Department**  
> - **Employee Module** → New sidebar link under "My Team" section: `Team Calendar` at `/employee/team/calendar`  
>   - Shows only the **manager's direct reports**  
>   - Visible only to employees who are reporting managers (same gating as existing "My Team" / "Team Leaves" links)

> [!NOTE]
> The calendar is a **pure CSS Grid + vanilla JavaScript** implementation. No external library (no FullCalendar, no npm packages). This keeps it consistent with the rest of the app's tech stack.

---

## Proposed Changes

### Component 1: HR Module — Organization Leave Calendar

---

#### [NEW] Route in [leave_routes.py](file:///c:/JGpc/app_at_present/app/hr/routes/leave_routes.py)

Add a new `leave_calendar()` route at the end of the file:

```python
@bp.route('/leave-calendar')
@module_required('hr')
def leave_calendar():
    """Visual month-grid leave calendar for the entire organization."""
    from calendar import monthrange
    from app.models import Department, Holiday, Attendance

    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    dept_filter = request.args.get('department', 0, type=int)

    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()

    # Compute calendar grid data
    _, num_days = monthrange(year, month)
    first_weekday = date(year, month, 1).weekday()  # 0=Mon

    # Holidays this month
    holidays = Holiday.query.filter(
        db.extract('year', Holiday.holiday_date) == year,
        db.extract('month', Holiday.holiday_date) == month
    ).all()
    holiday_map = {h.holiday_date.day: h.holiday_name for h in holidays}

    # Approved leaves this month
    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)

    leave_query = Leave.query.filter(
        Leave.status == 'Approved',
        Leave.start_date <= month_end,
        Leave.end_date >= month_start
    )
    if dept_filter:
        leave_query = leave_query.join(Employee).filter(Employee.department_id == dept_filter)
    approved_leaves = leave_query.all()

    # Build day → list of absent employees
    from collections import defaultdict
    day_absences = defaultdict(list)
    for lv in approved_leaves:
        emp = lv.employee
        s = max(lv.start_date, month_start)
        e = min(lv.end_date, month_end)
        current = s
        while current <= e:
            day_absences[current.day].append({
                'name': emp.user.full_name,
                'emp_code': emp.emp_code,
                'dept': emp.department_name,
                'leave_type': lv.leave_type,
                'is_half_day': lv.is_half_day
            })
            current += timedelta(days=1)

    # Employee count for "present" calculation
    emp_query = Employee.query.filter_by(is_active=True)
    if dept_filter:
        emp_query = emp_query.filter_by(department_id=dept_filter)
    total_employees = emp_query.count()

    # Build calendar data
    import json
    calendar_data = []
    for day in range(1, num_days + 1):
        d = date(year, month, day)
        is_weekend = d.weekday() >= 5
        is_holiday = day in holiday_map
        absences = day_absences.get(day, [])
        absent_count = len(absences)
        half_day_count = sum(1 for a in absences if a['is_half_day'])

        calendar_data.append({
            'day': day,
            'weekday': d.strftime('%a'),
            'is_weekend': is_weekend,
            'is_holiday': is_holiday,
            'holiday_name': holiday_map.get(day, ''),
            'is_today': d == date.today(),
            'absent_count': absent_count,
            'half_day_count': half_day_count,
            'present_count': max(0, total_employees - absent_count) if not is_weekend and not is_holiday else 0,
            'absences': absences
        })

    # Month navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_name = date(year, month, 1).strftime('%B %Y')

    return render_template('hr/leave_calendar.html',
                           calendar_data=calendar_data,
                           calendar_json=json.dumps(calendar_data),
                           first_weekday=first_weekday,
                           month_name=month_name,
                           year=year, month=month,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month,
                           departments=departments,
                           selected_dept=dept_filter,
                           total_employees=total_employees)
```

---

#### [NEW] Template [leave_calendar.html](file:///c:/JGpc/app_at_present/app/templates/hr/leave_calendar.html)

A full Jinja2 template extending `base.html` with:

- **Header**: Month name, ◀ / ▶ navigation arrows, department dropdown filter
- **Legend bar**: Color key (Present / On Leave / Half-day / Holiday / Weekend)
- **CSS Grid calendar**: 7 columns (Mon–Sun), each day cell shows:
  - Day number
  - Color-coded background based on status
  - Absent count badge (e.g., "3 on leave")
  - Weekend/holiday label
  - Today highlighted with a ring
- **Click popup (Bootstrap modal)**: When a day cell is clicked, a modal shows the full list of absent employees for that day (name, emp code, department, leave type)
- **Responsive**: On mobile, days show as a compact list instead of grid

---

#### [MODIFY] Sidebar in [base.html](file:///c:/JGpc/app_at_present/app/templates/base.html)

Add a "Leave Calendar" link under the HR sub-navigation (after the "Timesheets" link, around line 75):

```html
<a href="{{ url_for('hr.leave_calendar') }}" class="nav-link" style="padding:5px 10px; font-size:0.8rem;">
    <i class="fas fa-calendar-days" style="width:16px; font-size:0.75rem;"></i><span>Leave Calendar</span>
</a>
```

---

### Component 2: Employee Module — Team Leave Calendar (Managers Only)

---

#### [NEW] Route in [team_routes.py](file:///c:/JGpc/app_at_present/app/employee/routes/team_routes.py)

Add a new `team_calendar()` route after the existing `team_leaves()` function:

```python
@bp.route('/team/calendar')
@module_required('employee')
def team_calendar():
    """Visual leave calendar for manager's direct reports."""
    from calendar import monthrange
    from app.models import Holiday
    import json

    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    team_members = Employee.query.filter_by(reporting_manager_id=emp.id).all()
    team_ids = [e.id for e in team_members]

    if not team_ids:
        flash('You have no direct reports.', 'info')
        return redirect(url_for('employee.dashboard'))

    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    _, num_days = monthrange(year, month)
    first_weekday = date(year, month, 1).weekday()

    # Holidays
    holidays = Holiday.query.filter(
        db.extract('year', Holiday.holiday_date) == year,
        db.extract('month', Holiday.holiday_date) == month
    ).all()
    holiday_map = {h.holiday_date.day: h.holiday_name for h in holidays}

    # Team leaves
    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)
    approved_leaves = Leave.query.filter(
        Leave.status == 'Approved',
        Leave.employee_id.in_(team_ids),
        Leave.start_date <= month_end,
        Leave.end_date >= month_start
    ).all()

    day_absences = defaultdict(list)
    for lv in approved_leaves:
        e = Employee.query.get(lv.employee_id)
        s = max(lv.start_date, month_start)
        end = min(lv.end_date, month_end)
        current = s
        while current <= end:
            day_absences[current.day].append({
                'name': e.user.full_name,
                'emp_code': e.emp_code,
                'dept': e.department_name,
                'leave_type': lv.leave_type,
                'is_half_day': lv.is_half_day
            })
            current += timedelta(days=1)

    total_team = len(team_ids)
    calendar_data = []
    for day_num in range(1, num_days + 1):
        d = date(year, month, day_num)
        is_weekend = d.weekday() >= 5
        is_holiday = day_num in holiday_map
        absences = day_absences.get(day_num, [])
        calendar_data.append({
            'day': day_num,
            'weekday': d.strftime('%a'),
            'is_weekend': is_weekend,
            'is_holiday': is_holiday,
            'holiday_name': holiday_map.get(day_num, ''),
            'is_today': d == date.today(),
            'absent_count': len(absences),
            'half_day_count': sum(1 for a in absences if a['is_half_day']),
            'present_count': max(0, total_team - len(absences)) if not is_weekend and not is_holiday else 0,
            'absences': absences
        })

    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_name = date(year, month, 1).strftime('%B %Y')

    return render_template('employee/team_calendar.html',
                           calendar_data=calendar_data,
                           calendar_json=json.dumps(calendar_data),
                           first_weekday=first_weekday,
                           month_name=month_name,
                           year=year, month=month,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month,
                           total_team=total_team,
                           employee=emp)
```

---

#### [NEW] Template [team_calendar.html](file:///c:/JGpc/app_at_present/app/templates/employee/team_calendar.html)

Same calendar layout as the HR version but:
- No department filter (shows only direct reports)
- Header says "Team Leave Calendar" 
- Shows team size instead of total employees

---

#### [MODIFY] Sidebar in [base.html](file:///c:/JGpc/app_at_present/app/templates/base.html)

Add a "Team Calendar" link under the existing "Team Leaves" manager section (around line 155):

```html
<a href="{{ url_for('employee.team_calendar') }}" class="nav-link" style="padding:5px 10px; font-size:0.8rem;">
    <i class="fas fa-calendar-days" style="width:16px; font-size:0.75rem;"></i><span>Team Calendar</span>
</a>
```

---

## Complete File Change Summary

| Action | File | What Changes |
|--------|------|-------------|
| **MODIFY** | [leave_routes.py](file:///c:/JGpc/app_at_present/app/hr/routes/leave_routes.py) | Add `leave_calendar()` route (~70 lines) |
| **NEW** | [leave_calendar.html](file:///c:/JGpc/app_at_present/app/templates/hr/leave_calendar.html) | Full calendar template (~250 lines) |
| **MODIFY** | [team_routes.py](file:///c:/JGpc/app_at_present/app/employee/routes/team_routes.py) | Add `team_calendar()` route (~65 lines) |
| **NEW** | [team_calendar.html](file:///c:/JGpc/app_at_present/app/templates/employee/team_calendar.html) | Team calendar template (~220 lines) |
| **MODIFY** | [base.html](file:///c:/JGpc/app_at_present/app/templates/base.html) | Add 2 sidebar links (HR + Employee) |

**Total: 2 new files, 3 modified files. Zero new models. Zero database migrations.**

---

## Calendar UI Design

```
┌──────────────────────────────────────────────────────────────┐
│  ◀  June 2026  ▶          [Department ▾] [All Departments]  │
├──────────────────────────────────────────────────────────────┤
│  🟢 Present  🔴 On Leave  🟡 Half-day  ⬜ Holiday  🔵 Weekend │
├──────┬──────┬──────┬──────┬──────┬──────┬──────┤
│ Mon  │ Tue  │ Wed  │ Thu  │ Fri  │ Sat  │ Sun  │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│  1   │  2   │  3   │  4   │  5   │  6   │  7   │
│ 🟢45 │ 🟢44 │ 🟢45 │ 🔴 2 │ 🟢43 │ 🔵   │ 🔵   │
│      │ 🔴 1 │      │ 🟡 1 │ 🔴 2 │      │      │
├──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│  8   │  9   │  10  │  11  │  12  │  13  │  14  │
│ 🟢42 │ ⬜   │ 🟢44 │ 🟢45 │ 🔴 3 │ 🔵   │ 🔵   │
│ 🔴 3 │Eid   │ 🔴 1 │      │ 🟡 1 │      │      │
└──────┴──────┴──────┴──────┴──────┴──────┴──────┘

Click on day 4 → Modal popup:
┌─────────────────────────────────────┐
│ Thursday, 4 June 2026               │
│─────────────────────────────────────│
│ 🔴 Rahul Sharma (EMP0012)          │
│    Engineering · Casual Leave       │
│ 🔴 Priya Patel (EMP0034)           │
│    Marketing · Sick Leave           │
│ 🟡 Amit Kumar (EMP0021)            │
│    Engineering · Half-day           │
└─────────────────────────────────────┘
```

---

## Verification Plan

### Automated
- `python -m py_compile app/hr/routes/leave_routes.py`
- `python -m py_compile app/employee/routes/team_routes.py`

### Manual Browser Testing
1. **HR Leave Calendar**: Log in as HR user → navigate to `HR → Leave Calendar` → verify month grid renders with correct day count, weekends greyed out, holidays marked
2. **Department Filter**: Select a department → verify only that department's employees show in absence counts
3. **Day Click Popup**: Click on a day with absences → verify modal shows correct employee names, leave types
4. **Month Navigation**: Click ◀ / ▶ arrows → verify correct month loads, data refreshes
5. **Today Highlight**: Verify current day has a distinct visual ring/border
6. **Manager Team Calendar**: Log in as an employee who is a reporting manager → verify "Team Calendar" link appears in sidebar → verify calendar shows only direct reports
7. **Non-Manager**: Log in as a regular employee → verify "Team Calendar" link does NOT appear in sidebar
8. **Edge Cases**: Navigate to February → verify 28/29 days render correctly; navigate to month with zero leaves → verify all cells show green



👣 Manual Browser Verification Steps
To manually test and view the new premium calendar interface:

HR Organizational Calendar:

Log in as an HR user.
Navigate using the sidebar link: HR → Leave Calendar.
Verify that the calendar renders perfectly, today's date has a distinct purple ring, and weekends are greyed out.
Filter by Department to see the stats and present counts adapt in real-time.
Click on any day cell with absences (marked in red or orange) and verify that the modal correctly lists the absent employees' names, codes, departments, and leave types.
Manager Team Calendar:

Log in as an Employee who is a reporting manager.
Look under the Employee Space sidebar's direct reports section and click on Team Calendar.
Verify that the calendar successfully renders only direct reports' leaves and stats.
Log in as a regular non-manager employee and verify that the Team Calendar sidebar link is hidden.
Calendar Grid Navigation:

Click the ◀ and ▶ buttons on either calendar view to verify that months change correctly and calculate accurate dates (e.g., leap years, February lengths, etc.).
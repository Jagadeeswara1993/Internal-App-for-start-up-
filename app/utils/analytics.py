from collections import defaultdict
from datetime import date as date_cls, timedelta
from app.extensions import db
from app.models import (Project, Task, Employee, User, Timesheet, Department,
                        Attendance, Leave, Shift)

def get_organization_analytics_data():
    """Fetches and aggregates organization-wide analytics data for dashboards."""
    all_projects = Project.query.all()
    all_tasks = Task.query.all()
    all_employees = Employee.query.all()

    # Project Status
    status_counts = defaultdict(int)
    status_details = defaultdict(list)
    for p in all_projects:
        status_counts[p.status] += 1
        status_details[p.status].append({'id': p.id, 'name': p.name})
    project_status_data = {
        'labels': ['Not Started', 'In Progress', 'Completed', 'On Hold'],
        'values': [status_counts.get(s, 0) for s in ['Not Started', 'In Progress', 'Completed', 'On Hold']],
        'details': [status_details.get(s, []) for s in ['Not Started', 'In Progress', 'Completed', 'On Hold']]
    }

    # Task Status & Priority
    task_sc = defaultdict(int)
    task_sc_details = defaultdict(list)
    priority_c = defaultdict(int)
    priority_c_details = defaultdict(list)
    for t in all_tasks:
        task_sc[t.status] += 1
        task_sc_details[t.status].append({'id': t.project_id, 'name': t.title})
        priority_c[t.priority] += 1
        priority_c_details[t.priority].append({'id': t.project_id, 'name': t.title})

    task_status_data = {
        'labels': ['Pending', 'In Progress', 'Done'],
        'values': [task_sc.get(s, 0) for s in ['Pending', 'In Progress', 'Done']],
        'details': [task_sc_details.get(s, []) for s in ['Pending', 'In Progress', 'Done']]
    }
    priority_data = {
        'labels': ['Low', 'Medium', 'High', 'Critical'],
        'values': [priority_c.get(s, 0) for s in ['Low', 'Medium', 'High', 'Critical']],
        'details': [priority_c_details.get(s, []) for s in ['Low', 'Medium', 'High', 'Critical']]
    }

    # Hours Comparison per Project
    hours_comp = {'labels': [], 'estimated': [], 'actual': []}
    for p in all_projects:
        approved_h = db.session.query(
            db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)
        ).filter_by(project_id=p.id, status='Approved').scalar()
        hours_comp['labels'].append(p.name[:25])
        hours_comp['estimated'].append(round(p.estimated_hours or 0, 1))
        hours_comp['actual'].append(round(float(approved_h), 1))

    # Employee Workload (top 15)
    emp_workload = defaultdict(lambda: {'pending': 0, 'in_progress': 0, 'done': 0})
    for t in all_tasks:
        if t.assigned_to:
            u = User.query.get(t.assigned_to)
            if u:
                if t.status == 'Pending': emp_workload[u.full_name]['pending'] += 1
                elif t.status == 'In Progress': emp_workload[u.full_name]['in_progress'] += 1
                elif t.status == 'Done': emp_workload[u.full_name]['done'] += 1
    sorted_emp = sorted(emp_workload.keys(), key=lambda n: sum(emp_workload[n].values()), reverse=True)[:15]
    employee_workload_data = {
        'labels': sorted_emp,
        'pending': [emp_workload[n]['pending'] for n in sorted_emp],
        'in_progress': [emp_workload[n]['in_progress'] for n in sorted_emp],
        'done': [emp_workload[n]['done'] for n in sorted_emp],
    }

    # Employee Hours (top 15)
    emp_hours = defaultdict(float)
    approved_ts = Timesheet.query.filter_by(status='Approved').all()
    for ts in approved_ts:
        emp_hours[ts.employee_name] += ts.hours_worked
    sorted_by_hours = sorted(emp_hours.keys(), key=lambda n: emp_hours[n], reverse=True)[:15]
    employee_hours_data = {
        'labels': sorted_by_hours,
        'values': [round(emp_hours[n], 1) for n in sorted_by_hours]
    }

    # Project Progress
    progress_data = {
        'labels': [p.name[:25] for p in all_projects],
        'values': [p.progress for p in all_projects]
    }

    # Department Distribution
    departments = Department.query.filter_by(is_active=True).all()
    dept_data = {'labels': [], 'values': []}
    for d in departments:
        count = d.employees.count()
        if count > 0:
            dept_data['labels'].append(d.name)
            dept_data['values'].append(count)

    # Daily Trend (last 30 days)
    today = date_cls.today()
    thirty_ago = today - timedelta(days=30)
    daily_map = defaultdict(float)
    recent_ts = Timesheet.query.filter(
        Timesheet.date >= thirty_ago, Timesheet.status.in_(['Approved', 'Pending'])
    ).all()
    for ts in recent_ts:
        daily_map[ts.date.strftime('%d %b')] += ts.hours_worked
    date_labels = []
    date_values = []
    for i in range(30, -1, -1):
        d = today - timedelta(days=i)
        lbl = d.strftime('%d %b')
        date_labels.append(lbl)
        date_values.append(round(daily_map.get(lbl, 0), 1))
    daily_trend_data = {'labels': date_labels, 'values': date_values}

    total_hours = round(sum(emp_hours.values()), 1)
    stats = {
        'total_projects': len(all_projects),
        'total_employees': len(all_employees),
        'total_hours': total_hours
    }

    return {
        'stats': stats,
        'project_status_data': project_status_data,
        'task_status_data': task_status_data,
        'priority_data': priority_data,
        'hours_comparison_data': hours_comp,
        'employee_workload_data': employee_workload_data,
        'employee_hours_data': employee_hours_data,
        'progress_data': progress_data,
        'dept_distribution_data': dept_data,
        'daily_trend_data': daily_trend_data
    }


def get_hr_analytics_data():
    """Fetches HR-specific, people-centric analytics data.
    Covers attendance, leaves, departments, shifts, onboarding, and hours.
    Does NOT include project/task data (that belongs to PM)."""

    from app.hr import services as hr_services

    today = date_cls.today()
    current_year = today.year
    all_employees = Employee.query.filter_by(is_active=True).all()
    total_employees = len(all_employees)

    # ── 1. Department Headcount ─────────────────────────────────────────
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    dept_data = {'labels': [], 'values': []}
    for d in departments:
        count = d.employees.count()
        if count > 0:
            dept_data['labels'].append(d.name)
            dept_data['values'].append(count)

    # ── 2. Today's Attendance Snapshot ──────────────────────────────────
    today_records = Attendance.query.filter_by(date=today).all()
    present_count = sum(1 for r in today_records if r.status in ('Present', 'Late'))
    late_count = sum(1 for r in today_records if r.status == 'Late')
    absent_count = total_employees - len(today_records) if total_employees > 0 else 0
    half_day_count = sum(1 for r in today_records if r.status == 'Half-Day')
    on_leave_count = sum(1 for r in today_records if r.status == 'On Leave')

    today_attendance = {
        'labels': ['Present', 'Late', 'Absent', 'Half-Day', 'On Leave'],
        'values': [present_count - late_count, late_count, absent_count, half_day_count, on_leave_count]
    }

    # ── 3. Attendance Trend (Last 30 days) ─────────────────────────────
    thirty_ago = today - timedelta(days=30)
    recent_attendance = Attendance.query.filter(Attendance.date >= thirty_ago).all()
    att_day_map = defaultdict(lambda: {'present': 0, 'late': 0, 'absent': 0, 'half_day': 0})
    for r in recent_attendance:
        key = r.date.strftime('%d %b')
        if r.status == 'Present':
            att_day_map[key]['present'] += 1
        elif r.status == 'Late':
            att_day_map[key]['late'] += 1
        elif r.status == 'Absent':
            att_day_map[key]['absent'] += 1
        elif r.status == 'Half-Day':
            att_day_map[key]['half_day'] += 1

    att_trend_labels = []
    att_trend_present = []
    att_trend_late = []
    att_trend_absent = []
    for i in range(30, -1, -1):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue  # Skip weekends
        lbl = d.strftime('%d %b')
        att_trend_labels.append(lbl)
        att_trend_present.append(att_day_map.get(lbl, {}).get('present', 0))
        att_trend_late.append(att_day_map.get(lbl, {}).get('late', 0))
        att_trend_absent.append(att_day_map.get(lbl, {}).get('absent', 0))

    attendance_trend = {
        'labels': att_trend_labels,
        'present': att_trend_present,
        'late': att_trend_late,
        'absent': att_trend_absent
    }

    # ── 4. Leave Type Distribution (this year, approved) ───────────────
    approved_leaves = Leave.query.filter(
        Leave.status == 'Approved',
        db.extract('year', Leave.start_date) == current_year
    ).all()
    leave_type_counts = defaultdict(int)
    for lv in approved_leaves:
        leave_type_counts[lv.leave_type] += lv.total_days or 1

    leave_type_data = {
        'labels': list(leave_type_counts.keys()) or ['No Data'],
        'values': list(leave_type_counts.values()) or [0]
    }

    # ── 5. Monthly Leave Trend (this year) ─────────────────────────────
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_leaves = [0] * 12
    for lv in approved_leaves:
        if lv.start_date:
            monthly_leaves[lv.start_date.month - 1] += lv.total_days or 1

    monthly_leave_data = {
        'labels': month_names,
        'values': monthly_leaves
    }

    # ── 6. Top Employees by Timesheet Hours ────────────────────────────
    emp_hours = defaultdict(float)
    approved_ts = Timesheet.query.filter_by(status='Approved').all()
    for ts in approved_ts:
        emp_hours[ts.employee_name] += ts.hours_worked
    sorted_by_hours = sorted(emp_hours.keys(), key=lambda n: emp_hours[n], reverse=True)[:15]
    employee_hours_data = {
        'labels': sorted_by_hours,
        'values': [round(emp_hours[n], 1) for n in sorted_by_hours]
    }

    # ── 7. Employee Onboarding Status ──────────────────────────────────
    complete_count = sum(1 for e in all_employees if hr_services.is_employee_profile_complete(e))
    incomplete_count = total_employees - complete_count
    onboarding_data = {
        'labels': ['Profile Complete', 'Incomplete'],
        'values': [complete_count, incomplete_count]
    }

    # ── 8. Shift Distribution ──────────────────────────────────────────
    shifts = Shift.query.filter_by(is_active=True).all()
    shift_map = {s.id: s.shift_name for s in shifts}
    shift_counts = defaultdict(int)
    general_count = 0
    for emp in all_employees:
        if emp.shift_id and emp.shift_id in shift_map:
            shift_counts[shift_map[emp.shift_id]] += 1
        else:
            general_count += 1
    if general_count > 0:
        shift_counts['General'] = general_count
    shift_data = {
        'labels': list(shift_counts.keys()) or ['General'],
        'values': list(shift_counts.values()) or [total_employees]
    }

    # ── Pending counts for header ──────────────────────────────────────
    pending_leaves = Leave.query.filter_by(status='Pending').count()
    total_hours = round(sum(emp_hours.values()), 1)

    stats = {
        'total_employees': total_employees,
        'today_present': present_count,
        'pending_leaves': pending_leaves,
        'total_hours': total_hours
    }

    return {
        'stats': stats,
        'dept_data': dept_data,
        'today_attendance': today_attendance,
        'attendance_trend': attendance_trend,
        'leave_type_data': leave_type_data,
        'monthly_leave_data': monthly_leave_data,
        'employee_hours_data': employee_hours_data,
        'onboarding_data': onboarding_data,
        'shift_data': shift_data
    }


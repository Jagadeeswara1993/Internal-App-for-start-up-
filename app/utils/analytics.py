from collections import defaultdict
from datetime import date as date_cls, timedelta
from app.extensions import db
from app.models import Project, Task, Employee, User, Timesheet, Department

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

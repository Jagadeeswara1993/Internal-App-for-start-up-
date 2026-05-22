"""Employee notification, analytics, and team management routes."""

from collections import defaultdict
from datetime import date, timedelta
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, Notification, Timesheet, Task,
                        ProjectMember, Project, Leave)
from app.hr import services
from app.employee import services as employee_services


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================
@bp.route('/notifications')
@module_required('employee')
def notifications():
    page = request.args.get('page', 1, type=int)
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    return render_template('employee/notifications.html', notifications=notifs, unread_count=unread_count)


@bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@module_required('employee')
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    
    redirect_url = notif.link or url_for('employee.notifications')
    # If the employee is being redirected to a PM route they don't have access to,
    # safely redirect them to the employee tasks/projects equivalent
    if redirect_url.startswith('/pm/'):
        if not (current_user.is_admin or current_user.has_module('pm')):
            if '/projects/' in redirect_url:
                if 'Project' in notif.title or 'Added' in notif.title:
                    redirect_url = url_for('employee.projects')
                else:
                    redirect_url = url_for('employee.my_tasks')
            else:
                redirect_url = url_for('employee.my_tasks')
                
    return redirect(redirect_url)


@bp.route('/notifications/mark-all-read', methods=['POST'])
@module_required('employee')
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False)\
        .update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('employee.notifications'))


# ===========================================================================
# PERSONAL ANALYTICS
# ===========================================================================
@bp.route('/analytics')
@module_required('employee')
def analytics():
    """Personal analytics — hours, tasks, projects."""
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()

    # Daily Hours Trend (Last 30 Days)
    today = date.today()
    daily_hours_data = {'labels': [], 'values': []}
    
    start_date = today - timedelta(days=29)
    timesheets = Timesheet.query.filter(
        Timesheet.employee_id == emp.id,
        Timesheet.status == 'Approved',
        Timesheet.date >= start_date,
        Timesheet.date <= today
    ).all()
    
    ts_dict = defaultdict(float)
    for ts in timesheets:
        ts_dict[ts.date] += ts.hours_worked

    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        daily_hours_data['labels'].append(d.strftime('%d %b'))
        daily_hours_data['values'].append(round(ts_dict[d], 1))

    # Stats
    my_tasks = Task.query.filter_by(assigned_to=current_user.id).all()
    total_tasks = len(my_tasks)
    done_tasks = sum(1 for t in my_tasks if t.status == 'Done')
    
    total_hours_query = db.session.query(db.func.sum(Timesheet.hours_worked)).filter(
        Timesheet.employee_id == emp.id, Timesheet.status == 'Approved'
    ).scalar()
    total_hours = round(total_hours_query or 0, 1)

    stats = {
        'total_tasks': total_tasks,
        'done_tasks': done_tasks,
        'total_hours': total_hours
    }

    # Projects Data
    memberships = ProjectMember.query.filter_by(user_id=current_user.id).all()
    project_ids = [m.project_id for m in memberships]
    pm_projects = Project.query.filter_by(assigned_pm=current_user.id).all()
    all_project_ids = list(set(project_ids + [p.id for p in pm_projects]))

    projects = Project.query.filter(Project.id.in_(all_project_ids)).all() if all_project_ids else []

    projects_data = []
    for p in projects:
        p_tasks = [t for t in my_tasks if t.project_id == p.id]
        task_list = []
        for t in p_tasks:
            task_list.append({
                'title': t.title,
                'status': t.status,
                'priority': t.priority,
                'actual_hours': t.actual_hours,
                'estimated_hours': t.estimated_hours,
                'deadline': t.due_date.strftime('%Y-%m-%d') if t.due_date else None
            })
            
        my_logged_hours = db.session.query(db.func.sum(Timesheet.hours_worked)).filter(
            Timesheet.employee_id == emp.id, 
            Timesheet.project_id == p.id,
            Timesheet.status == 'Approved'
        ).scalar()

        projects_data.append({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'manager': p.pm_owner.full_name if p.pm_owner else 'N/A',
            'start_date': p.start_date.strftime('%Y-%m-%d') if p.start_date else None,
            'end_date': p.end_date.strftime('%Y-%m-%d') if p.end_date else None,
            'progress': p.progress,
            'status': p.status,
            'my_logged_hours': round(my_logged_hours or 0, 1),
            'tasks': task_list
        })

    return render_template('employee/analytics.html', employee=emp,
                           stats=stats,
                           daily_hours_data=daily_hours_data,
                           projects_data=projects_data)


# ===========================================================================
# TEAM MANAGEMENT (Reporting Manager features)
# ===========================================================================
@bp.route('/team')
@module_required('employee')
def my_team():
    """View direct reports."""
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    team_members = Employee.query.filter_by(reporting_manager_id=emp.id).all()
    team_ids = [e.id for e in team_members]
    
    pending_count = 0
    if team_ids:
        pending_count = Leave.query.filter(
            Leave.employee_id.in_(team_ids),
            Leave.manager_status == 'Pending'
        ).count()
        
    return render_template('employee/my_team.html', reports=team_members, pending_count=pending_count, employee=emp)


@bp.route('/team/leaves')
@module_required('employee')
def team_leaves():
    """View pending leave requests from direct reports."""
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    team_ids = [e.id for e in Employee.query.filter_by(reporting_manager_id=emp.id).all()]
    
    pending_count = 0
    if team_ids:
        pending_count = Leave.query.filter(
            Leave.employee_id.in_(team_ids),
            Leave.manager_status == 'Pending'
        ).count()
        
    status_filter = request.args.get('status')
        
    if not team_ids:
        return render_template('employee/team_leaves.html', leaves=[], employee=emp, pending_count=0, selected_status=status_filter)
        
    query = Leave.query.filter(Leave.employee_id.in_(team_ids))
    if status_filter:
        if status_filter == 'manager_pending':
            query = query.filter(Leave.manager_status == 'Pending')
        elif status_filter in ['Pending', 'Approved', 'Rejected']:
            query = query.filter(Leave.status == status_filter)
            
    leaves = query.order_by(Leave.created_at.desc()).all()
    return render_template('employee/team_leaves.html', leaves=leaves, employee=emp, pending_count=pending_count, selected_status=status_filter)


@bp.route('/team/leaves/<int:leave_id>/approve', methods=['POST'])
@module_required('employee')
def team_approve_leave(leave_id):
    """Reporting manager approves a team member's leave."""
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    leave = Leave.query.get_or_404(leave_id)
    team_member = Employee.query.get(leave.employee_id)
    if not team_member or team_member.reporting_manager_id != emp.id:
        flash('You are not the reporting manager for this employee.', 'danger')
        return redirect(url_for('employee.team_leaves'))

    success, msg = employee_services.manager_approve_leave(leave_id, emp.id, request.remote_addr or '')
    if success:
        services.log_audit(current_user.id, 'APPROVE', 'Leave', leave_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('employee.team_leaves'))


@bp.route('/team/leaves/<int:leave_id>/reject', methods=['POST'])
@module_required('employee')
def team_reject_leave(leave_id):
    """Reporting manager rejects a team member's leave."""
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    leave = Leave.query.get_or_404(leave_id)
    team_member = Employee.query.get(leave.employee_id)
    if not team_member or team_member.reporting_manager_id != emp.id:
        flash('You are not the reporting manager for this employee.', 'danger')
        return redirect(url_for('employee.team_leaves'))

    reason = request.form.get('rejection_reason', '').strip()
    success, msg = employee_services.manager_reject_leave(leave_id, emp.id, reason, request.remote_addr or '')
    if success:
        services.log_audit(current_user.id, 'REJECT', 'Leave', leave_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('employee.team_leaves'))


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


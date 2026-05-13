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
    return redirect(notif.link or url_for('employee.notifications'))


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

    success, msg = services.approve_leave(leave_id, current_user.id)
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

    reason = request.form.get('reason', '').strip()
    success, msg = services.reject_leave(leave_id, current_user.id, reason)
    if success:
        services.log_audit(current_user.id, 'REJECT', 'Leave', leave_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('employee.team_leaves'))

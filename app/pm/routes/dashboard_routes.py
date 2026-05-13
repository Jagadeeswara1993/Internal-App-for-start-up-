"""PM dashboard and analytics routes."""

from flask import render_template, request
from flask_login import current_user
from app.pm import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Project, Task, Milestone, Notification, User, Timesheet)
from app.pm.routes.helpers import _get_user_projects


@bp.route('/')
@module_required('pm')
def dashboard():
    visible_projects = _get_user_projects(current_user)
    visible_ids = [p.id for p in visible_projects]

    total_projects = len(visible_projects)
    active_projects = sum(1 for p in visible_projects if p.status == 'In Progress')
    completed_projects = sum(1 for p in visible_projects if p.status == 'Completed')
    on_hold_projects = sum(1 for p in visible_projects if p.status == 'On Hold')

    task_q = Task.query.filter(Task.project_id.in_(visible_ids)) if visible_ids else Task.query.filter(False)
    total_tasks = task_q.count()
    pending_tasks = task_q.filter(Task.status == 'Pending').count()
    tasks_done = task_q.filter(Task.status == 'Done').count()
    tasks_in_progress = task_q.filter(Task.status == 'In Progress').count()
    overdue_tasks = task_q.filter(Task.due_date < db.func.current_date(), Task.status != 'Done').count()

    ms_q = Milestone.query.filter(Milestone.project_id.in_(visible_ids)) if visible_ids else Milestone.query.filter(False)
    total_milestones = ms_q.count()
    completed_milestones = ms_q.filter(Milestone.status == 'Completed').count()

    recent_projects = visible_projects[:5]
    is_project_manager = any(p.assigned_pm == current_user.id for p in visible_projects)
    is_team_member = not current_user.is_admin and not is_project_manager

    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).order_by(Notification.created_at.desc()).limit(10).all()

    pending_timesheets = 0
    if visible_ids:
        pending_timesheets = Timesheet.query.filter(
            Timesheet.project_id.in_(visible_ids), Timesheet.status == 'Pending'
        ).count()

    return render_template('pm/dashboard.html',
                           total_projects=total_projects, active_projects=active_projects,
                           completed_projects=completed_projects, on_hold_projects=on_hold_projects,
                           total_tasks=total_tasks, pending_tasks=pending_tasks,
                           tasks_done=tasks_done, tasks_in_progress=tasks_in_progress,
                           overdue_tasks=overdue_tasks,
                           total_milestones=total_milestones,
                           completed_milestones=completed_milestones,
                           recent_projects=recent_projects,
                           unread_notifications=unread_notifications,
                           is_project_manager=is_project_manager,
                           is_team_member=is_team_member,
                           pending_timesheets=pending_timesheets)


@bp.route('/analytics')
@module_required('pm')
def analytics():
    """PM Analytics dashboard with filterable graphical representations."""
    visible_projects = _get_user_projects(current_user)
    projects_data = []

    for p in visible_projects:
        approved_hours = db.session.query(
            db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)
        ).filter_by(project_id=p.id, status='Approved').scalar()
        actual_h = round(float(approved_hours), 1)
        est_h = round(p.estimated_hours or 0, 1)

        mgr_name = "Unassigned"
        if p.assigned_pm:
            m = User.query.get(p.assigned_pm)
            if m: mgr_name = m.full_name

        p_tasks = []
        for t in p.tasks:
            assigned_name = "Unassigned"
            if t.assigned_to:
                u = User.query.get(t.assigned_to)
                if u: assigned_name = u.full_name
            p_tasks.append({
                'id': t.id, 'title': t.title, 'status': t.status,
                'priority': t.priority, 'assigned_to': assigned_name,
                'estimated_hours': round(t.estimated_hours or 0, 1),
                'actual_hours': round(t.actual_hours or 0, 1),
                'deadline': t.due_date.strftime('%Y-%m-%d') if t.due_date else ''
            })

        projects_data.append({
            'id': p.id, 'name': p.name, 'description': p.description,
            'status': p.status, 'progress': p.progress,
            'start_date': p.start_date.strftime('%Y-%m-%d') if p.start_date else '',
            'end_date': p.end_date.strftime('%Y-%m-%d') if p.end_date else '',
            'manager': mgr_name, 'estimated_hours': est_h,
            'actual_hours': actual_h, 'tasks': p_tasks
        })

    total_tasks = sum(len(p['tasks']) for p in projects_data)
    total_hours = sum(p['actual_hours'] for p in projects_data)
    stats = {'total_projects': len(projects_data), 'total_tasks': total_tasks,
             'total_hours': round(total_hours, 1)}

    return render_template('pm/analytics.html', stats=stats, projects_data=projects_data)

"""PM API, notification, and timesheet approval routes."""

from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from app.pm import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Project, Task, Milestone, ProjectMember, User,
                        Notification, Timesheet, Epic)
from app.pm.routes.helpers import (_get_user_projects, _is_pm_or_admin,
                                    _can_view_project, log_audit)
from app.pm import services


# ===========================================================================
# JSON APIS
# ===========================================================================
@bp.route('/api/projects')
@module_required('pm')
def api_projects():
    projects = _get_user_projects(current_user)
    return jsonify([{
        'id': p.id, 'name': p.name, 'status': p.status,
        'progress': p.progress, 'start_date': str(p.start_date or ''),
        'end_date': str(p.end_date or ''), 'deadline': str(p.deadline or ''),
        'task_count': p.tasks.count(), 'is_delayed': p.is_delayed
    } for p in projects])


@bp.route('/api/projects/<int:project_id>')
@module_required('pm')
def api_project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        return jsonify({'error': 'Forbidden'}), 403
    pm_name = ''
    if project.assigned_pm:
        pm_user = User.query.get(project.assigned_pm)
        if pm_user: pm_name = pm_user.full_name
    return jsonify({
        'id': project.id, 'name': project.name, 'description': project.description,
        'status': project.status, 'progress': project.progress,
        'start_date': str(project.start_date or ''), 'end_date': str(project.end_date or ''),
        'deadline': str(project.deadline or ''), 'estimated_hours': project.estimated_hours,
        'assigned_pm': pm_name, 'is_delayed': project.is_delayed
    })


@bp.route('/api/projects/<int:project_id>/tasks')
@module_required('pm')
def api_project_tasks(project_id):
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        return jsonify({'error': 'Forbidden'}), 403
    tasks = Task.query.filter_by(project_id=project.id).order_by(Task.created_at.desc()).all()
    return jsonify([{
        'id': t.id, 'title': t.title, 'status': t.status, 'priority': t.priority,
        'assigned_to': User.query.get(t.assigned_to).full_name if t.assigned_to else 'Unassigned',
        'due_date': str(t.due_date or ''), 'estimated_hours': t.estimated_hours or 0,
        'actual_hours': t.actual_hours or 0,
        'task_type': t.task_type or 'Task',
        'epic_id': t.epic_id,
        'parent_task_id': t.parent_task_id
    } for t in tasks])


@bp.route('/api/projects/<int:project_id>/milestones')
@module_required('pm')
def api_project_milestones(project_id):
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        return jsonify({'error': 'Forbidden'}), 403
    milestones = Milestone.query.filter_by(project_id=project.id).order_by(Milestone.deadline.asc().nullslast()).all()
    return jsonify([{
        'id': m.id, 'title': m.title, 'status': m.status,
        'deadline': str(m.deadline or ''), 'description': m.description or ''
    } for m in milestones])


@bp.route('/api/projects/<int:project_id>/members')
@module_required('pm')
def api_project_members(project_id):
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        return jsonify({'error': 'Forbidden'}), 403
    members = ProjectMember.query.filter_by(project_id=project.id).all()
    return jsonify([{
        'id': m.id, 'user_id': m.user_id, 'name': m.user.full_name, 'role': m.role
    } for m in members])


# ===========================================================================
# BOARD API — Kanban drag-drop
# ===========================================================================
@bp.route('/api/projects/<int:project_id>/board')
@module_required('pm')
def api_board(project_id):
    """Return tasks grouped by status for the Kanban board."""
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        return jsonify({'error': 'Forbidden'}), 403

    # Only show top-level tasks on the board (sub-tasks are nested inside cards)
    tasks = Task.query.filter_by(project_id=project.id)\
        .filter((Task.parent_task_id == None) | (Task.parent_task_id == 0))\
        .order_by(Task.updated_at.desc()).all()

    columns = {'Pending': [], 'In Progress': [], 'Done': []}
    for t in tasks:
        assignee_name = ''
        assignee_initial = ''
        if t.assigned_to:
            u = User.query.get(t.assigned_to)
            if u:
                assignee_name = u.full_name
                assignee_initial = u.full_name[0].upper()

        epic_info = None
        if t.epic_id:
            epic = Epic.query.get(t.epic_id)
            if epic:
                epic_info = {'id': epic.id, 'title': epic.title, 'color': epic.color_label}

        subtask_count = t.subtasks.count()
        subtask_done = t.subtasks.filter_by(status='Done').count()

        card = {
            'id': t.id, 'title': t.title, 'priority': t.priority,
            'task_type': t.task_type or 'Task',
            'assignee': assignee_name, 'assignee_initial': assignee_initial,
            'due_date': t.due_date.strftime('%d %b') if t.due_date else '',
            'epic': epic_info,
            'subtask_count': subtask_count,
            'subtask_done': subtask_done
        }
        if t.status in columns:
            columns[t.status].append(card)
        else:
            columns['Pending'].append(card)

    return jsonify(columns)


@bp.route('/api/projects/<int:project_id>/epics')
@module_required('pm')
def api_project_epics(project_id):
    """List epics for a project (used by board filters)."""
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        return jsonify({'error': 'Forbidden'}), 403
    epics = Epic.query.filter_by(project_id=project.id).order_by(Epic.title).all()
    return jsonify([{
        'id': e.id, 'title': e.title, 'status': e.status,
        'color': e.color_label, 'progress': e.progress,
        'task_count': e.tasks.count()
    } for e in epics])


@bp.route('/api/tasks/<int:task_id>/status', methods=['PATCH'])
@module_required('pm')
def api_update_task_status(task_id):
    """Kanban drag-drop: update task status via AJAX."""
    task = Task.query.get_or_404(task_id)
    project = task.project

    if not _can_view_project(current_user, project):
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json(silent=True)
    if not data or 'status' not in data:
        return jsonify({'error': 'Missing status'}), 400

    new_status = data['status']
    valid_statuses = ['Pending', 'In Progress', 'Done']
    if new_status not in valid_statuses:
        return jsonify({'error': f'Invalid status. Must be one of: {valid_statuses}'}), 400

    updated = services.update_task_status(task.id, new_status, current_user.id)
    db.session.commit()

    # Auto-update project status
    project.check_and_update_status()
    db.session.commit()

    return jsonify({
        'success': True,
        'task_id': task.id,
        'new_status': new_status,
        'project_progress': project.progress
    })


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================
@bp.route('/api/notifications')
@module_required('pm')
def api_notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': n.id, 'title': n.title, 'message': n.message,
        'category': n.category, 'is_read': n.is_read,
        'created_at': n.created_at.isoformat(), 'link': n.link or ''
    } for n in notifs])


@bp.route('/notifications')
@module_required('pm')
def notifications():
    page = request.args.get('page', 1, type=int)
    notifs = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc()).paginate(page=page, per_page=30, error_out=False)
    return render_template('pm/notifications.html', notifications=notifs)


@bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@module_required('pm')
def mark_notification_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(notif.link or url_for('pm.notifications'))


@bp.route('/notifications/mark-all-read', methods=['POST'])
@module_required('pm')
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('pm.notifications'))


# ===========================================================================
# TIMESHEET APPROVALS
# ===========================================================================
@bp.route('/timesheet-approvals')
@module_required('pm')
def timesheet_approvals():
    """PM views pending timesheets for their projects."""
    if current_user.is_admin:
        projects = Project.query.order_by(Project.name).all()
    else:
        projects = Project.query.filter_by(assigned_pm=current_user.id).order_by(Project.name).all()
        
    project_ids = [p.id for p in projects]

    selected_project = request.args.get('project', type=int)
    status_filter = request.args.get('status', 'Pending')
    page = request.args.get('page', 1, type=int)

    if not project_ids:
        stats = {'total': 0, 'pending': 0, 'approved': 0, 'total_hours': 0}
        timesheets = Timesheet.query.filter(False).paginate(page=page, per_page=15)
        return render_template('pm/timesheet_approvals.html',
                               timesheets=timesheets, stats=stats,
                               projects=[], selected_project=None,
                               selected_status=status_filter)

    query = Timesheet.query.filter(Timesheet.project_id.in_(project_ids))
    
    if selected_project:
        query = query.filter_by(project_id=selected_project)

    # Calculate stats BEFORE status filtering
    total_entries = query.count()
    pending_count = query.filter_by(status='Pending').count()
    approved_count = query.filter_by(status='Approved').count()
    
    approved_hours_val = db.session.query(db.func.sum(Timesheet.hours_worked))\
                                   .filter(Timesheet.project_id.in_(project_ids),
                                           Timesheet.status=='Approved')
    if selected_project:
        approved_hours_val = approved_hours_val.filter(Timesheet.project_id==selected_project)
    
    total_hours = approved_hours_val.scalar() or 0

    stats = {
        'total': total_entries,
        'pending': pending_count,
        'approved': approved_count,
        'total_hours': round(total_hours, 1)
    }

    if status_filter:
        query = query.filter_by(status=status_filter)

    timesheets = query.order_by(Timesheet.date.desc()).paginate(page=page, per_page=15, error_out=False)

    return render_template('pm/timesheet_approvals.html',
                           timesheets=timesheets,
                           stats=stats,
                           projects=projects,
                           selected_project=selected_project,
                           selected_status=status_filter)


@bp.route('/timesheets/<int:ts_id>/approve', methods=['POST'])
@module_required('pm')
def approve_timesheet(ts_id):
    ts = Timesheet.query.get_or_404(ts_id)
    project = Project.query.get(ts.project_id)
    if not _is_pm_or_admin(current_user, project):
        flash('Only the PM or Admin can approve timesheets.', 'danger')
        return redirect(url_for('pm.timesheet_approvals'))
    if ts.status != 'Pending':
        flash('This timesheet has already been processed.', 'warning')
        return redirect(url_for('pm.timesheet_approvals'))

    services.approve_timesheet(ts, current_user.id)
    db.session.commit()
    flash(f'Timesheet approved ({ts.hours_worked}h).', 'success')
    return redirect(url_for('pm.timesheet_approvals'))


@bp.route('/timesheets/<int:ts_id>/reject', methods=['POST'])
@module_required('pm')
def reject_timesheet(ts_id):
    ts = Timesheet.query.get_or_404(ts_id)
    project = Project.query.get(ts.project_id)
    if not _is_pm_or_admin(current_user, project):
        flash('Only the PM or Admin can reject timesheets.', 'danger')
        return redirect(url_for('pm.timesheet_approvals'))
    if ts.status != 'Pending':
        flash('This timesheet has already been processed.', 'warning')
        return redirect(url_for('pm.timesheet_approvals'))

    reason = request.form.get('rejection_reason', '').strip()
    services.reject_timesheet(ts, reason, current_user.id)
    db.session.commit()
    flash('Timesheet rejected.', 'warning')
    return redirect(url_for('pm.timesheet_approvals'))


@bp.route('/timesheets/bulk-approve', methods=['POST'])
@module_required('pm')
def bulk_approve_timesheets():
    """Bulk approve selected timesheets."""
    ts_ids = request.form.getlist('timesheet_ids', type=int)
    if not ts_ids:
        flash('No timesheets selected.', 'warning')
        return redirect(url_for('pm.timesheet_approvals'))

    count = 0
    timesheets_to_approve = []
    for ts_id in ts_ids:
        ts = Timesheet.query.get(ts_id)
        if ts and ts.status == 'Pending':
            project = Project.query.get(ts.project_id)
            if _is_pm_or_admin(current_user, project):
                timesheets_to_approve.append(ts)
                
    if timesheets_to_approve:
        count = services.bulk_approve_timesheets(timesheets_to_approve, current_user.id)

    db.session.commit()
    flash(f'{count} timesheet(s) approved.', 'success')
    return redirect(url_for('pm.timesheet_approvals'))

"""PM API, notification, and timesheet approval routes."""

from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from app.pm import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Project, Task, Milestone, ProjectMember, User,
                        Notification, Timesheet)
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
        'actual_hours': t.actual_hours or 0
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
        project_ids = [p.id for p in Project.query.all()]
    else:
        project_ids = [p.id for p in Project.query.filter_by(assigned_pm=current_user.id).all()]

    if not project_ids:
        return render_template('pm/timesheet_approvals.html',
                               pending_entries=[], approved_entries=[], rejected_entries=[])

    status_filter = request.args.get('status', 'Pending')
    query = Timesheet.query.filter(Timesheet.project_id.in_(project_ids))
    if status_filter:
        query = query.filter_by(status=status_filter)
    entries = query.order_by(Timesheet.date.desc()).all()

    pending_entries = [e for e in entries if e.status == 'Pending'] if status_filter in ('', 'Pending') else []
    approved_entries = [e for e in entries if e.status == 'Approved'] if status_filter in ('', 'Approved') else []
    rejected_entries = [e for e in entries if e.status == 'Rejected'] if status_filter in ('', 'Rejected') else []

    return render_template('pm/timesheet_approvals.html',
                           pending_entries=pending_entries,
                           approved_entries=approved_entries,
                           rejected_entries=rejected_entries,
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

"""PM team/member management routes."""

from flask import redirect, url_for, flash, request
from flask_login import current_user
from app.pm import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Project, ProjectMember, User
from app.pm.routes.helpers import _is_pm_or_admin, log_audit
from app.pm import services


@bp.route('/projects/<int:project_id>/add-member', methods=['POST'])
@module_required('pm')
def add_member(project_id):
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        flash('Only the assigned PM or Admin can manage team members.', 'danger')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    user_id = request.form.get('user_id', type=int)
    role = request.form.get('role', 'Developer')
    if user_id:
        success, msg = services.add_team_member(project, user_id, role, current_user.id)
        if success:
            db.session.commit()
            flash(msg, 'success')
        else:
            flash(msg, 'warning')
    return redirect(url_for('pm.project_detail', project_id=project.id))


@bp.route('/projects/<int:project_id>/remove-member/<int:member_id>', methods=['POST'])
@module_required('pm')
def remove_member(project_id, member_id):
    member = ProjectMember.query.get_or_404(member_id)
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        flash('Only the assigned PM or Admin can manage team members.', 'danger')
        return redirect(url_for('pm.project_detail', project_id=project_id))
    success, msg = services.remove_team_member(member, current_user.id)
    db.session.commit()
    flash(msg, 'info')
    return redirect(url_for('pm.project_detail', project_id=project_id))

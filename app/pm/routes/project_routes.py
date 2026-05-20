"""PM project CRUD routes."""

from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from app.pm import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Project, ProjectMember, Task, Milestone, User, Module, Epic
from app.pm.forms import ProjectForm
from app.pm.routes.helpers import (_get_user_projects, _is_pm_or_admin,
                                    _can_view_project, log_audit)
from app.pm import services


@bp.route('/projects')
@module_required('pm')
def projects():
    status_filter = request.args.get('status', '')
    visible = _get_user_projects(current_user)
    if status_filter:
        visible = [p for p in visible if p.status == status_filter]
    can_create = current_user.is_admin
    return render_template('pm/projects.html', projects=visible,
                           current_status=status_filter, can_create=can_create)


@bp.route('/projects/add', methods=['GET', 'POST'])
@module_required('pm')
def add_project():
    if not current_user.is_admin:
        flash('Only Admin can create projects.', 'danger')
        return redirect(url_for('pm.projects'))
    form = ProjectForm()
    pm_module = Module.query.filter_by(slug='pm').first()
    pm_users = pm_module.users.all() if pm_module else []
    form.assigned_pm.choices = [(0, '-- Select PM --')] + [
        (u.id, u.full_name) for u in pm_users if not u.is_admin
    ]
    if form.validate_on_submit():
        existing = Project.query.filter(
            db.func.lower(Project.name) == form.name.data.strip().lower()
        ).first()
        if existing:
            flash(f'Project "{form.name.data}" already exists.', 'danger')
            return render_template('pm/project_form.html', form=form, title='New Project')

        assigned = form.assigned_pm.data if form.assigned_pm.data != 0 else None
        data = {
            'name': form.name.data,
            'description': form.description.data,
            'start_date': form.start_date.data,
            'end_date': form.end_date.data,
            'deadline': form.deadline.data,
            'estimated_hours': form.estimated_hours.data,
            'status': form.status.data,
            'assigned_pm': assigned
        }
        project = services.create_project(data, current_user.id)
        db.session.commit()
        flash(f'Project "{project.name}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/project_form.html', form=form, title='New Project')


@bp.route('/projects/<int:project_id>')
@module_required('pm')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        abort(403)
    members = ProjectMember.query.filter_by(project_id=project.id).all()
    # Only show top-level tasks in the table (sub-tasks shown nested)
    tasks = Task.query.filter_by(project_id=project.id)\
        .order_by(Task.created_at.desc()).all()
    milestones = Milestone.query.filter_by(project_id=project.id)\
        .order_by(Milestone.deadline.asc().nullslast()).all()
    epics = Epic.query.filter_by(project_id=project.id)\
        .order_by(Epic.title).all()
    all_users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    progress = project.progress
    can_manage = _is_pm_or_admin(current_user, project)
    return render_template('pm/project_detail.html', project=project,
                           members=members, tasks=tasks, milestones=milestones,
                           epics=epics, all_users=all_users,
                           progress=progress, can_manage=can_manage)


@bp.route('/projects/<int:project_id>/board')
@module_required('pm')
def board_view(project_id):
    """Kanban board view for a project (Jira-style per-project board)."""
    project = Project.query.get_or_404(project_id)
    if not _can_view_project(current_user, project):
        abort(403)
    epics = Epic.query.filter_by(project_id=project.id).order_by(Epic.title).all()
    members = ProjectMember.query.filter_by(project_id=project.id).all()
    can_manage = _is_pm_or_admin(current_user, project)
    return render_template('pm/board.html', project=project,
                           epics=epics, members=members,
                           can_manage=can_manage)


@bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        abort(403)
    form = ProjectForm(obj=project)
    pm_module = Module.query.filter_by(slug='pm').first()
    pm_users = pm_module.users.all() if pm_module else []
    form.assigned_pm.choices = [(0, '-- Select PM --')] + [
        (u.id, u.full_name) for u in pm_users if not u.is_admin
    ]
    if request.method == 'GET':
        form.assigned_pm.data = project.assigned_pm or 0
    if form.validate_on_submit():
        existing = Project.query.filter(
            db.func.lower(Project.name) == form.name.data.strip().lower(),
            Project.id != project.id
        ).first()
        if existing:
            flash(f'Project "{form.name.data}" already exists.', 'danger')
            return render_template('pm/project_form.html', form=form,
                                   title='Edit Project', project=project)
        data = {
            'name': form.name.data,
            'description': form.description.data,
            'start_date': form.start_date.data,
            'end_date': form.end_date.data,
            'deadline': form.deadline.data,
            'estimated_hours': form.estimated_hours.data,
            'status': form.status.data,
        }
        if current_user.is_admin:
            data['assigned_pm'] = form.assigned_pm.data if form.assigned_pm.data != 0 else None
            
        services.update_project(project, data, current_user.id, current_user.is_admin)
        db.session.commit()
        flash(f'Project "{project.name}" updated.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/project_form.html', form=form,
                           title='Edit Project', project=project)


@bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@module_required('pm')
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    if not current_user.is_admin:
        abort(403)
    project_name = project.name
    log_audit(current_user.id, 'DELETE', 'Project', project.id,
              f'Deleted project "{project_name}"')
    db.session.delete(project)
    db.session.commit()
    flash(f'Project "{project_name}" deleted.', 'info')
    return redirect(url_for('pm.projects'))

"""PM routes — projects, tasks, members."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.pm import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Project, ProjectMember, Task, User


from app.pm.forms import ProjectForm, TaskForm


@bp.route('/')
@module_required('pm')
def dashboard():
    total_projects = Project.query.count()
    active_projects = Project.query.filter_by(status='In Progress').count()
    total_tasks = Task.query.count()
    tasks_done = Task.query.filter_by(status='Done').count()
    tasks_in_progress = Task.query.filter_by(status='In Progress').count()
    overdue_tasks = Task.query.filter(Task.due_date < db.func.current_date(),
                                       Task.status != 'Done').count()
    recent_projects = Project.query.order_by(Project.created_at.desc()).limit(5).all()
    return render_template('pm/dashboard.html',
                           total_projects=total_projects,
                           active_projects=active_projects,
                           total_tasks=total_tasks,
                           tasks_done=tasks_done,
                           tasks_in_progress=tasks_in_progress,
                           overdue_tasks=overdue_tasks,
                           recent_projects=recent_projects)


@bp.route('/projects')
@module_required('pm')
def projects():
    all_projects = Project.query.order_by(Project.created_at.desc()).all()
    return render_template('pm/projects.html', projects=all_projects)


@bp.route('/projects/add', methods=['GET', 'POST'])
@module_required('pm')
def add_project():
    form = ProjectForm()
    if form.validate_on_submit():
        project = Project(
            name=form.name.data,
            description=form.description.data or '',
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            status=form.status.data,
            created_by=current_user.id
        )
        db.session.add(project)
        db.session.commit()
        flash(f'Project "{project.name}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/project_form.html', form=form, title='New Project')


@bp.route('/projects/<int:project_id>')
@module_required('pm')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    members = ProjectMember.query.filter_by(project_id=project.id).all()
    tasks = Task.query.filter_by(project_id=project.id).order_by(Task.created_at.desc()).all()
    all_users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    return render_template('pm/project_detail.html', project=project,
                           members=members, tasks=tasks, all_users=all_users)


@bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    form = ProjectForm(obj=project)
    if form.validate_on_submit():
        project.name = form.name.data
        project.description = form.description.data or ''
        project.start_date = form.start_date.data
        project.end_date = form.end_date.data
        project.status = form.status.data
        db.session.commit()
        flash(f'Project "{project.name}" updated.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/project_form.html', form=form, title='Edit Project', project=project)


@bp.route('/projects/<int:project_id>/add-member', methods=['POST'])
@module_required('pm')
def add_member(project_id):
    project = Project.query.get_or_404(project_id)
    user_id = request.form.get('user_id', type=int)
    role = request.form.get('role', 'Member')
    if user_id:
        existing = ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first()
        if existing:
            flash('User is already a member of this project.', 'warning')
        else:
            member = ProjectMember(project_id=project.id, user_id=user_id, role=role)
            db.session.add(member)
            db.session.commit()
            flash('Member added.', 'success')
    return redirect(url_for('pm.project_detail', project_id=project.id))


@bp.route('/projects/<int:project_id>/remove-member/<int:member_id>', methods=['POST'])
@module_required('pm')
def remove_member(project_id, member_id):
    member = ProjectMember.query.get_or_404(member_id)
    db.session.delete(member)
    db.session.commit()
    flash('Member removed.', 'info')
    return redirect(url_for('pm.project_detail', project_id=project_id))


@bp.route('/projects/<int:project_id>/tasks/add', methods=['GET', 'POST'])
@module_required('pm')
def add_task(project_id):
    project = Project.query.get_or_404(project_id)
    form = TaskForm()
    users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    form.assigned_to.choices = [(0, '-- Unassigned --')] + [(u.id, u.full_name) for u in users]

    if form.validate_on_submit():
        task = Task(
            project_id=project.id,
            title=form.title.data,
            description=form.description.data or '',
            assigned_to=form.assigned_to.data if form.assigned_to.data != 0 else None,
            priority=form.priority.data,
            status=form.status.data,
            due_date=form.due_date.data
        )
        db.session.add(task)
        db.session.commit()
        flash(f'Task "{task.title}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
    return render_template('pm/task_form.html', form=form, project=project, title='New Task')


@bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    form = TaskForm(obj=task)
    users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    form.assigned_to.choices = [(0, '-- Unassigned --')] + [(u.id, u.full_name) for u in users]

    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data or ''
        task.assigned_to = form.assigned_to.data if form.assigned_to.data != 0 else None
        task.priority = form.priority.data
        task.status = form.status.data
        task.due_date = form.due_date.data
        db.session.commit()
        flash(f'Task "{task.title}" updated.', 'success')
        return redirect(url_for('pm.project_detail', project_id=task.project_id))
    return render_template('pm/task_form.html', form=form, project=task.project,
                           title='Edit Task', task=task)


@bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@module_required('pm')
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project_id = task.project_id
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted.', 'info')
    return redirect(url_for('pm.project_detail', project_id=project_id))

"""PM task, epic, and milestone management routes."""

from flask import redirect, url_for, flash, request, abort, render_template
from flask_login import current_user
from app.pm import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Project, Task, Milestone, User, Epic
from app.pm.forms import TaskForm, MilestoneForm, EpicForm
from app.pm.routes.helpers import (_is_pm_or_admin, _can_view_project,
                                    log_audit)
from app.pm import services


# ===========================================================================
# EPIC MANAGEMENT
# ===========================================================================
@bp.route('/projects/<int:project_id>/epics/add', methods=['GET', 'POST'])
@module_required('pm')
def add_epic(project_id):
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        flash('Only the PM or Admin can create epics.', 'danger')
        return redirect(url_for('pm.project_detail', project_id=project.id))

    form = EpicForm()
    if form.validate_on_submit():
        data = {
            'project_id': project.id,
            'title': form.title.data,
            'description': form.description.data,
            'status': form.status.data,
            'color_label': form.color_label.data or '#6366f1'
        }
        epic = services.create_epic(data, current_user.id)
        db.session.commit()
        flash(f'Epic "{epic.title}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))

    return render_template('pm/epic_form.html', form=form, project=project, title="Add Epic")


@bp.route('/epics/<int:epic_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_epic(epic_id):
    epic = Epic.query.get_or_404(epic_id)
    project = epic.project
    if not _is_pm_or_admin(current_user, project):
        abort(403)

    form = EpicForm(obj=epic)
    if form.validate_on_submit():
        data = {
            'title': form.title.data,
            'description': form.description.data,
            'status': form.status.data,
            'color_label': form.color_label.data or '#6366f1'
        }
        services.update_epic(epic, data, current_user.id)
        db.session.commit()
        flash(f'Epic "{epic.title}" updated.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))

    return render_template('pm/epic_form.html', form=form, project=project, title="Edit Epic")


@bp.route('/epics/<int:epic_id>/delete', methods=['POST'])
@module_required('pm')
def delete_epic(epic_id):
    epic = Epic.query.get_or_404(epic_id)
    project = epic.project
    if not _is_pm_or_admin(current_user, project):
        abort(403)
    title = epic.title
    # Unlink tasks from this epic before deleting
    Task.query.filter_by(epic_id=epic.id).update({'epic_id': None})
    log_audit(current_user.id, 'DELETE', 'Epic', epic.id, f'Deleted epic "{title}"')
    db.session.delete(epic)
    db.session.commit()
    flash(f'Epic "{title}" deleted.', 'info')
    return redirect(url_for('pm.project_detail', project_id=project.id))


# ===========================================================================
# TASK MANAGEMENT
# ===========================================================================
def _populate_task_form(form, project, task=None):
    """Populate dynamic choices for task form fields."""
    members = project.members
    form.assigned_to.choices = [(0, '— Unassigned —')] + \
        [(m.user_id, m.user.full_name) for m in members]

    epics = Epic.query.filter_by(project_id=project.id).order_by(Epic.title).all()
    form.epic_id.choices = [(0, '— No Epic —')] + [(e.id, e.title) for e in epics]

    # Parent task choices: only top-level tasks (not sub-tasks themselves)
    parent_candidates = Task.query.filter_by(
        project_id=project.id, parent_task_id=None
    ).order_by(Task.title).all()
    # Exclude self if editing
    if task:
        parent_candidates = [t for t in parent_candidates if t.id != task.id]
    form.parent_task_id.choices = [(0, '— None (Top-level) —')] + \
        [(t.id, f'{t.title}') for t in parent_candidates]


@bp.route('/projects/<int:project_id>/tasks/add', methods=['GET', 'POST'])
@module_required('pm')
def add_task(project_id):
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        flash('Only the PM or Admin can create tasks.', 'danger')
        return redirect(url_for('pm.project_detail', project_id=project.id))
        
    form = TaskForm()
    _populate_task_form(form, project)
    
    if form.validate_on_submit():
        assigned = form.assigned_to.data if form.assigned_to.data else None
        due_date = form.due_date.data
        priority = form.priority.data

        # ── Holiday check: block non-critical tasks on public holidays ──
        if due_date and assigned:
            from app.models import Holiday, Employee, CompOff
            holiday = Holiday.query.filter_by(holiday_date=due_date, is_active=True).first()
            if holiday:
                if priority not in ('Critical', 'High'):
                    flash(
                        f'Cannot assign this task — {due_date.strftime("%d %b %Y")} is a public holiday '
                        f'("{holiday.holiday_name}"). Only Critical or High priority tasks are allowed on holidays.',
                        'danger'
                    )
                    return render_template('pm/task_form.html', form=form, project=project, title="Add Task")
                else:
                    # Critical/High task on holiday → auto-earn comp-off for the employee
                    emp = Employee.query.filter_by(user_id=assigned).first()
                    if emp:
                        existing_comp = CompOff.query.filter_by(
                            employee_id=emp.id, earned_date=due_date
                        ).first()
                        if not existing_comp:
                            comp_off = CompOff(
                                employee_id=emp.id,
                                earned_date=due_date,
                                hours_extra=form.estimated_hours.data or 8.0,
                                status='Earned'
                            )
                            db.session.add(comp_off)
                        flash(
                            f'⚠️ {due_date.strftime("%d %b %Y")} is a holiday ("{holiday.holiday_name}"). '
                            f'A compensatory off has been auto-earned for the assigned employee.',
                            'warning'
                        )

        data = {
            'project_id': project.id,
            'title': form.title.data,
            'description': form.description.data,
            'assigned_to': assigned,
            'priority': priority,
            'due_date': due_date,
            'estimated_hours': form.estimated_hours.data,
            'milestone_id': form.milestone_id.data if hasattr(form, 'milestone_id') and form.milestone_id.data else None,
            'task_type': form.task_type.data,
            'epic_id': form.epic_id.data if form.epic_id.data else None,
            'parent_task_id': form.parent_task_id.data if form.parent_task_id.data else None
        }
        task = services.create_task(data, current_user.id)
        db.session.commit()
        flash(f'Task "{task.title}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
        
    return render_template('pm/task_form.html', form=form, project=project, title="Add Task")


@bp.route('/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project
    if not _is_pm_or_admin(current_user, project):
        member_ids = [m.user_id for m in project.members]
        if current_user.id not in member_ids:
            abort(403)
            
    form = TaskForm(obj=task)
    _populate_task_form(form, project, task)
    
    if request.method == 'GET':
        form.assigned_to.data = task.assigned_to if task.assigned_to else 0
        form.epic_id.data = task.epic_id if task.epic_id else 0
        form.parent_task_id.data = task.parent_task_id if task.parent_task_id else 0
        form.task_type.data = task.task_type or 'Task'

    if form.validate_on_submit():
        data = {
            'title': form.title.data,
            'description': form.description.data,
            'priority': form.priority.data,
            'status': form.status.data,
            'due_date': form.due_date.data,
            'estimated_hours': form.estimated_hours.data,
            'assigned_to': form.assigned_to.data if form.assigned_to.data else None,
            'task_type': form.task_type.data,
            'epic_id': form.epic_id.data if form.epic_id.data else None,
            'parent_task_id': form.parent_task_id.data if form.parent_task_id.data else None
        }
        if hasattr(form, 'milestone_id'):
            data['milestone_id'] = form.milestone_id.data if form.milestone_id.data else None

        services.update_task(task, data, current_user.id)
        db.session.commit()
        flash(f'Task "{task.title}" updated.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
        
    return render_template('pm/task_form.html', form=form, project=project, title="Edit Task")


@bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@module_required('pm')
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    project = task.project
    if not _is_pm_or_admin(current_user, project):
        abort(403)
    task_title = task.title
    log_audit(current_user.id, 'DELETE', 'Task', task.id,
              f'Deleted task "{task_title}"')
    db.session.delete(task)
    db.session.commit()
    flash(f'Task "{task_title}" deleted.', 'info')
    return redirect(url_for('pm.project_detail', project_id=project.id))


@bp.route('/tasks/<int:task_id>/log-hours', methods=['POST'])
@module_required('pm')
def log_task_hours(task_id):
    """Quick hour logging from project detail page."""
    task = Task.query.get_or_404(task_id)
    hours = request.form.get('hours', type=float)
    if not hours or hours <= 0:
        flash('Invalid hours.', 'danger')
        return redirect(url_for('pm.project_detail', project_id=task.project_id))
    services.log_task_hours(task, hours, current_user.id)
    db.session.commit()
    flash(f'{hours}h logged on "{task.title}".', 'success')
    return redirect(url_for('pm.project_detail', project_id=task.project_id))


# ===========================================================================
# MILESTONE MANAGEMENT
# ===========================================================================
@bp.route('/projects/<int:project_id>/milestones/add', methods=['GET', 'POST'])
@module_required('pm')
def add_milestone(project_id):
    project = Project.query.get_or_404(project_id)
    if not _is_pm_or_admin(current_user, project):
        abort(403)
    form = MilestoneForm()
    if form.validate_on_submit():
        data = {
            'project_id': project.id,
            'title': form.title.data,
            'description': form.description.data,
            'deadline': form.deadline.data
        }
        ms = services.create_milestone(data, current_user.id)
        db.session.commit()
        flash(f'Milestone "{ms.title}" created.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
        
    return render_template('pm/milestone_form.html', form=form, project=project, title="Add Milestone")


@bp.route('/milestones/<int:milestone_id>/edit', methods=['GET', 'POST'])
@module_required('pm')
def edit_milestone(milestone_id):
    ms = Milestone.query.get_or_404(milestone_id)
    project = ms.project
    if not _is_pm_or_admin(current_user, project):
        abort(403)
        
    form = MilestoneForm(obj=ms)
    
    if form.validate_on_submit():
        ms.title = form.title.data
        ms.description = form.description.data
        ms.status = form.status.data
        ms.deadline = form.deadline.data
        
        log_audit(current_user.id, 'UPDATE', 'Milestone', ms.id,
                  f'Updated milestone "{ms.title}"')
        db.session.commit()
        flash(f'Milestone "{ms.title}" updated.', 'success')
        return redirect(url_for('pm.project_detail', project_id=project.id))
        
    return render_template('pm/milestone_form.html', form=form, project=project, title="Edit Milestone")


@bp.route('/milestones/<int:milestone_id>/delete', methods=['POST'])
@module_required('pm')
def delete_milestone(milestone_id):
    ms = Milestone.query.get_or_404(milestone_id)
    project = ms.project
    if not _is_pm_or_admin(current_user, project):
        abort(403)
    title = ms.title
    log_audit(current_user.id, 'DELETE', 'Milestone', ms.id,
              f'Deleted milestone "{title}"')
    db.session.delete(ms)
    db.session.commit()
    flash(f'Milestone "{title}" deleted.', 'info')
    return redirect(url_for('pm.project_detail', project_id=project.id))

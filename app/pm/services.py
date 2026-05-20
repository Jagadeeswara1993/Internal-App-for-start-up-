from datetime import datetime
from app.extensions import db
from app.models import Project, Task, Milestone, ProjectMember, Timesheet, Epic
from app.utils.audit import log_audit
from app.pm.routes.helpers import notify

# ===========================================================================
# PROJECT SERVICES
# ===========================================================================
def create_project(data, creator_id):
    """Create a new project and notify the assigned PM."""
    project = Project(
        name=data.get('name').strip(),
        description=data.get('description', ''),
        start_date=data.get('start_date'),
        end_date=data.get('end_date'),
        deadline=data.get('deadline'),
        estimated_hours=data.get('estimated_hours', 0.0),
        status=data.get('status'),
        assigned_pm=data.get('assigned_pm'),
        created_by=creator_id
    )
    db.session.add(project)
    db.session.flush()

    log_audit(creator_id, 'CREATE', 'Project', project.id, f'Created project "{project.name}"')
    
    if project.assigned_pm:
        notify(project.assigned_pm, 'Project Assigned',
               f'You have been assigned as Project Manager for "{project.name}".',
               category='info', link=f'/pm/projects/{project.id}')
    return project

def update_project(project, data, updater_id, is_admin=False):
    """Update an existing project and check for delays."""
    old_status = project.status
    project.name = data.get('name', project.name).strip()
    project.description = data.get('description', project.description)
    project.start_date = data.get('start_date', project.start_date)
    project.end_date = data.get('end_date', project.end_date)
    project.deadline = data.get('deadline', project.deadline)
    project.estimated_hours = data.get('estimated_hours', project.estimated_hours)
    project.status = data.get('status', project.status)
    
    if is_admin and 'assigned_pm' in data:
        project.assigned_pm = data.get('assigned_pm')

    log_audit(updater_id, 'UPDATE', 'Project', project.id, f'Updated project "{project.name}"')
    
    if project.is_delayed and old_status != project.status:
        notify(project.created_by, 'Project Delayed',
               f'Project "{project.name}" is past its deadline.',
               category='warning', link=f'/pm/projects/{project.id}')
    return project

# ===========================================================================
# EPIC SERVICES
# ===========================================================================
def create_epic(data, creator_id):
    """Create a new epic."""
    epic = Epic(
        project_id=data.get('project_id'),
        title=data.get('title').strip(),
        description=data.get('description', ''),
        status=data.get('status', 'To Do'),
        color_label=data.get('color_label', '#6366f1')
    )
    db.session.add(epic)
    db.session.flush()

    project = Project.query.get(epic.project_id)
    log_audit(creator_id, 'CREATE', 'Epic', epic.id,
              f'Created epic "{epic.title}" in project "{project.name}"')
    return epic

def update_epic(epic, data, updater_id):
    """Update an existing epic."""
    epic.title = data.get('title', epic.title).strip()
    epic.description = data.get('description', epic.description)
    epic.status = data.get('status', epic.status)
    epic.color_label = data.get('color_label', epic.color_label)

    log_audit(updater_id, 'UPDATE', 'Epic', epic.id, f'Updated epic "{epic.title}"')
    return epic

# ===========================================================================
# TASK SERVICES
# ===========================================================================
def create_task(data, creator_id):
    """Create a new task and notify the assignee."""
    task_type = data.get('task_type', 'Task')
    parent_task_id = data.get('parent_task_id')
    if parent_task_id:
        task_type = 'Sub-task'

    task = Task(
        project_id=data.get('project_id'),
        title=data.get('title'),
        description=data.get('description', ''),
        assigned_to=data.get('assigned_to'),
        priority=data.get('priority'),
        status='Pending',
        due_date=data.get('due_date'),
        estimated_hours=data.get('estimated_hours', 0.0),
        milestone_id=data.get('milestone_id'),
        epic_id=data.get('epic_id'),
        parent_task_id=parent_task_id,
        task_type=task_type
    )
    db.session.add(task)
    db.session.flush()

    project = Project.query.get(task.project_id)
    log_audit(creator_id, 'CREATE', 'Task', task.id,
              f'Created task "{task.title}" in project "{project.name}"')

    if task.assigned_to:
        notify(task.assigned_to, 'Task Assigned',
               f'You have been assigned task "{task.title}" in project "{project.name}".',
               category='info', link=f'/pm/projects/{project.id}')
    return task

def update_task(task, data, updater_id):
    """Update a task and notify assignee on status changes."""
    old_status = task.status
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.priority = data.get('priority', task.priority)
    new_status = data.get('status', task.status)
    task.status = new_status
    
    if 'assigned_to' in data:
        task.assigned_to = data.get('assigned_to')
    if 'due_date' in data:
        task.due_date = data.get('due_date')
    if 'estimated_hours' in data:
        task.estimated_hours = data.get('estimated_hours')
    if 'milestone_id' in data:
        task.milestone_id = data.get('milestone_id')
    if 'epic_id' in data:
        task.epic_id = data.get('epic_id')
    if 'parent_task_id' in data:
        task.parent_task_id = data.get('parent_task_id')
        if task.parent_task_id:
            task.task_type = 'Sub-task'
    if 'task_type' in data and not task.parent_task_id:
        task.task_type = data.get('task_type', task.task_type)

    log_audit(updater_id, 'UPDATE', 'Task', task.id, f'Status: {old_status}→{new_status}')

    if task.assigned_to and old_status != new_status:
        project = Project.query.get(task.project_id)
        notify(task.assigned_to, 'Task Updated',
               f'Task "{task.title}" status changed from {old_status} to {new_status}.',
               category='info', link=f'/pm/projects/{project.id}')

    # Auto-complete parent when all subtasks are Done
    if new_status == 'Done' and task.parent_task_id:
        parent = Task.query.get(task.parent_task_id)
        if parent:
            all_done = parent.subtasks.filter(Task.status != 'Done').count() == 0
            if all_done and parent.status != 'Done':
                parent.status = 'Done'
                log_audit(updater_id, 'AUTO_COMPLETE', 'Task', parent.id,
                          f'Auto-completed parent task "{parent.title}" (all subtasks done)')

    return task

def update_task_status(task_id, new_status, updater_id):
    """Lightweight status update for Kanban drag-drop."""
    task = Task.query.get(task_id)
    if not task:
        return None
    old_status = task.status
    task.status = new_status
    task.updated_at = datetime.utcnow()

    log_audit(updater_id, 'STATUS_CHANGE', 'Task', task.id,
              f'Status: {old_status}→{new_status} (board)')

    if task.assigned_to and old_status != new_status:
        project = Project.query.get(task.project_id)
        notify(task.assigned_to, 'Task Status Changed',
               f'Task "{task.title}" moved from {old_status} to {new_status}.',
               category='info', link=f'/pm/projects/{project.id}')

    # Auto-complete parent when all subtasks are Done
    if new_status == 'Done' and task.parent_task_id:
        parent = Task.query.get(task.parent_task_id)
        if parent:
            all_done = parent.subtasks.filter(Task.status != 'Done').count() == 0
            if all_done and parent.status != 'Done':
                parent.status = 'Done'
                log_audit(updater_id, 'AUTO_COMPLETE', 'Task', parent.id,
                          f'Auto-completed parent "{parent.title}"')

    return task

def log_task_hours(task, hours, updater_id):
    """Log actual hours on a task."""
    task.actual_hours = (task.actual_hours or 0) + hours
    log_audit(updater_id, 'LOG_HOURS', 'Task', task.id, f'Logged {hours}h on "{task.title}"')
    return task

# ===========================================================================
# MILESTONE SERVICES
# ===========================================================================
def create_milestone(data, creator_id):
    """Create a new milestone."""
    ms = Milestone(
        project_id=data.get('project_id'),
        title=data.get('title'),
        description=data.get('description', ''),
        deadline=data.get('deadline'),
        status='Pending'
    )
    db.session.add(ms)
    db.session.flush()

    project = Project.query.get(ms.project_id)
    log_audit(creator_id, 'CREATE', 'Milestone', ms.id,
              f'Created milestone "{ms.title}" in "{project.name}"')
    return ms

# ===========================================================================
# TIMESHEET SERVICES
# ===========================================================================
def approve_timesheet(ts, approver_id):
    """Approve a timesheet and add to task actual hours."""
    ts.status = 'Approved'
    ts.approved_by = approver_id
    ts.approved_at = datetime.utcnow()
    
    if ts.task_id:
        task = Task.query.get(ts.task_id)
        if task:
            task.actual_hours = (task.actual_hours or 0) + ts.hours_worked

    log_audit(approver_id, 'APPROVE', 'Timesheet', ts.id,
              f'Approved {ts.hours_worked}h for emp#{ts.employee_id}')
    notify(ts.employee.user_id, 'Timesheet Approved',
           f'Your timesheet for {ts.date.strftime("%d %b %Y")} ({ts.hours_worked}h) has been approved.',
           category='success', link='/employee/timesheets')
    return True

def reject_timesheet(ts, reason, approver_id):
    """Reject a timesheet."""
    ts.status = 'Rejected'
    ts.rejection_reason = reason
    log_audit(approver_id, 'REJECT', 'Timesheet', ts.id,
              f'Rejected timesheet for emp#{ts.employee_id}: {reason}')
    notify(ts.employee.user_id, 'Timesheet Rejected',
           f'Your timesheet for {ts.date.strftime("%d %b %Y")} was rejected: {reason}',
           category='danger', link='/employee/timesheets')
    return True

def bulk_approve_timesheets(timesheets, approver_id):
    """Approve multiple timesheets."""
    count = 0
    for ts in timesheets:
        if ts and ts.status == 'Pending':
            ts.status = 'Approved'
            ts.approved_by = approver_id
            ts.approved_at = datetime.utcnow()
            
            if ts.task_id:
                task = Task.query.get(ts.task_id)
                if task:
                    task.actual_hours = (task.actual_hours or 0) + ts.hours_worked
            
            notify(ts.employee.user_id, 'Timesheet Approved',
                   f'Your timesheet for {ts.date.strftime("%d %b %Y")} ({ts.hours_worked}h) approved.',
                   category='success', link='/employee/timesheets')
            count += 1

    if count > 0:
        log_audit(approver_id, 'BULK_APPROVE', 'Timesheet', None, f'Bulk approved {count} timesheet(s)')
    return count

# ===========================================================================
# TEAM MEMBER SERVICES
# ===========================================================================
def add_team_member(project, user_id, role, creator_id):
    existing = ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first()
    if existing:
        return False, 'User is already a member of this project.'
        
    member = ProjectMember(project_id=project.id, user_id=user_id, role=role)
    db.session.add(member)
    db.session.flush()
    
    from app.models import User
    user = User.query.get(user_id)
    notify(user_id, 'Added to Project',
           f'You have been added to project "{project.name}" as {role}.',
           category='info', link=f'/pm/projects/{project.id}')
    log_audit(creator_id, 'CREATE', 'ProjectMember', None,
              f'Added {user.full_name} to project "{project.name}" as {role}')
    return True, f'{user.full_name} added as {role}.'

def remove_team_member(member, remover_id):
    user_name = member.user.full_name
    notify(member.user_id, 'Removed from Project',
           f'You have been removed from project "{member.project.name}".',
           category='warning')
    log_audit(remover_id, 'DELETE', 'ProjectMember', member.id,
              f'Removed {user_name} from project')
    db.session.delete(member)
    return True, f'{user_name} removed.'

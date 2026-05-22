import re
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db



# ===========================================================================
# PROJECT MANAGEMENT MODELS — UPGRADED
# ===========================================================================

# ---------------------------------------------------------------------------
# Project — UPGRADED with lifecycle, deadline, unique name, progress
# ---------------------------------------------------------------------------
class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)   # prevent duplicates
    description = db.Column(db.Text, default='')
    start_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    deadline = db.Column(db.Date, nullable=True)                     # NEW — hard deadline
    estimated_hours = db.Column(db.Float, default=0.0)               # NEW - estimated hours
    status = db.Column(db.String(30), default='Not Started')         # Not Started, In Progress, Completed, On Hold
    assigned_pm = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Project Manager
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    pm_owner = db.relationship('User', foreign_keys=[assigned_pm], backref='managed_projects')
    members = db.relationship('ProjectMember', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    milestones = db.relationship('Milestone', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    epics = db.relationship('Epic', backref='project', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def progress(self):
        """Calculate project progress (%) based on completed tasks."""
        total = self.tasks.count()
        if total == 0:
            return 0
        done = self.tasks.filter_by(status='Done').count()
        return round((done / total) * 100)

    def check_and_update_status(self):
        """Automatically set project status to Completed if progress is 100%."""
        if self.tasks.count() > 0:
            if self.progress == 100 and self.status != 'Completed':
                self.status = 'Completed'
            elif self.progress < 100 and self.status == 'Completed':
                self.status = 'In Progress'

    @property
    def is_delayed(self):
        """Check if project is past deadline but not completed."""
        if self.deadline and self.status != 'Completed':
            return date.today() > self.deadline
        return False

    def __repr__(self):
        return f'<Project {self.name}>'


# ---------------------------------------------------------------------------
# ProjectMember — UPGRADED with expanded project roles
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# ProjectMember — UPGRADED with expanded project roles
# ---------------------------------------------------------------------------
class ProjectMember(db.Model):
    __tablename__ = 'project_members'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(50), default='Developer')  # Developer, Tester, Designer, Lead, Observer
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='project_memberships')
    __table_args__ = (db.UniqueConstraint('project_id', 'user_id', name='uq_project_user'),)

    def __repr__(self):
        return f'<ProjectMember P{self.project_id} U{self.user_id}>'


# ---------------------------------------------------------------------------
# Epic — NEW (Jira-inspired grouping for tasks)
# ---------------------------------------------------------------------------
class Epic(db.Model):
    __tablename__ = 'epics'

    id          = db.Column(db.Integer, primary_key=True)
    project_id  = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title       = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    status      = db.Column(db.String(30), default='To Do')   # To Do, In Progress, Done
    color_label = db.Column(db.String(7), default='#6366f1')   # hex color for board swimlane
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks       = db.relationship('Task', backref='epic', lazy='dynamic')

    __table_args__ = (db.UniqueConstraint('project_id', 'title', name='uq_project_epic'),)

    @property
    def progress(self):
        """Calculate progress using hour-weighted Earned Value logic:
        - Standalone tasks and subtasks are counted (parent container tasks are excluded to avoid double-counting).
        - If a task is Done: it contributes its full estimated hours.
        - If a task is In Progress/Pending: it contributes its actual hours worked (capped at estimated hours).
        - Falls back to count-based progress if total estimated hours is 0.
        """
        from sqlalchemy import or_
        # Get direct tasks belonging to the epic
        direct_tasks = self.tasks.all()
        direct_task_ids = [t.id for t in direct_tasks]
        if not direct_task_ids:
            return 0
            
        # Get all tasks and subtasks associated with this epic
        all_tasks = Task.query.filter(
            or_(
                Task.epic_id == self.id,
                Task.parent_task_id.in_(direct_task_ids)
            )
        ).all()
        
        if not all_tasks:
            return 0
            
        # Filter to leaf tasks only (exclude parent tasks that have subtasks)
        leaf_tasks = [t for t in all_tasks if not t.is_parent]
        if not leaf_tasks:
            return 0
            
        total_estimated = sum(t.estimated_hours or 0.0 for t in leaf_tasks)
        
        # Fallback to count-based calculation if there are no estimated hours defined
        if total_estimated == 0.0:
            done_count = sum(1 for t in leaf_tasks if t.status == 'Done')
            return round((done_count / len(leaf_tasks)) * 100)
            
        completed_hours = 0.0
        for t in leaf_tasks:
            est = t.estimated_hours or 0.0
            act = t.actual_hours or 0.0
            if t.status == 'Done':
                # Earn full estimate
                completed_hours += est
            else:
                # Earn actual hours, capped at estimated hours to prevent over-progress
                completed_hours += min(act, est)
                
        return min(100, round((completed_hours / total_estimated) * 100))


    def check_and_update_status(self):
        """Auto-update epic status based on task completion.
        - All tasks Done → Epic 'Done'
        - Any task In Progress or Done → Epic 'In Progress'
        - Otherwise → Epic 'To Do'
        """
        from sqlalchemy import or_
        direct_task_ids = [t.id for t in self.tasks]
        if not direct_task_ids:
            return
        all_tasks = Task.query.filter(
            or_(
                Task.epic_id == self.id,
                Task.parent_task_id.in_(direct_task_ids)
            )
        ).all()
        if not all_tasks:
            return
        statuses = {t.status for t in all_tasks}
        if statuses == {'Done'}:
            self.status = 'Done'
        elif 'In Progress' in statuses or 'Done' in statuses:
            self.status = 'In Progress'
        else:
            self.status = 'To Do'

    def __repr__(self):
        return f'<Epic {self.title}>'


# ---------------------------------------------------------------------------
# Task — UPGRADED with hierarchy (Epic + Sub-tasks) and task_type
# ---------------------------------------------------------------------------
class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    priority = db.Column(db.String(20), default='Medium')    # Low, Medium, High, Critical
    status = db.Column(db.String(20), default='Pending')     # Pending, In Progress, Done
    estimated_hours = db.Column(db.Float, default=0.0)       # PM's estimate
    actual_hours = db.Column(db.Float, default=0.0)          # Employee's actual spent hours
    due_date = db.Column(db.Date, nullable=True)
    milestone_id = db.Column(db.Integer, db.ForeignKey('milestones.id'), nullable=True)
    # ── NEW: Hierarchy fields ──
    epic_id = db.Column(db.Integer, db.ForeignKey('epics.id', ondelete='SET NULL'), nullable=True)
    parent_task_id = db.Column(db.Integer, db.ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True)
    task_type = db.Column(db.String(20), default='Task')     # Task, Story, Bug, Sub-task
    # ──────────────────────────
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    milestone = db.relationship('Milestone', backref=db.backref('tasks', lazy='dynamic'))
    subtasks = db.relationship('Task',
                               backref=db.backref('parent_task', remote_side='Task.id'),
                               lazy='dynamic')

    @property
    def is_parent(self):
        """Check if this task has sub-tasks."""
        return self.subtasks.count() > 0

    @property
    def total_estimated_hours(self):
        """Sum of subtask estimated hours (or own if no subtasks)."""
        if self.is_parent:
            return sum(s.estimated_hours or 0 for s in self.subtasks)
        return self.estimated_hours or 0

    @property
    def total_actual_hours(self):
        """Sum of subtask actual hours (or own if no subtasks)."""
        if self.is_parent:
            return sum(s.actual_hours or 0 for s in self.subtasks)
        return self.actual_hours or 0

    def __repr__(self):
        return f'<Task {self.title}>'


# ---------------------------------------------------------------------------
# Milestone — NEW
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Milestone — NEW
# ---------------------------------------------------------------------------
class Milestone(db.Model):
    __tablename__ = 'milestones'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    deadline = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(30), default='Pending')     # Pending, In Progress, Completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('project_id', 'title', name='uq_project_milestone'),)

    @property
    def is_overdue(self):
        if self.deadline and self.status != 'Completed':
            return date.today() > self.deadline
        return False

    def __repr__(self):
        return f'<Milestone {self.title}>'


# ---------------------------------------------------------------------------
# Notification — NEW (system notifications for PM events)
# ---------------------------------------------------------------------------



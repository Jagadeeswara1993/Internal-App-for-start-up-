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
# Task — UPGRADED with updated_at tracking
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Task — UPGRADED with updated_at tracking
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    milestone = db.relationship('Milestone', backref=db.backref('tasks', lazy='dynamic'))

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



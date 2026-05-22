"""PM helper functions shared across route sub-modules."""

from flask import request
from app.extensions import db
from app.models import Project, ProjectMember, Notification, AuditLog


def _get_user_projects(user):
    """Return projects visible to the user based on role hierarchy."""
    if user.is_admin:
        return Project.query.order_by(Project.created_at.desc()).all()
    pm_projects = Project.query.filter_by(assigned_pm=user.id).all()
    if pm_projects:
        return pm_projects
    member_project_ids = db.session.query(ProjectMember.project_id).filter_by(user_id=user.id).subquery()
    return Project.query.filter(Project.id.in_(member_project_ids)).order_by(Project.created_at.desc()).all()


def _is_pm_or_admin(user, project):
    """Check if user is the assigned PM or an admin."""
    return user.is_admin or project.assigned_pm == user.id


def _can_view_project(user, project):
    """Check if user can view this project."""
    if user.is_admin or project.assigned_pm == user.id:
        return True
    return ProjectMember.query.filter_by(project_id=project.id, user_id=user.id).first() is not None


def notify(user_id, title, message, category='info', link=''):
    """Create a notification for a user."""
    from app.models import User
    user = User.query.get(user_id)
    if user and link.startswith('/pm/'):
        # If the user does not have pm access, redirect them to the employee equivalent
        if not (user.is_admin or user.has_module('pm')):
            if '/projects/' in link:
                if 'Project' in title or 'Added' in title:
                    link = '/employee/projects'
                else:
                    link = '/employee/tasks'
            else:
                link = '/employee/tasks'
    n = Notification(user_id=user_id, title=title, message=message,
                     category=category, link=link)
    db.session.add(n)


from app.utils.audit import log_audit

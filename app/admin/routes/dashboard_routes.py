"""Admin dashboard route."""

from flask import render_template
from app.admin import bp
from app.decorators import admin_required
from app.models import (User, Module, Employee, Project, Notification,
                        Department, Designation, Shift, LeavePolicy, Timesheet)


@bp.route('/')
@admin_required
def dashboard():
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active_user=True).count()
    total_modules = Module.query.count()
    total_employees = Employee.query.count()
    total_projects = Project.query.count()
    total_notifications = Notification.query.count()
    total_departments = Department.query.count()
    total_designations = Designation.query.count()
    total_shifts = Shift.query.filter_by(is_active=True).count()
    total_leave_policies = LeavePolicy.query.filter_by(is_active=True).count()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    # Count unassigned employees for onboarding visibility
    from app.hr import services as hr_services
    unassigned_employees = hr_services.get_unassigned_count()

    # Timesheet stats
    total_timesheets = Timesheet.query.count()
    pending_timesheets = Timesheet.query.filter_by(status='Pending').count()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           active_users=active_users,
                           total_modules=total_modules,
                           total_employees=total_employees,
                           total_projects=total_projects,
                           total_notifications=total_notifications,
                           total_departments=total_departments,
                           total_designations=total_designations,
                           total_shifts=total_shifts,
                           total_leave_policies=total_leave_policies,
                           recent_users=recent_users,
                           unassigned_employees=unassigned_employees,
                           total_timesheets=total_timesheets,
                           pending_timesheets=pending_timesheets)

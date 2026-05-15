"""Employee dashboard route."""

from datetime import date
from flask import render_template
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, Attendance, Leave, Notification,
                        PerformanceReview, Timesheet, Task, ProjectMember)


@bp.route('/')
@module_required('employee')
def dashboard():
    from app.employee import services
    from app.hr import services as hr_services

    employee = Employee.query.filter_by(user_id=current_user.id).first_or_404()

    today_att = None
    leave_balances = []
    pending_leaves = 0
    att_summary = {}
    profile_complete = False
    shift_rules = None
    comp_off_count = 0

    if employee:
        profile_complete = hr_services.is_employee_profile_complete(employee)
        today_att = services.get_today_attendance(employee.id)
        leave_balances = services.get_my_leave_balances(employee.id)
        pending_leaves = len(services.get_my_leaves(employee.id, status='Pending'))
        att_summary = services.get_my_attendance_summary(employee.id)
        shift_rules = services.get_my_shift_rules(employee.id)
        comp_off_count = len([c for c in services.get_my_comp_offs(employee.id) if c.status == 'Earned'])

    tasks = services.get_my_tasks(current_user.id)
    tasks_pending = sum(1 for t in tasks if t.status != 'Done')
    tasks_done = sum(1 for t in tasks if t.status == 'Done')
    notifications = services.get_my_notifications(current_user.id, limit=5)
    unread_count = services.get_unread_count(current_user.id)

    # Timesheet summary for dashboard
    ts_summary = services.get_timesheet_summary(employee.id) if employee else {
        'total_entries': 0, 'total_hours': 0, 'approved_hours': 0,
        'pending_hours': 0, 'rejected_count': 0
    }

    # Manager: team pending count for dashboard card
    team_pending = 0
    team_size = 0
    is_manager = False
    if employee and services.is_manager(employee.id):
        is_manager = True
        team_pending = services.get_team_pending_count(employee.id)
        team_size = len(services.get_direct_reports(employee.id))

    return render_template('employee/dashboard.html',
                           employee=employee,
                           profile_complete=profile_complete,
                           today_att=today_att,
                           leave_balances=leave_balances,
                           pending_leaves=pending_leaves,
                           att_summary=att_summary,
                           shift_rules=shift_rules,
                           comp_off_count=comp_off_count,
                           tasks=tasks[:5],
                           tasks_pending=tasks_pending,
                           tasks_done=tasks_done,
                           notifications=notifications,
                           unread_count=unread_count,
                           ts_summary=ts_summary,
                           is_manager=is_manager,
                           team_pending=team_pending,
                           team_size=team_size)

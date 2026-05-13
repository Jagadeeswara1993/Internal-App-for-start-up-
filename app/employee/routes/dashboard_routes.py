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
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()

    today = date.today()
    today_att = Attendance.query.filter_by(employee_id=emp.id, date=today).first()
    pending_leaves = Leave.query.filter_by(employee_id=emp.id, status='Pending').count()
    approved_leaves = Leave.query.filter_by(employee_id=emp.id, status='Approved').count()
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, is_read=False
    ).count()
    recent_reviews = PerformanceReview.query.filter_by(employee_id=emp.id)\
        .order_by(PerformanceReview.created_at.desc()).limit(3).all()

    recent_attendance = Attendance.query.filter_by(employee_id=emp.id)\
        .order_by(Attendance.date.desc()).limit(5).all()

    # Timesheet stats
    pending_timesheets = Timesheet.query.filter_by(employee_id=emp.id, status='Pending').count()
    approved_ts_hours = db.session.query(
        db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)
    ).filter_by(employee_id=emp.id, status='Approved').scalar()

    # Task stats
    my_tasks = Task.query.filter_by(assigned_to=current_user.id).all()
    tasks_pending = sum(1 for t in my_tasks if t.status == 'Pending')
    tasks_in_progress = sum(1 for t in my_tasks if t.status == 'In Progress')
    tasks_done = sum(1 for t in my_tasks if t.status == 'Done')

    # Project count
    member_projects = ProjectMember.query.filter_by(user_id=current_user.id).count()

    return render_template('employee/dashboard.html',
                           employee=emp, today_att=today_att,
                           pending_leaves=pending_leaves,
                           approved_leaves=approved_leaves,
                           unread_notifications=unread_notifications,
                           unread_count=unread_notifications,
                           recent_reviews=recent_reviews,
                           recent_attendance=recent_attendance,
                           pending_timesheets=pending_timesheets,
                           approved_ts_hours=round(approved_ts_hours, 1),
                           tasks_pending=tasks_pending,
                           tasks_in_progress=tasks_in_progress,
                           tasks_done=tasks_done,
                           member_projects=member_projects)

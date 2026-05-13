"""HR dashboard route."""

from datetime import date
from flask import render_template
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, Leave, Attendance, Department,
                        Shift, CompOff, ShiftSwapRequest, Timesheet)
from app.hr import services


@bp.route('/')
@module_required('hr')
def dashboard():
    total_employees = Employee.query.count()
    pending_leaves = Leave.query.filter_by(status='Pending').count()
    approved_leaves = Leave.query.filter_by(status='Approved').count()

    today = date.today()
    today_records = Attendance.query.filter_by(date=today).all()
    today_present = sum(1 for r in today_records if r.status in ('Present', 'Late'))
    today_late = sum(1 for r in today_records if r.status == 'Late')
    today_absent = total_employees - len(today_records) if total_employees > 0 else 0

    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    dept_stats = []
    for dept in departments:
        count = dept.employees.count()
        if count > 0:
            dept_stats.append({'name': dept.name, 'count': count})

    recent_leaves = Leave.query.order_by(Leave.created_at.desc()).limit(5).all()
    rules = services.get_attendance_rules()
    unassigned_count = services.get_unassigned_count()
    pending_swaps = ShiftSwapRequest.query.filter_by(status='Pending').count()
    pending_comp_offs = CompOff.query.filter_by(status='Earned').count()
    total_shifts = Shift.query.filter_by(is_active=True).count()

    total_timesheets = Timesheet.query.count()
    pending_timesheets = Timesheet.query.filter_by(status='Pending').count()
    approved_ts_hours = db.session.query(
        db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)
    ).filter_by(status='Approved').scalar()

    return render_template('hr/dashboard.html',
                           total_employees=total_employees,
                           pending_leaves=pending_leaves,
                           approved_leaves=approved_leaves,
                           today_present=today_present,
                           today_late=today_late,
                           today_absent=today_absent,
                           dept_stats=dept_stats,
                           recent_leaves=recent_leaves,
                           rules=rules,
                           unassigned_count=unassigned_count,
                           pending_swaps=pending_swaps,
                           pending_comp_offs=pending_comp_offs,
                           total_shifts=total_shifts,
                           total_timesheets=total_timesheets,
                           pending_timesheets=pending_timesheets,
                           approved_ts_hours=round(approved_ts_hours, 1))

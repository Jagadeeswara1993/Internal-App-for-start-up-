"""HR leave management routes."""

import json
from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime, timedelta
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, Leave, LeavePolicy, Notification, Holiday, Department
from app.hr.forms import LeaveActionForm
from app.hr import services


@bp.route('/leaves')
@module_required('hr')
def leaves():
    status_filter = request.args.get('status', '')
    query = Leave.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    page = request.args.get('page', 1, type=int)
    all_leaves = query.order_by(Leave.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('hr/leaves.html', leaves=all_leaves,
                           selected_status=status_filter)


@bp.route('/leaves/<int:leave_id>/action', methods=['POST'])
@module_required('hr')
def leave_action(leave_id):
    form = LeaveActionForm()
    if form.validate_on_submit():
        if form.status.data == 'Approved':
            success, msg = services.approve_leave(leave_id, current_user.id)
        else:
            success, msg = services.reject_leave(leave_id, current_user.id,
                                                  form.rejection_reason.data or '')
        if success:
            services.log_audit(current_user.id, form.status.data.upper(), 'Leave', leave_id,
                              msg, request.remote_addr or '')
            db.session.commit()
            flash(msg, 'success')
        else:
            flash(msg, 'danger')
    return redirect(url_for('hr.leaves'))


@bp.route('/leave-balances')
@module_required('hr')
def leave_balances():
    """Overview of all employees' leave balances."""
    from app.hr.services import _get_cycle_label_year
    year = request.args.get('year', _get_cycle_label_year(), type=int)
    employees = Employee.query.order_by(Employee.emp_code).all()
    policies = LeavePolicy.query.filter_by(is_active=True).order_by(LeavePolicy.leave_type).all()

    balance_data = []
    for emp in employees:
        balances = services.get_all_leave_balances(emp.id, year)
        bal_map = {b.leave_type: b for b in balances}
        balance_data.append({'employee': emp, 'balances': bal_map})

    return render_template('hr/leave_balances.html', balance_data=balance_data,
                           policies=policies, year=year)


# ===========================================================================
# LEAVE CANCELLATION (HR-Side)
# ===========================================================================
@bp.route('/leaves/<int:leave_id>/cancel', methods=['POST'])
@module_required('hr')
def cancel_leave(leave_id):
    """HR cancels an approved leave and restores balance."""
    leave = Leave.query.get_or_404(leave_id)
    if leave.status not in ('Approved', 'Pending'):
        flash(f'Cannot cancel — leave is already {leave.status}.', 'danger')
        return redirect(url_for('hr.leaves'))

    cancel_reason = request.form.get('reason', 'Cancelled by HR')

    if leave.status == 'Approved' and leave.total_days:
        from app.hr.services import _get_cycle_label_year
        balance = services.get_leave_balance(leave.employee_id, leave.leave_type, _get_cycle_label_year(leave.start_date))
        if balance:
            balance.used = max(0, balance.used - leave.total_days)

    leave.status = 'Cancelled'
    leave.cancelled_at = datetime.utcnow()
    leave.cancelled_reason = cancel_reason
    services.log_audit(current_user.id, 'CANCEL', 'Leave', leave.id,
                      f'Cancelled {leave.leave_type} for emp#{leave.employee_id}',
                      request.remote_addr or '')

    notif = Notification(
        user_id=leave.employee.user_id,
        title='Leave Cancelled',
        message=f'Your {leave.leave_type} leave ({leave.start_date} to {leave.end_date}) has been cancelled. Reason: {cancel_reason}',
        category='warning', link='/employee/leaves'
    )
    db.session.add(notif)
    db.session.commit()
    flash(f'Leave cancelled and balance restored.', 'warning')
    return redirect(url_for('hr.leaves'))


@bp.route('/leave-calendar')
@module_required('hr')
def leave_calendar():
    """Visual month-grid leave calendar for the entire organization."""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    dept_filter = request.args.get('department', 0, type=int)

    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()

    # Compute calendar grid data
    _, num_days = monthrange(year, month)
    first_weekday = date(year, month, 1).weekday()  # 0=Mon

    # Holidays this month
    holidays = Holiday.query.filter(
        db.extract('year', Holiday.holiday_date) == year,
        db.extract('month', Holiday.holiday_date) == month
    ).all()
    holiday_map = {h.holiday_date.day: h.holiday_name for h in holidays}

    # Approved leaves this month
    month_start = date(year, month, 1)
    month_end = date(year, month, num_days)

    leave_query = Leave.query.filter(
        Leave.status == 'Approved',
        Leave.start_date <= month_end,
        Leave.end_date >= month_start
    )
    if dept_filter:
        leave_query = leave_query.join(Employee).filter(Employee.department_id == dept_filter)
    approved_leaves = leave_query.all()

    # Build day -> list of absent employees
    day_absences = defaultdict(list)
    for lv in approved_leaves:
        emp = lv.employee
        s = max(lv.start_date, month_start)
        e = min(lv.end_date, month_end)
        current = s
        while current <= e:
            day_absences[current.day].append({
                'name': emp.user.full_name,
                'emp_code': emp.emp_code,
                'dept': emp.department_name,
                'leave_type': lv.leave_type,
                'is_half_day': lv.is_half_day
            })
            current += timedelta(days=1)

    # Employee count for "present" calculation
    emp_query = Employee.query.filter_by(is_active=True)
    if dept_filter:
        emp_query = emp_query.filter_by(department_id=dept_filter)
    total_employees = emp_query.count()

    # Build calendar data
    calendar_data = []
    for day in range(1, num_days + 1):
        d = date(year, month, day)
        is_weekend = d.weekday() >= 5
        is_holiday = day in holiday_map
        absences = day_absences.get(day, [])
        absent_count = len(absences)
        half_day_count = sum(1 for a in absences if a['is_half_day'])

        calendar_data.append({
            'day': day,
            'weekday': d.strftime('%a'),
            'is_weekend': is_weekend,
            'is_holiday': is_holiday,
            'holiday_name': holiday_map.get(day, ''),
            'is_today': d == date.today(),
            'absent_count': absent_count,
            'half_day_count': half_day_count,
            'present_count': max(0, total_employees - absent_count) if not is_weekend and not is_holiday else 0,
            'absences': absences
        })

    # Month navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    month_name = date(year, month, 1).strftime('%B %Y')

    return render_template('hr/leave_calendar.html',
                           calendar_data=calendar_data,
                           calendar_json=json.dumps(calendar_data),
                           first_weekday=first_weekday,
                           month_name=month_name,
                           year=year, month=month,
                           prev_year=prev_year, prev_month=prev_month,
                           next_year=next_year, next_month=next_month,
                           departments=departments,
                           selected_dept=dept_filter,
                           total_employees=total_employees)


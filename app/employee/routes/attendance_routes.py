"""Employee attendance routes — check-in/out, regularization, holidays."""

from datetime import date, datetime, time
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, Attendance, AttendanceRegularization,
                        Holiday, Notification)
from app.hr import services


@bp.route('/attendance')
@module_required('employee')
def attendance():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    records = Attendance.query.filter_by(employee_id=emp.id).filter(
        db.extract('month', Attendance.date) == month,
        db.extract('year', Attendance.date) == year
    ).order_by(Attendance.date.desc()).all()

    summary = services.get_attendance_summary(emp.id, year, month)
    today_att = Attendance.query.filter_by(employee_id=emp.id, date=date.today()).first()

    pending_regularizations = AttendanceRegularization.query.filter_by(
        employee_id=emp.id, status='Pending'
    ).count()

    return render_template('employee/attendance.html',
                           employee=emp, records=records, summary=summary,
                           today_att=today_att, month=month, year=year,
                           pending_regularizations=pending_regularizations)


@bp.route('/attendance/checkin', methods=['POST'])
@module_required('employee')
def attendance_checkin():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    now = datetime.now().time()
    success, msg = services.perform_checkin(emp.id, now.strftime('%H:%M'))
    if success:
        services.log_audit(current_user.id, 'CHECKIN', 'Attendance', emp.id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('employee.attendance'))


@bp.route('/attendance/checkout', methods=['POST'])
@module_required('employee')
def attendance_checkout():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    now = datetime.now().time()
    success, msg = services.perform_checkout(emp.id, now.strftime('%H:%M'))
    if success:
        services.log_audit(current_user.id, 'CHECKOUT', 'Attendance', emp.id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('employee.attendance'))


@bp.route('/attendance/regularization', methods=['GET', 'POST'])
@module_required('employee')
def attendance_regularization():
    """Request attendance regularization for a past date."""
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()

    my_requests = AttendanceRegularization.query.filter_by(employee_id=emp.id)\
        .order_by(AttendanceRegularization.created_at.desc()).limit(10).all()

    if request.method == 'POST':
        date_str = request.form.get('date', '').strip()
        reason = request.form.get('reason', '').strip()
        check_in = request.form.get('check_in', '').strip()
        check_out = request.form.get('check_out', '').strip()

        if not date_str or not reason:
            flash('Date and reason are required.', 'danger')
            return redirect(url_for('employee.attendance_regularization'))

        try:
            req_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return redirect(url_for('employee.attendance_regularization'))

        if req_date >= date.today():
            flash('Regularization is only for past dates.', 'danger')
            return redirect(url_for('employee.attendance_regularization'))

        existing = AttendanceRegularization.query.filter_by(
            employee_id=emp.id, date=req_date, status='Pending'
        ).first()
        if existing:
            flash('A pending request already exists for this date.', 'warning')
            return redirect(url_for('employee.attendance_regularization'))

        reg = AttendanceRegularization(
            employee_id=emp.id, date=req_date, reason=reason,
            requested_check_in=check_in or None,
            requested_check_out=check_out or None
        )
        db.session.add(reg)

        hr_notif = Notification(
            user_id=1,
            title='Attendance Regularization Request',
            message=f'{current_user.full_name} ({emp.emp_code}) requested regularization for {req_date}.',
            category='info', link='/hr/attendance-regularizations'
        )
        db.session.add(hr_notif)
        db.session.commit()
        flash('Regularization request submitted for HR review.', 'success')
        return redirect(url_for('employee.attendance_regularization'))

    return render_template('employee/attendance_regularization.html',
                           employee=emp, my_requests=my_requests)


@bp.route('/holidays')
@module_required('employee')
def holiday_calendar():
    """View company holiday calendar for the current year."""
    year = request.args.get('year', date.today().year, type=int)
    holidays = Holiday.query.filter(
        db.extract('year', Holiday.holiday_date) == year
    ).order_by(Holiday.holiday_date).all()
    return render_template('employee/holiday_calendar.html', holidays=holidays, year=year)

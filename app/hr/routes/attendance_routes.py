"""HR attendance routes — records, check-in, reports, export, override, regularization."""

import csv
import io
from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, User, Attendance, Department,
                        AttendanceRegularization, Notification)
from app.hr.forms import (CheckInOutForm, AttendanceFilterForm,
                          AttendanceOverrideForm)
from app.hr import services


@bp.route('/api/attendance')
@module_required('hr')
def api_attendance():
    """API for real-time attendance search by employee ID/name."""
    emp_query = request.args.get('employee_id', '').strip()
    query = Employee.query.join(User)
    if emp_query:
        query = query.filter(
            db.or_(
                Employee.emp_code.ilike(f'%{emp_query}%'),
                User.full_name.ilike(f'%{emp_query}%')
            )
        )
    employees = query.order_by(Employee.emp_code).all()
    today_records = {a.employee_id: a for a in Attendance.query.filter_by(date=date.today()).all()}
    results = []
    for emp in employees:
        rec = today_records.get(emp.id)
        results.append({
            'emp_code': emp.emp_code,
            'full_name': emp.user.full_name,
            'check_in': str(rec.check_in) if rec and rec.check_in else '—',
            'check_out': str(rec.check_out) if rec and rec.check_out else '—',
            'working_hours': f'{rec.working_hours:.1f}h' if rec and rec.working_hours else '—',
            'status': rec.status if rec else 'Not Recorded'
        })
    return jsonify(results)


@bp.route('/attendance')
@module_required('hr')
def attendance():
    emp_search = request.args.get('employee_id', '').strip()
    dept_id = request.args.get('department', type=int)
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Attendance.query.join(Employee).join(User)
    if emp_search:
        query = query.filter(
            db.or_(
                Employee.emp_code.ilike(f'%{emp_search}%'),
                User.full_name.ilike(f'%{emp_search}%')
            )
        )
    if dept_id:
        query = query.filter(Employee.department_id == dept_id)
    if status_filter:
        query = query.filter(Attendance.status == status_filter)
    if date_from:
        try:
            query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    page = request.args.get('page', 1, type=int)
    records = query.order_by(Attendance.date.desc()).paginate(page=page, per_page=25, error_out=False)
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    rules = services.get_attendance_rules()

    return render_template('hr/attendance.html', records=records,
                           departments=departments, rules=rules,
                           selected_dept=dept_id, selected_status=status_filter,
                           date_from=date_from, date_to=date_to,
                           emp_search=emp_search)


@bp.route('/attendance/check-in', methods=['GET', 'POST'])
@module_required('hr')
def attendance_checkin():
    form = CheckInOutForm()
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(0, '— Select Employee —')] + [
        (e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees
    ]
    today_records = {a.employee_id: a for a in Attendance.query.filter_by(date=date.today()).all()}

    if form.validate_on_submit():
        emp_id = form.employee_id.data
        if emp_id == 0:
            flash('Please select an employee.', 'danger')
        else:
            action = request.form.get('action', 'checkin')
            if action == 'checkout':
                success, msg = services.perform_checkout(emp_id, form.time.data)
            else:
                success, msg = services.perform_checkin(emp_id, form.time.data)
            if success:
                services.log_audit(current_user.id, action.upper(), 'Attendance', emp_id,
                                  msg, request.remote_addr or '')
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'danger')
        return redirect(url_for('hr.attendance_checkin'))

    return render_template('hr/attendance_checkin.html', form=form,
                           today_records=today_records, employees=employees)


@bp.route('/attendance/report')
@module_required('hr')
def attendance_report():
    """Monthly attendance summary report."""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    emp_search = request.args.get('employee_id', '').strip()

    query = Employee.query.join(User)
    if emp_search:
        query = query.filter(
            db.or_(
                Employee.emp_code.ilike(f'%{emp_search}%'),
                User.full_name.ilike(f'%{emp_search}%')
            )
        )
    employees = query.order_by(Employee.emp_code).all()

    report = []
    for emp in employees:
        summary = services.get_attendance_summary(emp.id, year, month)
        summary['employee'] = emp
        report.append(summary)

    return render_template('hr/attendance_report.html', report=report,
                           year=year, month=month, emp_search=emp_search)


@bp.route('/attendance/export')
@module_required('hr')
def export_attendance():
    """Export day-wise attendance as CSV."""
    emp_search = request.args.get('employee_id', '').strip()
    dept_id = request.args.get('department', type=int)
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Attendance.query.join(Employee).join(User)
    if emp_search:
        query = query.filter(db.or_(
            Employee.emp_code.ilike(f'%{emp_search}%'),
            User.full_name.ilike(f'%{emp_search}%')
        ))
    if dept_id:
        query = query.filter(Employee.department_id == dept_id)
    if status_filter:
        query = query.filter(Attendance.status == status_filter)
    if date_from:
        try:
            query = query.filter(Attendance.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Attendance.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    records = query.order_by(Attendance.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee ID', 'Employee Name', 'Department', 'Date', 'Check-In', 'Check-Out', 'Working Hours', 'Status'])
    for r in records:
        writer.writerow([
            r.employee.emp_code, r.employee.user.full_name, r.employee.department_name,
            r.date.strftime('%d %b %Y'),
            str(r.check_in) if r.check_in else '', str(r.check_out) if r.check_out else '',
            r.working_hours or 0, r.status
        ])

    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=attendance_export.csv'})


@bp.route('/attendance/report/export')
@module_required('hr')
def export_attendance_report():
    """Export month-wise attendance report as CSV."""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    emp_search = request.args.get('employee_id', '').strip()

    query = Employee.query.join(User)
    if emp_search:
        query = query.filter(db.or_(
            Employee.emp_code.ilike(f'%{emp_search}%'),
            User.full_name.ilike(f'%{emp_search}%')
        ))
    employees = query.order_by(Employee.emp_code).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee ID', 'Employee Name', 'Department', 'Month', 'Year',
                     'Present', 'Late', 'Absent', 'Half-Day', 'Total Hours', 'Effective Days'])
    for emp in employees:
        summary = services.get_attendance_summary(emp.id, year, month)
        writer.writerow([
            emp.emp_code, emp.user.full_name, emp.department_name, month, year,
            summary['present'], summary['late'], summary['absent'],
            summary['half_day'], summary['total_hours'], summary['effective_days']
        ])

    return Response(output.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=attendance_report_{year}_{month}.csv'})


# ===========================================================================
# ATTENDANCE OVERRIDE & AUTO-ABSENT
# ===========================================================================
@bp.route('/attendance/override', methods=['GET', 'POST'])
@module_required('hr')
def attendance_override():
    form = AttendanceOverrideForm()
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(0, '— Select Employee —')] + [
        (e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees
    ]
    if form.validate_on_submit():
        if form.employee_id.data == 0:
            flash('Please select an employee.', 'danger')
        else:
            success, msg = services.override_attendance(
                form.employee_id.data, form.date.data,
                form.status.data, form.check_in.data or '',
                form.check_out.data or '', form.notes.data or ''
            )
            if success:
                services.log_audit(current_user.id, 'OVERRIDE', 'Attendance',
                                  form.employee_id.data, msg, request.remote_addr or '')
                db.session.commit()
                flash(msg, 'success')
            else:
                flash(msg, 'danger')
        return redirect(url_for('hr.attendance_override'))
    return render_template('hr/attendance_override.html', form=form)


@bp.route('/attendance/auto-absent', methods=['POST'])
@module_required('hr')
def run_auto_absent():
    """Manually trigger auto-absent marking for yesterday."""
    count = services.auto_mark_absent()
    if count > 0:
        services.log_audit(current_user.id, 'AUTO_ABSENT', 'Attendance', None,
                          f'Marked {count} employees absent', request.remote_addr or '')
        db.session.commit()
        flash(f'{count} employee(s) marked absent.', 'warning')
    else:
        flash('No employees to mark absent.', 'info')
    return redirect(url_for('hr.attendance'))


# ===========================================================================
# ATTENDANCE REGULARIZATION APPROVALS (HR-Side)
# ===========================================================================
@bp.route('/attendance-regularizations')
@module_required('hr')
def attendance_regularizations():
    """View all attendance regularization requests."""
    status_filter = request.args.get('status', '')
    query = AttendanceRegularization.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    reqs = query.order_by(AttendanceRegularization.created_at.desc()).all()
    return render_template('hr/attendance_regularizations.html',
                           regularizations=reqs, selected_status=status_filter)


@bp.route('/attendance-regularizations/<int:reg_id>/approve', methods=['POST'])
@module_required('hr')
def approve_regularization(reg_id):
    """Approve an attendance regularization request."""
    reg = AttendanceRegularization.query.get_or_404(reg_id)
    if reg.status != 'Pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('hr.attendance_regularizations'))

    success, msg = services.override_attendance(
        reg.employee_id, reg.date,
        'Present', reg.requested_check_in, reg.requested_check_out,
        f'Regularized: {reg.reason}'
    )
    if success:
        reg.status = 'Approved'
        reg.reviewed_by = current_user.id
        reg.reviewed_at = datetime.utcnow()
        services.log_audit(current_user.id, 'APPROVE', 'AttendanceRegularization', reg.id,
                          msg, request.remote_addr or '')
        notif = Notification(
            user_id=reg.employee.user_id,
            title='Attendance Regularization Approved',
            message=f'Your regularization request for {reg.date} has been approved.',
            category='success', link='/employee/attendance'
        )
        db.session.add(notif)
        db.session.commit()
        flash(f'Regularization approved for {reg.employee.emp_code} on {reg.date}.', 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('hr.attendance_regularizations'))


@bp.route('/attendance-regularizations/<int:reg_id>/reject', methods=['POST'])
@module_required('hr')
def reject_regularization(reg_id):
    """Reject an attendance regularization request."""
    reg = AttendanceRegularization.query.get_or_404(reg_id)
    if reg.status != 'Pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('hr.attendance_regularizations'))

    rejection_reason = request.form.get('reason', '').strip()
    reg.status = 'Rejected'
    reg.reviewed_by = current_user.id
    reg.reviewed_at = datetime.utcnow()
    reg.rejection_reason = rejection_reason
    services.log_audit(current_user.id, 'REJECT', 'AttendanceRegularization', reg.id,
                      f'Rejected for {reg.date}', request.remote_addr or '')

    notif = Notification(
        user_id=reg.employee.user_id,
        title='Attendance Regularization Rejected',
        message=f'Your regularization request for {reg.date} was rejected. {rejection_reason}',
        category='warning', link='/employee/attendance'
    )
    db.session.add(notif)
    db.session.commit()
    flash('Regularization request rejected.', 'warning')
    return redirect(url_for('hr.attendance_regularizations'))

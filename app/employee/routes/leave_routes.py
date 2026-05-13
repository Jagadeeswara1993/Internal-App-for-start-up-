"""Employee leave management routes."""

from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, Leave, Notification
from app.employee.forms import LeaveRequestForm
from app.hr import services


@bp.route('/leaves')
@module_required('employee')
def my_leaves():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    status_filter = request.args.get('status', '')
    query = Leave.query.filter_by(employee_id=emp.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    leaves = query.order_by(Leave.created_at.desc()).all()
    return render_template('employee/my_leaves.html', leaves=leaves, employee=emp,
                           selected_status=status_filter)


@bp.route('/leaves/balance')
@module_required('employee')
def leave_balance():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    balances = services.get_all_leave_balances(emp.id)
    return render_template('employee/leave_balance.html', balances=balances, employee=emp)


@bp.route('/leaves/request', methods=['GET', 'POST'])
@module_required('employee')
def request_leave():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    form = LeaveRequestForm()
    balances = services.get_all_leave_balances(emp.id)
    form.leave_type.choices = [(b.leave_type, f'{b.leave_type} (Available: {b.remaining})') for b in balances]

    if form.validate_on_submit():
        if form.end_date.data < form.start_date.data:
            flash('End date must be after start date.', 'danger')
            return render_template('employee/leave_request.html', form=form, employee=emp)

        success, msg = services.apply_leave(
            employee_id=emp.id,
            leave_type=form.leave_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data or ''
        )
        if success:
            hr_notif = Notification(
                user_id=1,
                title='Leave Request',
                message=f'{current_user.full_name} ({emp.emp_code}) requested {form.leave_type.data} leave from {form.start_date.data} to {form.end_date.data}.',
                category='info', link='/hr/leaves'
            )
            db.session.add(hr_notif)
            db.session.commit()
            flash(msg, 'success')
            return redirect(url_for('employee.my_leaves'))
        else:
            flash(msg, 'danger')
    return render_template('employee/leave_request.html', form=form, employee=emp)


@bp.route('/leaves/<int:leave_id>/cancel', methods=['POST'])
@module_required('employee')
def cancel_leave(leave_id):
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    leave = Leave.query.filter_by(id=leave_id, employee_id=emp.id).first_or_404()

    if leave.status not in ('Pending', 'Approved'):
        flash(f'Cannot cancel — leave is already {leave.status}.', 'danger')
        return redirect(url_for('employee.my_leaves'))

    if leave.status == 'Approved' and leave.total_days:
        balance = services.get_leave_balance(emp.id, leave.leave_type, leave.start_date.year)
        if balance:
            balance.used = max(0, balance.used - leave.total_days)

    leave.status = 'Cancelled'
    leave.cancelled_at = datetime.utcnow()
    leave.cancelled_reason = 'Cancelled by employee'
    services.log_audit(current_user.id, 'CANCEL', 'Leave', leave.id,
                      f'Employee cancelled {leave.leave_type}', request.remote_addr or '')

    hr_notif = Notification(
        user_id=1,
        title='Leave Cancelled by Employee',
        message=f'{current_user.full_name} cancelled their {leave.leave_type} leave ({leave.start_date} to {leave.end_date}).',
        category='warning', link='/hr/leaves'
    )
    db.session.add(hr_notif)
    db.session.commit()
    flash('Leave cancelled successfully.', 'warning')
    return redirect(url_for('employee.my_leaves'))

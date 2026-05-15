"""Employee leave management routes."""

from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, Leave, Notification
from app.employee.forms import LeaveRequestForm
from app.employee import services
from app.utils.audit import log_audit


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
    balances = services.get_my_leave_balances(emp.id)

    # Get cycle info for display
    from app.hr.services import get_leave_cycle_dates, get_leave_policies_for_employee
    from app.models import CompanySettings
    cycle_start, cycle_end = get_leave_cycle_dates()
    settings = CompanySettings.get_settings()
    type_labels = {'calendar': 'Calendar Year', 'financial': 'Financial Year', 'custom': 'Custom Cycle'}
    cycle_info = {
        'type_label': type_labels.get(settings.leave_cycle_type, 'Financial Year'),
        'start': cycle_start.strftime('%d %b %Y'),
        'end': cycle_end.strftime('%d %b %Y'),
    }

    # Get policies for info table
    policies = get_leave_policies_for_employee(emp.id)

    return render_template('employee/leave_balance.html', balances=balances, employee=emp,
                           cycle_info=cycle_info, policies=policies)


@bp.route('/leaves/request', methods=['GET', 'POST'])
@module_required('employee')
def request_leave():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    form = LeaveRequestForm()
    balances = services.get_my_leave_balances(emp.id)
    form.leave_type.choices = [(b.leave_type, f'{b.leave_type} (Available: {b.remaining})') for b in balances]

    if form.validate_on_submit():
        if form.end_date.data < form.start_date.data:
            flash('End date must be after start date.', 'danger')
            return render_template('employee/leave_request.html', form=form, employee=emp)

        success, msg = services.submit_leave_request(
            employee=emp,
            leave_type=form.leave_type.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            reason=form.reason.data or '',
            is_urgent=getattr(form, 'is_urgent', False) and form.is_urgent.data,
            is_half_day=getattr(form, 'is_half_day', False) and form.is_half_day.data,
            ip=request.remote_addr or ''
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
        from app.hr.services import get_leave_balance, _get_cycle_label_year
        balance = get_leave_balance(emp.id, leave.leave_type, _get_cycle_label_year(leave.start_date))
        if balance:
            balance.used = max(0, balance.used - leave.total_days)

    leave.status = 'Cancelled'
    leave.cancelled_at = datetime.utcnow()
    leave.cancelled_reason = 'Cancelled by employee'
    log_audit(current_user.id, 'CANCEL', 'Leave', leave.id,
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

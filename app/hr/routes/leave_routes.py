"""HR leave management routes."""

from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, Leave, LeavePolicy, Notification
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

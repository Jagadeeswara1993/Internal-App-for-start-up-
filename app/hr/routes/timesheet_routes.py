"""HR timesheet, shift swap, comp-off, profile update, and analytics routes."""

from collections import defaultdict
from datetime import date, datetime
from datetime import date as date_cls, timedelta
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, User, Department, Timesheet,
                        ShiftSwapRequest, CompOff, ProfileUpdateRequest,
                        Notification, Project, Task)
from app.hr import services


# ===========================================================================
# TIMESHEET MANAGEMENT (HR)
# ===========================================================================
@bp.route('/timesheets')
@module_required('hr')
def timesheets():
    """Organization-wide timesheet view with filters."""
    status_filter = request.args.get('status', '')
    dept_filter = request.args.get('department', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Timesheet.query.join(Employee)
    if status_filter:
        query = query.filter(Timesheet.status == status_filter)
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    if date_from:
        try:
            query = query.filter(Timesheet.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(Timesheet.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    page = request.args.get('page', 1, type=int)
    records = query.order_by(Timesheet.date.desc()).paginate(page=page, per_page=25, error_out=False)
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()

    total_hours = db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).filter(query.whereclause).scalar() if query.whereclause is not None else db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).scalar()
    approved_hours = db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).filter(query.whereclause, Timesheet.status == 'Approved').scalar() if query.whereclause is not None else db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).filter(Timesheet.status == 'Approved').scalar()

    return render_template('hr/timesheets.html', records=records,
                           departments=departments,
                           selected_status=status_filter,
                           selected_dept=dept_filter,
                           date_from=date_from, date_to=date_to,
                           total_hours=round(total_hours, 2),
                           approved_hours=round(approved_hours, 2))


@bp.route('/timesheets/attendance-comparison')
@module_required('hr')
def timesheet_attendance_comparison():
    """Side-by-side: Attendance hours vs. Timesheet hours per employee."""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    employees = Employee.query.order_by(Employee.emp_code).all()
    comparison = []
    for emp in employees:
        att_summary = services.get_attendance_summary(emp.id, year, month)
        att_hours = att_summary.get('total_hours', 0)
        ts_entries = Timesheet.query.filter(
            Timesheet.employee_id == emp.id, Timesheet.status == 'Approved',
            db.extract('year', Timesheet.date) == year,
            db.extract('month', Timesheet.date) == month
        ).all()
        ts_hours = round(sum(e.hours_worked for e in ts_entries), 2)
        overtime_flag = ts_hours > att_hours if att_hours > 0 else False
        comparison.append({
            'employee': emp, 'attendance_hours': round(att_hours, 2),
            'timesheet_hours': ts_hours, 'difference': round(ts_hours - att_hours, 2),
            'overtime_flag': overtime_flag
        })
    return render_template('hr/timesheet_comparison.html',
                           comparison=comparison, year=year, month=month)


# ===========================================================================
# SHIFT SWAP REQUESTS
# ===========================================================================
@bp.route('/shift-swaps')
@module_required('hr')
def shift_swaps():
    status_filter = request.args.get('status', '')
    query = ShiftSwapRequest.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    swaps = query.order_by(ShiftSwapRequest.created_at.desc()).all()
    return render_template('hr/shift_swap_requests.html', swaps=swaps,
                           selected_status=status_filter)


@bp.route('/shift-swaps/<int:swap_id>/approve', methods=['POST'])
@module_required('hr')
def approve_shift_swap(swap_id):
    success, msg = services.approve_shift_swap(swap_id, current_user.id)
    if success:
        services.log_audit(current_user.id, 'APPROVE', 'ShiftSwapRequest', swap_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('hr.shift_swaps'))


@bp.route('/shift-swaps/<int:swap_id>/reject', methods=['POST'])
@module_required('hr')
def reject_shift_swap(swap_id):
    success, msg = services.reject_shift_swap(swap_id, current_user.id)
    if success:
        services.log_audit(current_user.id, 'REJECT', 'ShiftSwapRequest', swap_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('hr.shift_swaps'))


# ===========================================================================
# COMP-OFF MANAGEMENT
# ===========================================================================
@bp.route('/comp-offs')
@module_required('hr')
def comp_offs():
    status_filter = request.args.get('status', '')
    comps = services.get_comp_offs(status=status_filter or None)
    return render_template('hr/comp_offs.html', comp_offs=comps,
                           selected_status=status_filter)


@bp.route('/comp-offs/<int:comp_id>/approve', methods=['POST'])
@module_required('hr')
def approve_comp_off(comp_id):
    success, msg = services.approve_comp_off(comp_id, current_user.id)
    if success:
        services.log_audit(current_user.id, 'APPROVE', 'CompOff', comp_id,
                          msg, request.remote_addr or '')
        db.session.commit()
        flash(msg, 'success')
    else:
        flash(msg, 'danger')
    return redirect(url_for('hr.comp_offs'))


# ===========================================================================
# PROFILE UPDATE APPROVALS (HR-Side)
# ===========================================================================
@bp.route('/profile-update-requests')
@module_required('hr')
def profile_update_requests():
    """View all profile update requests from employees."""
    status_filter = request.args.get('status', '')
    query = ProfileUpdateRequest.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    requests_list = query.order_by(ProfileUpdateRequest.employee_id,
                                    ProfileUpdateRequest.created_at.desc()).all()
    grouped_requests = {}
    for r in requests_list:
        if r.employee not in grouped_requests:
            grouped_requests[r.employee] = []
        grouped_requests[r.employee].append(r)
    return render_template('hr/profile_update_requests.html',
                           grouped_requests=grouped_requests,
                           selected_status=status_filter)


@bp.route('/profile-update-requests/<int:req_id>/approve', methods=['POST'])
@module_required('hr')
def approve_profile_update(req_id):
    """Approve a profile update request and apply changes."""
    req_obj = ProfileUpdateRequest.query.get_or_404(req_id)
    if req_obj.status != 'Pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('hr.profile_update_requests'))

    emp = Employee.query.get(req_obj.employee_id)
    if not emp:
        flash('Employee not found.', 'danger')
        return redirect(url_for('hr.profile_update_requests'))

    field_name = req_obj.field_name
    new_value = req_obj.new_value
    if field_name == 'phone': emp.user.phone = new_value
    elif field_name == 'bank_account': emp.bank_account = new_value
    elif field_name == 'pan_number': emp.pan_number = new_value.upper()
    elif field_name == 'aadhar_number': emp.aadhar_number = new_value
    elif field_name == 'location': emp.location = new_value
    elif field_name == 'date_of_birth':
        try:
            emp.date_of_birth = datetime.strptime(new_value, '%Y-%m-%d').date()
        except ValueError:
            pass

    req_obj.status = 'Approved'
    req_obj.reviewed_by = current_user.id
    req_obj.reviewed_at = datetime.utcnow()
    services.log_audit(current_user.id, 'APPROVE', 'ProfileUpdateRequest', req_obj.id,
                      f'Approved {field_name} update for emp#{emp.id}', request.remote_addr or '')
    notif = Notification(user_id=emp.user_id, title='Profile Update Approved',
                        message=f'Your request to update {field_name} has been approved.',
                        category='success', link='/employee/profile')
    db.session.add(notif)
    db.session.commit()
    flash(f'Profile update for {emp.user.full_name} ({field_name}) approved and applied.', 'success')
    return redirect(url_for('hr.profile_update_requests'))


@bp.route('/profile-update-requests/<int:req_id>/reject', methods=['POST'])
@module_required('hr')
def reject_profile_update(req_id):
    """Reject a profile update request."""
    req_obj = ProfileUpdateRequest.query.get_or_404(req_id)
    if req_obj.status != 'Pending':
        flash('This request has already been processed.', 'warning')
        return redirect(url_for('hr.profile_update_requests'))
    rejection_reason = request.form.get('reason', '').strip()
    req_obj.status = 'Rejected'
    req_obj.reviewed_by = current_user.id
    req_obj.reviewed_at = datetime.utcnow()
    req_obj.rejection_reason = rejection_reason
    services.log_audit(current_user.id, 'REJECT', 'ProfileUpdateRequest', req_obj.id,
                      f'Rejected {req_obj.field_name} update', request.remote_addr or '')
    emp = Employee.query.get(req_obj.employee_id)
    if emp:
        notif = Notification(user_id=emp.user_id, title='Profile Update Rejected',
                            message=f'Your request to update {req_obj.field_name} was rejected. {rejection_reason}',
                            category='warning', link='/employee/profile')
        db.session.add(notif)
    db.session.commit()
    flash('Profile update request rejected.', 'warning')
    return redirect(url_for('hr.profile_update_requests'))


@bp.route('/profile-update-requests/<int:emp_id>/approve-all', methods=['POST'])
@module_required('hr')
def approve_all_profile_updates(emp_id):
    """Approve all pending profile update requests for an employee."""
    emp = Employee.query.get_or_404(emp_id)
    pending_requests = ProfileUpdateRequest.query.filter_by(employee_id=emp_id, status='Pending').all()
    if not pending_requests:
        flash('No pending requests found for this employee.', 'warning')
        return redirect(url_for('hr.profile_update_requests'))
    for req_obj in pending_requests:
        field_name = req_obj.field_name
        new_value = req_obj.new_value
        if field_name == 'full_name': emp.user.full_name = new_value
        elif field_name == 'phone': emp.user.phone = new_value
        elif field_name == 'bank_account': emp.bank_account = new_value
        elif field_name == 'pan_number': emp.pan_number = new_value.upper()
        elif field_name == 'aadhar_number': emp.aadhar_number = new_value
        elif field_name == 'location': emp.location = new_value
        elif field_name == 'date_of_birth':
            try:
                emp.date_of_birth = datetime.strptime(new_value, '%Y-%m-%d').date()
            except ValueError:
                pass
        req_obj.status = 'Approved'
        req_obj.reviewed_by = current_user.id
        req_obj.reviewed_at = datetime.utcnow()
        services.log_audit(current_user.id, 'APPROVE', 'ProfileUpdateRequest', req_obj.id,
                          f'Approved {field_name} update for emp#{emp.id}', request.remote_addr or '')
    notif = Notification(user_id=emp.user_id, title='Profile Updates Approved',
                        message='Your profile update requests have been approved and applied.',
                        category='success', link='/employee/profile')
    db.session.add(notif)
    db.session.commit()
    flash(f'All profile updates for {emp.user.full_name} approved and applied.', 'success')
    return redirect(url_for('hr.profile_update_requests'))


@bp.route('/profile-update-requests/<int:emp_id>/reject-all', methods=['POST'])
@module_required('hr')
def reject_all_profile_updates(emp_id):
    """Reject all pending profile update requests for an employee."""
    emp = Employee.query.get_or_404(emp_id)
    pending_requests = ProfileUpdateRequest.query.filter_by(employee_id=emp_id, status='Pending').all()
    if not pending_requests:
        flash('No pending requests found for this employee.', 'warning')
        return redirect(url_for('hr.profile_update_requests'))
    rejection_reason = request.form.get('reason', '').strip()
    for req_obj in pending_requests:
        req_obj.status = 'Rejected'
        req_obj.reviewed_by = current_user.id
        req_obj.reviewed_at = datetime.utcnow()
        req_obj.rejection_reason = rejection_reason
        services.log_audit(current_user.id, 'REJECT', 'ProfileUpdateRequest', req_obj.id,
                          f'Rejected {req_obj.field_name} update', request.remote_addr or '')
    notif = Notification(user_id=emp.user_id, title='Profile Updates Rejected',
                        message=f'Your profile update requests were rejected. {rejection_reason}',
                        category='warning', link='/employee/profile')
    db.session.add(notif)
    db.session.commit()
    flash(f'All profile updates for {emp.user.full_name} rejected.', 'warning')
    return redirect(url_for('hr.profile_update_requests'))


# ===========================================================================
# ORGANIZATION ANALYTICS (HR)
# ===========================================================================
@bp.route('/analytics')
@module_required('hr')
def analytics():
    """HR analytics — people-centric workforce insights."""
    from app.utils.analytics import get_hr_analytics_data
    data = get_hr_analytics_data()
    return render_template('hr/analytics.html', **data)

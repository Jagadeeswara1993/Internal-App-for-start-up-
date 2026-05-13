"""Admin configuration routes — departments, designations, leave policies,
attendance rules, shifts, holidays, audit logs."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.admin import bp
from app.decorators import admin_required
from app.extensions import db
from app.models import (Employee, Department, Designation, LeavePolicy,
                        AttendanceRule, Shift, AuditLog, Holiday)
from app.admin.config_forms import (DepartmentForm, DesignationForm,
                                     LeavePolicyForm, AttendanceRuleForm, ShiftForm)


from app.utils.audit import log_audit


# ===========================================================================
# DEPARTMENT MANAGEMENT
# ===========================================================================
@bp.route('/departments')
@admin_required
def departments():
    all_depts = Department.query.order_by(Department.name).all()
    return render_template('admin/departments.html', departments=all_depts)


@bp.route('/departments/add', methods=['GET', 'POST'])
@admin_required
def add_department():
    form = DepartmentForm()
    if form.validate_on_submit():
        if Department.query.filter_by(code=form.code.data).first():
            flash('Department code already exists.', 'danger')
            return render_template('admin/department_form.html', form=form, title='Add Department')
        dept = Department(
            name=form.name.data, code=form.code.data.upper(),
            description=form.description.data or '', is_active=form.is_active.data
        )
        db.session.add(dept)
        log_audit(current_user.id, 'CREATE', 'Department', None, f'Created dept {dept.code}')
        db.session.commit()
        flash(f'Department "{dept.name}" created.', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title='Add Department')


@bp.route('/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)
    form = DepartmentForm(obj=dept)
    if form.validate_on_submit():
        existing = Department.query.filter(Department.code == form.code.data, Department.id != dept.id).first()
        if existing:
            flash('Department code already taken.', 'danger')
            return render_template('admin/department_form.html', form=form, title='Edit Department', dept=dept)
        dept.name = form.name.data
        dept.code = form.code.data.upper()
        dept.description = form.description.data or ''
        dept.is_active = form.is_active.data
        log_audit(current_user.id, 'UPDATE', 'Department', dept.id, f'Updated dept {dept.code}')
        db.session.commit()
        flash(f'Department "{dept.name}" updated.', 'success')
        return redirect(url_for('admin.departments'))
    return render_template('admin/department_form.html', form=form, title='Edit Department', dept=dept)


@bp.route('/departments/<int:dept_id>/delete', methods=['POST'])
@admin_required
def delete_department(dept_id):
    """Soft-delete a department (set is_active=False)."""
    dept = Department.query.get_or_404(dept_id)
    active_emps = Employee.query.filter_by(department_id=dept.id, is_active=True).count()
    if active_emps > 0:
        flash(f'Cannot deactivate "{dept.name}" — {active_emps} active employee(s) assigned.', 'danger')
        return redirect(url_for('admin.departments'))
    dept.is_active = False
    log_audit(current_user.id, 'SOFT_DELETE', 'Department', dept.id, f'Deactivated dept {dept.code}')
    db.session.commit()
    flash(f'Department "{dept.name}" deactivated.', 'warning')
    return redirect(url_for('admin.departments'))


@bp.route('/departments/<int:dept_id>/restore', methods=['POST'])
@admin_required
def restore_department(dept_id):
    """Restore a soft-deleted department."""
    dept = Department.query.get_or_404(dept_id)
    dept.is_active = True
    log_audit(current_user.id, 'RESTORE', 'Department', dept.id, f'Restored dept {dept.code}')
    db.session.commit()
    flash(f'Department "{dept.name}" restored.', 'success')
    return redirect(url_for('admin.departments'))


# ===========================================================================
# DESIGNATION MANAGEMENT
# ===========================================================================
@bp.route('/designations')
@admin_required
def designations():
    all_desig = Designation.query.order_by(Designation.department_id, Designation.level).all()
    return render_template('admin/designations.html', designations=all_desig)


@bp.route('/designations/add', methods=['GET', 'POST'])
@admin_required
def add_designation():
    form = DesignationForm()
    form.department_id.choices = [(d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name)]
    if form.validate_on_submit():
        desig = Designation(
            title=form.title.data, department_id=form.department_id.data,
            level=form.level.data, is_active=form.is_active.data
        )
        db.session.add(desig)
        log_audit(current_user.id, 'CREATE', 'Designation', None, f'Created designation {desig.title}')
        db.session.commit()
        flash(f'Designation "{desig.title}" created.', 'success')
        return redirect(url_for('admin.designations'))
    return render_template('admin/designation_form.html', form=form, title='Add Designation')


@bp.route('/designations/<int:desig_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_designation(desig_id):
    desig = Designation.query.get_or_404(desig_id)
    form = DesignationForm(obj=desig)
    form.department_id.choices = [(d.id, d.name) for d in Department.query.filter_by(is_active=True).order_by(Department.name)]
    if form.validate_on_submit():
        desig.title = form.title.data
        desig.department_id = form.department_id.data
        desig.level = form.level.data
        desig.is_active = form.is_active.data
        log_audit(current_user.id, 'UPDATE', 'Designation', desig.id, f'Updated designation {desig.title}')
        db.session.commit()
        flash(f'Designation "{desig.title}" updated.', 'success')
        return redirect(url_for('admin.designations'))
    return render_template('admin/designation_form.html', form=form, title='Edit Designation', desig=desig)


@bp.route('/designations/<int:desig_id>/delete', methods=['POST'])
@admin_required
def delete_designation(desig_id):
    """Soft-delete a designation (set is_active=False)."""
    desig = Designation.query.get_or_404(desig_id)
    active_emps = Employee.query.filter_by(designation_id=desig.id, is_active=True).count()
    if active_emps > 0:
        flash(f'Cannot deactivate "{desig.title}" — {active_emps} active employee(s) assigned.', 'danger')
        return redirect(url_for('admin.designations'))
    desig.is_active = False
    log_audit(current_user.id, 'SOFT_DELETE', 'Designation', desig.id, f'Deactivated designation {desig.title}')
    db.session.commit()
    flash(f'Designation "{desig.title}" deactivated.', 'warning')
    return redirect(url_for('admin.designations'))


@bp.route('/designations/<int:desig_id>/restore', methods=['POST'])
@admin_required
def restore_designation(desig_id):
    """Restore a soft-deleted designation."""
    desig = Designation.query.get_or_404(desig_id)
    desig.is_active = True
    log_audit(current_user.id, 'RESTORE', 'Designation', desig.id, f'Restored designation {desig.title}')
    db.session.commit()
    flash(f'Designation "{desig.title}" restored.', 'success')
    return redirect(url_for('admin.designations'))


# ===========================================================================
# LEAVE POLICY MANAGEMENT
# ===========================================================================
@bp.route('/leave-policies')
@admin_required
def leave_policies():
    policies = LeavePolicy.query.order_by(LeavePolicy.leave_type, LeavePolicy.designation_id).all()
    return render_template('admin/leave_policies.html', policies=policies)


@bp.route('/leave-policies/add', methods=['GET', 'POST'])
@admin_required
def add_leave_policy():
    form = LeavePolicyForm()
    form.designation_id.choices = [(0, '— Global (All Roles) —')] + [
        (d.id, f'{d.title} ({d.department.name})') for d in
        Designation.query.filter_by(is_active=True).order_by(Designation.title)
    ]
    if form.validate_on_submit():
        desig_id = form.designation_id.data if form.designation_id.data != 0 else None
        existing = LeavePolicy.query.filter_by(
            leave_type=form.leave_type.data, designation_id=desig_id
        ).first()
        if existing:
            flash(f'Leave policy "{form.leave_type.data}" already exists for this designation.', 'danger')
            return render_template('admin/leave_policy_form.html', form=form, title='Add Leave Policy')
        policy = LeavePolicy(
            leave_type=form.leave_type.data, designation_id=desig_id,
            total_days=form.total_days.data, carry_forward=form.carry_forward.data,
            max_carry_days=form.max_carry_days.data or 0,
            monthly_accrual=form.monthly_accrual.data,
            encashment_allowed=form.encashment_allowed.data,
            max_per_request=form.max_per_request.data if form.max_per_request.data else None,
            blackout_dates=form.blackout_dates.data or '',
            description=form.description.data or '', is_active=form.is_active.data
        )
        db.session.add(policy)
        log_audit(current_user.id, 'CREATE', 'LeavePolicy', None, f'Created policy {policy.leave_type}')
        db.session.commit()
        flash(f'Leave policy "{policy.leave_type}" created.', 'success')
        return redirect(url_for('admin.leave_policies'))
    return render_template('admin/leave_policy_form.html', form=form, title='Add Leave Policy')


@bp.route('/leave-policies/<int:policy_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_leave_policy(policy_id):
    policy = LeavePolicy.query.get_or_404(policy_id)
    form = LeavePolicyForm(obj=policy)
    form.designation_id.choices = [(0, '— Global (All Roles) —')] + [
        (d.id, f'{d.title} ({d.department.name})') for d in
        Designation.query.filter_by(is_active=True).order_by(Designation.title)
    ]
    if request.method == 'GET':
        form.designation_id.data = policy.designation_id or 0
    if form.validate_on_submit():
        desig_id = form.designation_id.data if form.designation_id.data != 0 else None
        policy.leave_type = form.leave_type.data
        policy.designation_id = desig_id
        policy.total_days = form.total_days.data
        policy.carry_forward = form.carry_forward.data
        policy.max_carry_days = form.max_carry_days.data or 0
        policy.monthly_accrual = form.monthly_accrual.data
        policy.encashment_allowed = form.encashment_allowed.data
        policy.max_per_request = form.max_per_request.data if form.max_per_request.data else None
        policy.blackout_dates = form.blackout_dates.data or ''
        policy.description = form.description.data or ''
        policy.is_active = form.is_active.data
        log_audit(current_user.id, 'UPDATE', 'LeavePolicy', policy.id, f'Updated policy {policy.leave_type}')
        db.session.commit()
        flash(f'Leave policy "{policy.leave_type}" updated.', 'success')
        return redirect(url_for('admin.leave_policies'))
    return render_template('admin/leave_policy_form.html', form=form, title='Edit Leave Policy', policy=policy)


# ===========================================================================
# ATTENDANCE RULES
# ===========================================================================
@bp.route('/attendance-rules', methods=['GET', 'POST'])
@admin_required
def attendance_rules():
    rule = AttendanceRule.query.first()
    if not rule:
        rule = AttendanceRule()
        db.session.add(rule)
        db.session.commit()
    form = AttendanceRuleForm(obj=rule)
    if form.validate_on_submit():
        rule.work_start = form.work_start.data
        rule.work_end = form.work_end.data
        rule.late_threshold_mins = form.late_threshold_mins.data
        rule.half_day_hours = form.half_day_hours.data
        rule.full_day_hours = form.full_day_hours.data
        log_audit(current_user.id, 'UPDATE', 'AttendanceRule', rule.id, 'Updated attendance rules')
        db.session.commit()
        flash('Attendance rules updated.', 'success')
        return redirect(url_for('admin.attendance_rules'))
    return render_template('admin/attendance_rules.html', form=form, rule=rule)


# ===========================================================================
# SHIFT MANAGEMENT
# ===========================================================================
@bp.route('/shifts')
@admin_required
def shifts():
    all_shifts = Shift.query.order_by(Shift.shift_name).all()
    return render_template('admin/shifts.html', shifts=all_shifts)


@bp.route('/shifts/add', methods=['GET', 'POST'])
@admin_required
def add_shift():
    form = ShiftForm()
    if form.validate_on_submit():
        if Shift.query.filter_by(shift_name=form.shift_name.data).first():
            flash('Shift name already exists.', 'danger')
            return render_template('admin/shift_form.html', form=form, title='Add Shift')
        shift = Shift(
            shift_name=form.shift_name.data, start_time=form.start_time.data,
            end_time=form.end_time.data, grace_period_mins=form.grace_period_mins.data,
            min_working_hours=form.min_working_hours.data,
            late_mark_after_mins=form.late_mark_after_mins.data,
            overtime_eligible=form.overtime_eligible.data, is_active=form.is_active.data
        )
        db.session.add(shift)
        log_audit(current_user.id, 'CREATE', 'Shift', None, f'Created shift {shift.shift_name}')
        db.session.commit()
        flash(f'Shift "{shift.shift_name}" created.', 'success')
        return redirect(url_for('admin.shifts'))
    return render_template('admin/shift_form.html', form=form, title='Add Shift')


@bp.route('/shifts/<int:shift_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_shift(shift_id):
    shift = Shift.query.get_or_404(shift_id)
    form = ShiftForm(obj=shift)
    if form.validate_on_submit():
        existing = Shift.query.filter(Shift.shift_name == form.shift_name.data, Shift.id != shift.id).first()
        if existing:
            flash('Shift name already taken.', 'danger')
            return render_template('admin/shift_form.html', form=form, title='Edit Shift', shift=shift)
        shift.shift_name = form.shift_name.data
        shift.start_time = form.start_time.data
        shift.end_time = form.end_time.data
        shift.grace_period_mins = form.grace_period_mins.data
        shift.min_working_hours = form.min_working_hours.data
        shift.late_mark_after_mins = form.late_mark_after_mins.data
        shift.overtime_eligible = form.overtime_eligible.data
        shift.is_active = form.is_active.data
        log_audit(current_user.id, 'UPDATE', 'Shift', shift.id, f'Updated shift {shift.shift_name}')
        db.session.commit()
        flash(f'Shift "{shift.shift_name}" updated.', 'success')
        return redirect(url_for('admin.shifts'))
    return render_template('admin/shift_form.html', form=form, title='Edit Shift', shift=shift)


# ===========================================================================
# AUDIT LOG VIEWER
# ===========================================================================
@bp.route('/audit-logs')
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('admin/audit_logs.html', logs=logs)


# ===========================================================================
# HOLIDAY CALENDAR MANAGEMENT
# ===========================================================================
@bp.route('/holidays')
@admin_required
def holidays():
    """View company holiday calendar."""
    year = request.args.get('year', __import__('datetime').date.today().year, type=int)
    query = Holiday.query.filter(
        db.extract('year', Holiday.date) == year
    ).order_by(Holiday.date)
    all_holidays = query.all()
    return render_template('admin/holidays.html', holidays=all_holidays, year=year)


@bp.route('/holidays/add', methods=['GET', 'POST'])
@admin_required
def add_holiday():
    """Add a company holiday."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        date_str = request.form.get('date', '').strip()
        holiday_type = request.form.get('holiday_type', 'Public')
        description = request.form.get('description', '').strip()
        if not name or not date_str:
            flash('Holiday name and date are required.', 'danger')
            return render_template('admin/holiday_form.html', title='Add Holiday')
        from datetime import datetime as dt
        try:
            h_date = dt.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('admin/holiday_form.html', title='Add Holiday')
        existing = Holiday.query.filter_by(name=name, date=h_date).first()
        if existing:
            flash('A holiday with this name and date already exists.', 'danger')
            return render_template('admin/holiday_form.html', title='Add Holiday')
        holiday = Holiday(
            name=name, date=h_date, holiday_type=holiday_type,
            description=description, created_by=current_user.id
        )
        db.session.add(holiday)
        log_audit(current_user.id, 'CREATE', 'Holiday', None, f'Added holiday: {name} on {h_date}')
        db.session.commit()
        flash(f'Holiday "{name}" added.', 'success')
        return redirect(url_for('admin.holidays'))
    return render_template('admin/holiday_form.html', title='Add Holiday')


@bp.route('/holidays/<int:holiday_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_holiday(holiday_id):
    """Edit a company holiday."""
    holiday = Holiday.query.get_or_404(holiday_id)
    if request.method == 'POST':
        holiday.name = request.form.get('name', '').strip()
        date_str = request.form.get('date', '').strip()
        holiday.holiday_type = request.form.get('holiday_type', 'Public')
        holiday.description = request.form.get('description', '').strip()
        from datetime import datetime as dt
        try:
            holiday.date = dt.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format.', 'danger')
            return render_template('admin/holiday_form.html', title='Edit Holiday', holiday=holiday)
        log_audit(current_user.id, 'UPDATE', 'Holiday', holiday.id, f'Updated holiday: {holiday.name}')
        db.session.commit()
        flash(f'Holiday "{holiday.name}" updated.', 'success')
        return redirect(url_for('admin.holidays'))
    return render_template('admin/holiday_form.html', title='Edit Holiday', holiday=holiday)


@bp.route('/holidays/<int:holiday_id>/delete', methods=['POST'])
@admin_required
def delete_holiday(holiday_id):
    """Delete a company holiday."""
    holiday = Holiday.query.get_or_404(holiday_id)
    log_audit(current_user.id, 'DELETE', 'Holiday', holiday.id,
              f'Deleted holiday: {holiday.name} ({holiday.date})')
    db.session.delete(holiday)
    db.session.commit()
    flash(f'Holiday "{holiday.name}" deleted.', 'warning')
    return redirect(url_for('admin.holidays'))

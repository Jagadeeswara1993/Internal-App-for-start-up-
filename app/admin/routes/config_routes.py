"""Admin configuration routes — departments, designations, leave policies,
attendance rules, shifts, holidays, audit logs."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.admin import bp
from app.decorators import admin_required
from app.extensions import db
from app.models import (Employee, Department, Designation, LeavePolicy,
                        AttendanceRule, Shift, AuditLog, Holiday, CompanySettings)
from app.admin.config_forms import (DepartmentForm, DesignationForm,
                                     LeavePolicyForm, AttendanceRuleForm, ShiftForm,
                                     LeaveCycleForm)


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
            total_days=form.total_days.data,
            is_calendar_days=form.is_calendar_days.data,
            is_prorated=form.is_prorated.data,
            carry_forward=form.carry_forward.data,
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
        policy.is_calendar_days = form.is_calendar_days.data
        policy.is_prorated = form.is_prorated.data
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
        db.extract('year', Holiday.holiday_date) == year
    ).order_by(Holiday.holiday_date)
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
        existing = Holiday.query.filter_by(holiday_name=name, holiday_date=h_date).first()
        if existing:
            flash('A holiday with this name and date already exists.', 'danger')
            return render_template('admin/holiday_form.html', title='Add Holiday')
        holiday = Holiday(
            holiday_name=name, holiday_date=h_date, holiday_type=holiday_type,
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
        holiday.holiday_name = request.form.get('name', '').strip()
        date_str = request.form.get('date', '').strip()
        holiday.holiday_type = request.form.get('holiday_type', 'Public')
        holiday.description = request.form.get('description', '').strip()
        from datetime import datetime as dt
        try:
            holiday.holiday_date = dt.strptime(date_str, '%Y-%m-%d').date()
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


@bp.route('/holidays/upload', methods=['POST'])
@admin_required
def upload_holidays():
    """Bulk upload holidays via Excel or CSV."""
    import pandas as pd
    from datetime import datetime
    import os
    from werkzeug.utils import secure_filename

    if 'file' not in request.files:
        flash('No file uploaded.', 'danger')
        return redirect(url_for('admin.holidays'))
        
    file = request.files['file']
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('admin.holidays'))
        
    if not (file.filename.endswith('.csv') or file.filename.endswith('.xlsx')):
        flash('Invalid file format. Please upload a .csv or .xlsx file.', 'danger')
        return redirect(url_for('admin.holidays'))
        
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
            
        # Standardize column names
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        required_cols = ['holiday_name', 'holiday_date']
        for col in required_cols:
            if col not in df.columns:
                flash(f'Missing required column: {col}', 'danger')
                return redirect(url_for('admin.holidays'))
            
        added_count = 0
        skipped_count = 0
        
        for index, row in df.iterrows():
            name = str(row.get('holiday_name', '')).strip()
            date_val = row.get('holiday_date')
            
            if not name or name == 'nan' or pd.isna(date_val):
                continue
                
            # Parse date
            try:
                if isinstance(date_val, str):
                    h_date = datetime.strptime(str(date_val).strip()[:10], '%Y-%m-%d').date()
                else:
                    h_date = date_val.date() if hasattr(date_val, 'date') else date_val
            except Exception:
                skipped_count += 1
                continue
                
            h_day = str(row.get('holiday_day', '')).strip()
            if h_day == 'nan':
                h_day = h_date.strftime('%A')
                
            h_type = str(row.get('holiday_type', 'Public')).strip()
            if h_type not in ['Public', 'Restricted', 'Optional']:
                h_type = 'Public'
                
            desc = str(row.get('description', '')).strip()
            if desc == 'nan': 
                desc = ''
            
            # Prevent duplicate holiday dates
            existing = Holiday.query.filter_by(holiday_date=h_date).first()
            if existing:
                # Update existing if duplicate found
                existing.holiday_name = name
                existing.holiday_day = h_day
                existing.holiday_type = h_type
                existing.description = desc
                added_count += 1
                continue
                
            holiday = Holiday(
                holiday_name=name,
                holiday_date=h_date,
                holiday_day=h_day,
                holiday_type=h_type,
                description=desc,
                created_by=current_user.id
            )
            db.session.add(holiday)
            added_count += 1
            
        if added_count > 0:
            log_audit(current_user.id, 'BULK_UPLOAD', 'Holiday', None, f'Bulk uploaded/updated {added_count} holidays')
            db.session.commit()
            flash(f'Upload complete: {added_count} holidays processed successfully. Skipped rows: {skipped_count}', 'success')
        else:
            flash(f'No new valid holidays found to upload. Skipped rows: {skipped_count}', 'info')

    except Exception as e:
        db.session.rollback()
        flash(f'Error processing file: {str(e)}', 'danger')
        
    return redirect(url_for('admin.holidays'))


@bp.route('/holidays/template/download')
@admin_required
def download_holiday_template():
    """Download CSV template for bulk holiday upload."""
    import csv
    import io
    from flask import Response
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['holiday_name', 'holiday_date', 'holiday_day', 'holiday_type', 'description'])
    writer.writerow(['New Year', '2026-01-01', 'Thursday', 'Public', 'New Year Day'])
    writer.writerow(['Diwali', '2026-11-08', 'Sunday', 'Public', 'Festival of Lights'])
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=holiday_template.csv"}
    )

# ===========================================================================
# LEAVE CYCLE SETTINGS
# ===========================================================================
@bp.route('/leave-cycle-settings', methods=['GET', 'POST'])
@admin_required
def leave_cycle_settings():
    """Configure the company leave cycle type and proration rules."""
    settings = CompanySettings.get_settings()
    form = LeaveCycleForm(obj=settings)
    if form.validate_on_submit():
        settings.leave_cycle_type = form.leave_cycle_type.data
        settings.custom_cycle_start_month = form.custom_cycle_start_month.data
        settings.custom_cycle_start_day = form.custom_cycle_start_day.data
        settings.proration_rounding = form.proration_rounding.data
        log_audit(current_user.id, 'UPDATE', 'CompanySettings', settings.id,
                  f'Updated leave cycle to {settings.leave_cycle_type}')
        db.session.commit()
        flash('Leave cycle settings updated.', 'success')
        return redirect(url_for('admin.leave_cycle_settings'))

    # Compute current cycle for display
    from app.hr.services import get_leave_cycle_dates
    cycle_start, cycle_end = get_leave_cycle_dates()
    return render_template('admin/leave_cycle_settings.html', form=form,
                           settings=settings, cycle_start=cycle_start,
                           cycle_end=cycle_end)


@bp.route('/leave-cycle/rollover', methods=['POST'])
@admin_required
def trigger_leave_rollover():
    """Manually trigger yearly leave rollover for all employees."""
    from app.hr.services import run_yearly_leave_rollover
    processed, skipped = run_yearly_leave_rollover()
    log_audit(current_user.id, 'ROLLOVER', 'LeaveBalance', None,
              f'Yearly rollover: {processed} employees processed, {skipped} already done')
    db.session.commit()
    flash(f'Leave rollover complete: {processed} employees processed, {skipped} already up-to-date.', 'success')
    return redirect(url_for('admin.leave_cycle_settings'))

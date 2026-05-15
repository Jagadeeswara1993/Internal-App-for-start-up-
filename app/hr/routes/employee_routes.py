"""HR employee management routes — list, edit, detail, onboarding, API."""

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, User, Attendance, Leave, Department
from app.hr.forms import EmployeeForm
from app.hr import services


@bp.route('/employees')
@module_required('hr')
def employees():
    dept_id = request.args.get('department', type=int)
    search = request.args.get('search', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = Employee.query
    if dept_id:
        query = query.filter_by(department_id=dept_id)
    if search:
        query = query.join(User).filter(
            db.or_(
                User.full_name.ilike(f'%{search}%'),
                Employee.emp_code.ilike(f'%{search}%')
            )
        )

    is_complete_condition = db.and_(
        Employee.department_id.isnot(None),
        Employee.designation_id.isnot(None),
        Employee.salary > 0,
        db.func.coalesce(Employee.bank_account, '') != '',
        db.func.coalesce(Employee.pan_number, '') != '',
        db.func.coalesce(User.phone, '') != ''
    )

    if status_filter == 'unassigned':
        query = query.filter(db.not_(is_complete_condition))
    elif status_filter == 'assigned':
        query = query.filter(is_complete_condition)

    page = request.args.get('page', 1, type=int)
    all_employees = query.order_by(Employee.emp_code).paginate(page=page, per_page=25, error_out=False)

    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    unassigned_count = services.get_unassigned_count()
    return render_template('hr/employees.html', employees=all_employees,
                           departments=departments, selected_dept=dept_id,
                           search=search, status_filter=status_filter,
                           unassigned_count=unassigned_count,
                           is_profile_complete=services.is_employee_profile_complete)


@bp.route('/employees/<int:emp_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def edit_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    form = EmployeeForm(obj=emp)
    form.department_id.choices = [(0, '— Select Department —')] + services.get_departments_for_dropdown()
    form.designation_id.choices = [(0, '— Select Designation —')] + services.get_designations_for_dropdown()
    form.shift_id.choices = [(0, '— General Shift —')] + services.get_shifts_for_dropdown()
    form.reporting_manager_id.choices = [(0, '— No Manager (Direct to HR) —')] + services.get_managers_for_dropdown(exclude_emp_id=emp.id)

    if request.method == 'GET':
        form.shift_id.data = emp.shift_id or 0
        form.reporting_manager_id.data = emp.reporting_manager_id or 0

    if form.validate_on_submit():
        emp.department_id = form.department_id.data if form.department_id.data != 0 else None
        emp.designation_id = form.designation_id.data if form.designation_id.data != 0 else None
        emp.shift_id = form.shift_id.data if form.shift_id.data != 0 else None
        emp.reporting_manager_id = form.reporting_manager_id.data if form.reporting_manager_id.data != 0 else None
        emp.date_of_birth = form.date_of_birth.data
        emp.date_of_joining = form.date_of_joining.data
        emp.salary = form.salary.data or 0
        emp.bank_account = form.bank_account.data or ''
        emp.pan_number = form.pan_number.data or ''
        emp.aadhar_number = form.aadhar_number.data or ''
        emp.location = form.location.data or ''

        # Re-check leave allocation when designation changes
        services.reallocate_leave_on_designation_change(emp.id)
        services.log_audit(current_user.id, 'UPDATE', 'Employee', emp.id,
                          f'Updated employee {emp.emp_code}', request.remote_addr or '')
        db.session.commit()
        flash(f'Employee {emp.emp_code} updated.', 'success')
        return redirect(url_for('hr.employees'))
    return render_template('hr/employee_form.html', form=form, title='Edit Employee', employee=emp)


@bp.route('/employees/<int:emp_id>')
@module_required('hr')
def employee_detail(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    leave_balances = services.get_all_leave_balances(emp.id)
    recent_attendance = Attendance.query.filter_by(employee_id=emp.id)\
        .order_by(Attendance.date.desc()).limit(10).all()
    recent_leaves = Leave.query.filter_by(employee_id=emp.id)\
        .order_by(Leave.created_at.desc()).limit(5).all()
    return render_template('hr/employee_detail.html', employee=emp,
                           leave_balances=leave_balances,
                           recent_attendance=recent_attendance,
                           recent_leaves=recent_leaves)


@bp.route('/api/designations/<int:dept_id>')
@module_required('hr')
def api_designations(dept_id):
    desigs = services.get_designations_for_department(dept_id)
    return jsonify(desigs)


# ===========================================================================
# UNASSIGNED EMPLOYEES / ONBOARDING
# ===========================================================================
@bp.route('/employees/unassigned')
@module_required('hr')
def unassigned_employees():
    """List employees with incomplete profiles awaiting HR onboarding."""
    unassigned = services.get_unassigned_employees()
    emp_info = []
    for emp in unassigned:
        emp_info.append({
            'employee': emp,
            'missing': services.get_missing_fields(emp)
        })
    return render_template('hr/unassigned_employees.html',
                           emp_info=emp_info,
                           unassigned_count=len(unassigned))


@bp.route('/employees/<int:emp_id>/complete-profile', methods=['GET', 'POST'])
@module_required('hr')
def complete_profile(emp_id):
    """HR fills in missing details for an unassigned employee."""
    emp = Employee.query.get_or_404(emp_id)
    form = EmployeeForm(obj=emp)
    form.department_id.choices = [(0, '— Select Department —')] + services.get_departments_for_dropdown()
    form.designation_id.choices = [(0, '— Select Designation —')] + services.get_designations_for_dropdown()
    form.shift_id.choices = [(0, '— General Shift —')] + services.get_shifts_for_dropdown()
    form.reporting_manager_id.choices = [(0, '— No Manager (Direct to HR) —')] + services.get_managers_for_dropdown(exclude_emp_id=emp.id)
    missing = services.get_missing_fields(emp)

    if form.validate_on_submit():
        success, msg = services.complete_employee_profile(
            emp,
            department_id=form.department_id.data,
            designation_id=form.designation_id.data,
            salary=form.salary.data,
            bank_account=form.bank_account.data,
            pan_number=form.pan_number.data,
            aadhar_number=form.aadhar_number.data,
            date_of_birth=form.date_of_birth.data,
            location=form.location.data,
            phone=request.form.get('phone', '').strip(),
            country_code=request.form.get('country_code', '+91'),
            date_of_joining=form.date_of_joining.data
        )
        if success:
            emp.reporting_manager_id = form.reporting_manager_id.data if form.reporting_manager_id.data != 0 else None
            services.initialize_leave_balances(emp.id)
            services.log_audit(current_user.id, 'COMPLETE_PROFILE', 'Employee', emp.id,
                              f'Completed profile for {emp.emp_code}', request.remote_addr or '')
            db.session.commit()
            flash(msg, 'success')
            return redirect(url_for('hr.employee_detail', emp_id=emp.id))
        else:
            flash(msg, 'danger')

    return render_template('hr/complete_profile.html', form=form,
                           employee=emp, missing=missing,
                           title='Complete Employee Profile')


@bp.route('/api/employee/<int:emp_id>/profile-status')
@module_required('hr')
def api_profile_status(emp_id):
    """API: Check if an employee's profile is complete."""
    emp = Employee.query.get(emp_id)
    if not emp:
        return jsonify({'error': 'Employee not found'}), 404
    complete = services.is_employee_profile_complete(emp)
    missing = services.get_missing_fields(emp) if not complete else []
    return jsonify({
        'employee_id': emp.id, 'emp_code': emp.emp_code,
        'is_complete': complete, 'missing_fields': missing
    })

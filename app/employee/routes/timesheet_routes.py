"""Employee timesheet, shift swap, and comp-off routes."""

from datetime import date, datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, Timesheet, Project, ProjectMember, Task,
                        ShiftSwapRequest, Shift, CompOff, Notification)
from app.employee.forms import TimesheetForm
from app.hr import services


@bp.route('/timesheets')
@module_required('employee')
def my_timesheets():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    status_filter = request.args.get('status', '')
    date_from_str = request.args.get('date_from', '')
    date_to_str = request.args.get('date_to', '')

    query = Timesheet.query.filter_by(employee_id=emp.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    if date_from_str:
        try:
            d_from = datetime.strptime(date_from_str, '%Y-%m-%d').date()
            query = query.filter(Timesheet.date >= d_from)
        except ValueError:
            pass
            
    if date_to_str:
        try:
            d_to = datetime.strptime(date_to_str, '%Y-%m-%d').date()
            query = query.filter(Timesheet.date <= d_to)
        except ValueError:
            pass

    entries = query.order_by(Timesheet.date.desc()).all()

    total_hours = sum(e.hours_worked for e in entries)
    approved_hours = sum(e.hours_worked for e in entries if e.status == 'Approved')
    pending_hours = sum(e.hours_worked for e in entries if e.status == 'Pending')
    rejected_count = sum(1 for e in entries if e.status == 'Rejected')

    summary = {
        'total_hours': round(total_hours, 1),
        'approved_hours': round(approved_hours, 1),
        'pending_hours': round(pending_hours, 1),
        'rejected_count': rejected_count
    }

    return render_template('employee/my_timesheets.html', timesheets=entries, employee=emp,
                           summary=summary,
                           selected_status=status_filter,
                           date_from=date_from_str,
                           date_to=date_to_str)


@bp.route('/timesheets/submit', methods=['GET', 'POST'])
@module_required('employee')
def submit_timesheet():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    form = TimesheetForm()

    member_of = ProjectMember.query.filter_by(user_id=current_user.id).all()
    project_ids = [m.project_id for m in member_of]
    pm_projects = Project.query.filter_by(assigned_pm=current_user.id).all()
    all_project_ids = list(set(project_ids + [p.id for p in pm_projects]))
    projects = Project.query.filter(Project.id.in_(all_project_ids)).order_by(Project.name).all() if all_project_ids else []

    form.project_id.choices = [(0, '— Select Project —')] + [(p.id, p.name) for p in projects]
    form.task_id.choices = [(0, '— Optional: Select Task —')]

    if request.method == 'GET' and projects:
        first_project = projects[0]
        tasks = Task.query.filter_by(project_id=first_project.id).order_by(Task.title).all()
        form.task_id.choices += [(t.id, t.title) for t in tasks]

    if form.validate_on_submit():
        project_id = form.project_id.data
        if project_id == 0:
            flash('Please select a project.', 'danger')
            return render_template('employee/timesheet_form.html', form=form, employee=emp)

        task_id = form.task_id.data if form.task_id.data != 0 else None
        ts = Timesheet(
            employee_id=emp.id, project_id=project_id, task_id=task_id,
            date=form.date.data, hours_worked=form.hours_worked.data,
            description=form.description.data or '', status='Pending'
        )
        db.session.add(ts)

        project = Project.query.get(project_id)
        if project and project.assigned_pm:
            notif = Notification(
                user_id=project.assigned_pm,
                title='New Timesheet Entry',
                message=f'{current_user.full_name} submitted {form.hours_worked.data}h for "{project.name}" on {form.date.data}.',
                category='info', link='/pm/timesheet-approvals'
            )
            db.session.add(notif)
        db.session.commit()
        flash('Timesheet entry submitted for approval.', 'success')
        return redirect(url_for('employee.my_timesheets'))

    return render_template('employee/timesheet_form.html', form=form, employee=emp)


@bp.route('/api/tasks-for-project/<int:project_id>')
@module_required('employee')
def api_tasks_for_project(project_id):
    """AJAX endpoint — return tasks for a given project."""
    tasks = Task.query.filter_by(project_id=project_id).order_by(Task.title).all()
    return jsonify([{'id': t.id, 'title': t.title} for t in tasks])


# ===========================================================================
# SHIFT SWAP
# ===========================================================================
@bp.route('/shift-swap', methods=['GET', 'POST'])
@module_required('employee')
def shift_swap():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    my_requests = ShiftSwapRequest.query.filter_by(employee_id=emp.id)\
        .order_by(ShiftSwapRequest.created_at.desc()).all()
    shifts = Shift.query.filter_by(is_active=True).order_by(Shift.shift_name).all()

    if request.method == 'POST':
        requested_shift_id = request.form.get('requested_shift_id', type=int)
        reason = request.form.get('reason', '').strip()
        swap_date_str = request.form.get('swap_date', '').strip()

        if not requested_shift_id or not reason:
            flash('Please select a shift and provide a reason.', 'danger')
            return redirect(url_for('employee.shift_swap'))

        swap_date = None
        if swap_date_str:
            try:
                swap_date = datetime.strptime(swap_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format.', 'danger')
                return redirect(url_for('employee.shift_swap'))

        swap_req = ShiftSwapRequest(
            employee_id=emp.id,
            current_shift_id=emp.shift_id,
            requested_shift_id=requested_shift_id,
            swap_date=swap_date,
            reason=reason
        )
        db.session.add(swap_req)

        hr_notif = Notification(
            user_id=1,
            title='Shift Swap Request',
            message=f'{current_user.full_name} ({emp.emp_code}) requested a shift swap.',
            category='info', link='/hr/shift-swaps'
        )
        db.session.add(hr_notif)
        db.session.commit()
        flash('Shift swap request submitted.', 'success')
        return redirect(url_for('employee.shift_swap'))

    return render_template('employee/shift_swap.html', employee=emp,
                           my_requests=my_requests, shifts=shifts)


# ===========================================================================
# COMP-OFFS
# ===========================================================================
@bp.route('/comp-offs')
@module_required('employee')
def my_comp_offs():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    comp_offs = CompOff.query.filter_by(employee_id=emp.id)\
        .order_by(CompOff.earned_date.desc()).all()
    return render_template('employee/comp_offs.html', comp_offs=comp_offs, employee=emp)

"""Employee work routes — payslips, expenses, documents, performance, projects, tasks."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import (Employee, SalaryRecord, Expense, EmployeeDocument,
                        PerformanceReview, Project, ProjectMember, Task, Notification)
from app.employee.forms import ExpenseClaimForm
from app.hr import services


# ===========================================================================
# PAYSLIPS
# ===========================================================================
@bp.route('/payslips')
@module_required('employee')
def payslips():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    records = SalaryRecord.query.filter_by(employee_id=emp.id)\
        .order_by(SalaryRecord.year.desc(), SalaryRecord.month.desc()).all()
    return render_template('employee/payslips.html', records=records, employee=emp)


@bp.route('/payslips/<int:record_id>')
@module_required('employee')
def payslip_detail(record_id):
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    record = SalaryRecord.query.filter_by(id=record_id, employee_id=emp.id).first_or_404()
    return render_template('employee/payslip_detail.html', record=record, employee=emp)


# ===========================================================================
# EXPENSES
# ===========================================================================
@bp.route('/expenses')
@module_required('employee')
def expenses():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    claims = Expense.query.filter_by(submitted_by=current_user.id)\
        .order_by(Expense.date.desc()).all()
    return render_template('employee/expenses.html', claims=claims, employee=emp)


@bp.route('/expenses/submit', methods=['GET', 'POST'])
@module_required('employee')
def submit_expense():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    form = ExpenseClaimForm()
    if form.validate_on_submit():
        claim = Expense(
            submitted_by=emp.user.id,
            amount=form.amount.data,
            date=form.expense_date.data,
            category=form.category.data,
            description=form.description.data or '',
            status='Pending'
        )
        db.session.add(claim)
        notif = Notification(
            user_id=1,
            title='New Expense Claim',
            message=f'{current_user.full_name} submitted expense: {form.title.data} (₹{form.amount.data})',
            category='info', link='/finance/employee-expenses'
        )
        db.session.add(notif)
        db.session.commit()
        flash('Expense claim submitted.', 'success')
        return redirect(url_for('employee.expenses'))
    return render_template('employee/expense_form.html', form=form, employee=emp)


@bp.route('/expenses/<int:expense_id>')
@module_required('employee')
def expense_detail(expense_id):
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    claim = Expense.query.filter_by(id=expense_id, submitted_by=emp.user.id).first_or_404()
    return render_template('employee/expense_detail.html', claim=claim, employee=emp)


# ===========================================================================
# DOCUMENTS
# ===========================================================================
@bp.route('/documents')
@module_required('employee')
def documents():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    docs = EmployeeDocument.query.filter_by(employee_id=emp.id)\
        .order_by(EmployeeDocument.uploaded_at.desc()).all()
    return render_template('employee/documents.html', documents=docs, employee=emp)


@bp.route('/documents/<int:doc_id>/download')
@module_required('employee')
def document_download(doc_id):
    from flask import current_app, send_from_directory
    import os
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    doc = EmployeeDocument.query.filter_by(id=doc_id, employee_id=emp.id).first_or_404()
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
    return send_from_directory(upload_folder, doc.filename,
                               as_attachment=True, download_name=doc.original_name)


# ===========================================================================
# PERFORMANCE
# ===========================================================================
@bp.route('/performance')
@module_required('employee')
def performance():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    reviews = PerformanceReview.query.filter_by(employee_id=emp.id)\
        .order_by(PerformanceReview.created_at.desc()).all()
    return render_template('employee/performance.html', reviews=reviews, employee=emp)


@bp.route('/performance/<int:review_id>')
@module_required('employee')
def performance_detail(review_id):
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    review = PerformanceReview.query.filter_by(id=review_id, employee_id=emp.id).first_or_404()
    return render_template('employee/performance_detail.html', review=review, employee=emp)


# ===========================================================================
# PROJECTS & TASKS
# ===========================================================================
@bp.route('/projects')
@module_required('employee')
def projects():
    memberships = ProjectMember.query.filter_by(user_id=current_user.id).all()
    project_ids = [m.project_id for m in memberships]
    my_projects = Project.query.filter(Project.id.in_(project_ids)).order_by(Project.created_at.desc()).all() if project_ids else []
    return render_template('employee/projects.html', projects=my_projects, memberships=memberships)


@bp.route('/tasks')
@module_required('employee')
def my_tasks():
    status_filter = request.args.get('status', '')
    query = Task.query.filter_by(assigned_to=current_user.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
    tasks = query.order_by(Task.due_date.asc().nullslast()).all()
    return render_template('employee/my_tasks.html', tasks=tasks, selected_status=status_filter)


@bp.route('/api/tasks/<int:task_id>/status', methods=['POST'])
@module_required('employee')
def update_task_status(task_id):
    task = Task.query.filter_by(id=task_id, assigned_to=current_user.id).first_or_404()
    new_status = request.form.get('status', '')
    if new_status in ('Pending', 'In Progress', 'Done'):
        old_status = task.status
        task.status = new_status
        services.log_audit(current_user.id, 'UPDATE', 'Task', task.id,
                          f'Status: {old_status}→{new_status}', request.remote_addr or '')
        if task.project.assigned_pm:
            notif = Notification(
                user_id=task.project.assigned_pm,
                title='Task Status Updated',
                message=f'{current_user.full_name} changed "{task.title}" from {old_status} to {new_status}.',
                category='info', link=f'/pm/projects/{task.project_id}'
            )
            db.session.add(notif)
        db.session.commit()
        flash(f'Task status updated to {new_status}.', 'success')
    else:
        flash('Invalid status.', 'danger')
    return redirect(url_for('employee.my_tasks'))


@bp.route('/tasks/<int:task_id>/log-hours', methods=['POST'])
@module_required('employee')
def log_task_hours(task_id):
    task = Task.query.filter_by(id=task_id, assigned_to=current_user.id).first_or_404()
    hours = request.form.get('hours', type=float)
    if not hours or hours <= 0:
        flash('Invalid hours value.', 'danger')
        return redirect(url_for('employee.my_tasks'))
    task.actual_hours = (task.actual_hours or 0) + hours
    services.log_audit(current_user.id, 'LOG_HOURS', 'Task', task.id,
                      f'Logged {hours}h on "{task.title}"', request.remote_addr or '')
    db.session.commit()
    flash(f'{hours}h logged on "{task.title}".', 'success')
    return redirect(url_for('employee.my_tasks'))

"""Finance routes — salaries, expenses, invoices."""

from datetime import date
from flask import render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import current_user
from app.finance import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Expense, Invoice, SalaryRecord, Employee, EmployeeExpense, PayrollInput
from app.finance.forms import ExpenseForm, EmployeeExpenseForm, InvoiceForm, SalaryForm, PaymentForm
from app.finance import services


@bp.route('/')
@module_required('finance')
def dashboard():
    overdue_count = services.detect_and_update_overdue_invoices()
    if overdue_count > 0:
        db.session.commit()
    total_expenses = db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0)).scalar()
    pending_expenses = Expense.query.filter_by(status='Pending').count()
    total_invoiced = db.session.query(db.func.coalesce(db.func.sum(Invoice.amount), 0)).scalar()
    unpaid_invoices = Invoice.query.filter_by(status='Unpaid').count()
    total_salary_paid = db.session.query(
        db.func.coalesce(db.func.sum(SalaryRecord.net_salary), 0)
    ).filter(SalaryRecord.status == 'Paid').scalar()
    recent_expenses = Expense.query.order_by(Expense.date.desc()).limit(5).all()
    recent_invoices = Invoice.query.order_by(Invoice.issue_date.desc()).limit(5).all()
    pending_payroll_count = PayrollInput.query.filter_by(status='Submitted').count()
    return render_template('finance/dashboard.html',
                           total_expenses=total_expenses,
                           pending_expenses=pending_expenses,
                           total_invoiced=total_invoiced,
                           unpaid_invoices=unpaid_invoices,
                           total_salary_paid=total_salary_paid,
                           recent_expenses=recent_expenses,
                           recent_invoices=recent_invoices,
                           pending_payroll_count=pending_payroll_count)


# ── Expenses ─────────────────────────────────────────────────────────────────
@bp.route('/expenses')
@module_required('finance')
def expenses():
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = request.args.get('page', 1, type=int)

    filters = {
        'category': category,
        'status': status,
        'date_from': date_from,
        'date_to': date_to
    }
    paginated_expenses = services.get_expenses(filters, page=page, per_page=20)
    return render_template('finance/expenses.html',
                           expenses=paginated_expenses,
                           selected_category=category,
                           selected_status=status,
                           date_from=date_from,
                           date_to=date_to)


@bp.route('/expenses/add', methods=['GET', 'POST'])
@module_required('finance')
def add_expense():
    form = ExpenseForm()
    if form.validate_on_submit():
        services.create_expense(
            category=form.category.data,
            amount=form.amount.data,
            date_val=form.date.data,
            description=form.description.data,
            user_id=current_user.id,
            ip_address=request.remote_addr or ''
        )
        db.session.commit()
        flash('Expense recorded.', 'success')
        return redirect(url_for('finance.expenses'))
    return render_template('finance/expense_form.html', form=form, title='Add Expense')


@bp.route('/expenses/<int:expense_id>/edit', methods=['GET', 'POST'])
@module_required('finance')
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    form = ExpenseForm(obj=expense)
    if form.validate_on_submit():
        services.update_expense(
            expense_id=expense_id,
            category=form.category.data,
            amount=form.amount.data,
            date_val=form.date.data,
            description=form.description.data,
            user_id=current_user.id,
            ip_address=request.remote_addr or ''
        )
        db.session.commit()
        flash('Expense updated.', 'success')
        return redirect(url_for('finance.expenses'))
    return render_template('finance/expense_form.html', form=form, title='Edit Expense', expense=expense)


@bp.route('/expenses/<int:expense_id>/approve', methods=['POST'])
@module_required('finance')
def approve_expense(expense_id):
    services.approve_expense(expense_id, current_user.id, request.remote_addr or '')
    db.session.commit()
    flash('Expense approved.', 'success')
    return redirect(url_for('finance.expenses'))


@bp.route('/expenses/<int:expense_id>/reject', methods=['POST'])
@module_required('finance')
def reject_expense(expense_id):
    services.reject_expense(expense_id, current_user.id, request.remote_addr or '')
    db.session.commit()
    flash('Expense rejected.', 'warning')
    return redirect(url_for('finance.expenses'))


# ── Employee Expenses ────────────────────────────────────────────────────────
@bp.route('/employee-expenses')
@module_required('finance')
def employee_expenses():
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    payment_status = request.args.get('payment_status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    employee_search = request.args.get('employee_search', '').strip()
    employee_id = request.args.get('employee_id', type=int)
    page = request.args.get('page', 1, type=int)

    filters = {
        'category': category,
        'status': status,
        'payment_status': payment_status,
        'date_from': date_from,
        'date_to': date_to,
        'employee_id': employee_id,
        'employee_search': employee_search
    }
    paginated_claims = services.get_employee_expenses(filters, page=page, per_page=20)
    employees = Employee.query.order_by(Employee.emp_code).all()
    return render_template('finance/employee_expenses.html',
                           claims=paginated_claims,
                           employees=employees,
                           selected_category=category,
                           selected_status=status,
                           selected_payment_status=payment_status,
                           selected_employee=employee_id,
                           employee_search=employee_search,
                           date_from=date_from,
                           date_to=date_to)


@bp.route('/employee-expenses/<int:claim_id>')
@module_required('finance')
def employee_expense_detail(claim_id):
    claim = EmployeeExpense.query.get_or_404(claim_id)
    return render_template('finance/employee_expense_detail.html', claim=claim)


@bp.route('/employee-expenses/<int:claim_id>/receipt')
@module_required('finance')
def employee_expense_receipt(claim_id):
    import os
    claim = EmployeeExpense.query.get_or_404(claim_id)
    if not claim.receipt_filename:
        flash('No receipt attached to this claim.', 'warning')
        return redirect(url_for('finance.employee_expense_detail', claim_id=claim_id))
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
    return send_from_directory(upload_folder, claim.receipt_filename,
                               as_attachment=True, download_name=claim.receipt_original or claim.receipt_filename)


@bp.route('/employee-expenses/<int:claim_id>/approve', methods=['POST'])
@module_required('finance')
def approve_employee_expense(claim_id):
    services.approve_employee_expense(claim_id, current_user.id, request.remote_addr or '')
    db.session.commit()
    flash('Employee expense claim approved.', 'success')
    # Redirect back to referrer if from list page, otherwise to detail
    referrer = request.referrer or ''
    if 'employee-expenses' in referrer and str(claim_id) not in referrer:
        return redirect(url_for('finance.employee_expenses'))
    return redirect(url_for('finance.employee_expense_detail', claim_id=claim_id))


@bp.route('/employee-expenses/<int:claim_id>/reject', methods=['POST'])
@module_required('finance')
def reject_employee_expense(claim_id):
    rejection_notes = request.form.get('rejection_notes', '').strip()
    services.reject_employee_expense(claim_id, current_user.id, rejection_notes=rejection_notes, ip_address=request.remote_addr or '')
    db.session.commit()
    flash('Employee expense claim rejected.', 'warning')
    # Redirect back to referrer if from list page, otherwise to detail
    referrer = request.referrer or ''
    if 'employee-expenses' in referrer and str(claim_id) not in referrer:
        return redirect(url_for('finance.employee_expenses'))
    return redirect(url_for('finance.employee_expense_detail', claim_id=claim_id))


@bp.route('/employee-expenses/<int:claim_id>/mark-paid', methods=['POST'])
@module_required('finance')
def mark_employee_expense_paid(claim_id):
    payment_reference = request.form.get('payment_reference', '').strip()
    claim, err = services.mark_employee_expense_paid(claim_id, payment_reference, current_user.id, request.remote_addr or '')
    if err:
        flash(err, 'danger')
    else:
        db.session.commit()
        flash(f'Expense claim for {claim.employee.user.full_name} marked as reimbursed.', 'success')
    return redirect(url_for('finance.employee_expense_detail', claim_id=claim_id))


@bp.route('/employee-expenses/<int:claim_id>/edit', methods=['GET', 'POST'])
@module_required('finance')
def edit_employee_expense(claim_id):
    claim = EmployeeExpense.query.get_or_404(claim_id)
    form = EmployeeExpenseForm(obj=claim)
    if form.validate_on_submit():
        services.update_employee_expense(
            claim_id=claim_id,
            category=form.category.data,
            amount=form.amount.data,
            date_val=form.date.data,
            description=form.description.data,
            user_id=current_user.id,
            ip_address=request.remote_addr or ''
        )
        db.session.commit()
        flash('Employee expense claim updated.', 'success')
        return redirect(url_for('finance.employee_expenses'))
    return render_template('finance/employee_expense_form.html', form=form, title='Edit Employee Expense Claim', claim=claim)


# ── Invoices ─────────────────────────────────────────────────────────────────
@bp.route('/invoices')
@module_required('finance')
def invoices():
    overdue_count = services.detect_and_update_overdue_invoices()
    if overdue_count > 0:
        db.session.commit()
    status = request.args.get('status', '').strip()
    client_name = request.args.get('client_name', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = request.args.get('page', 1, type=int)

    filters = {
        'status': status,
        'client_name': client_name,
        'date_from': date_from,
        'date_to': date_to
    }
    paginated_invoices = services.get_invoices(filters, page=page, per_page=20)
    return render_template('finance/invoices.html',
                           invoices=paginated_invoices,
                           selected_status=status,
                           client_name=client_name,
                           date_from=date_from,
                           date_to=date_to)


@bp.route('/invoices/add', methods=['GET', 'POST'])
@module_required('finance')
def add_invoice():
    form = InvoiceForm()
    if form.validate_on_submit():
        invoice, err = services.create_invoice(
            invoice_number=form.invoice_number.data,
            client_name=form.client_name.data,
            amount=form.amount.data,
            issue_date=form.issue_date.data,
            due_date=form.due_date.data,
            status=form.status.data,
            description=form.description.data,
            user_id=current_user.id,
            ip_address=request.remote_addr or ''
        )
        if err:
            flash(err, 'danger')
            return render_template('finance/invoice_form.html', form=form, title='New Invoice')
        db.session.commit()
        flash(f'Invoice {invoice.invoice_number} created.', 'success')
        return redirect(url_for('finance.invoices'))
    return render_template('finance/invoice_form.html', form=form, title='New Invoice')


@bp.route('/invoices/<int:invoice_id>/edit', methods=['GET', 'POST'])
@module_required('finance')
def edit_invoice(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    form = InvoiceForm(obj=invoice)
    if form.validate_on_submit():
        updated_invoice, err = services.update_invoice(
            invoice_id=invoice_id,
            invoice_number=form.invoice_number.data,
            client_name=form.client_name.data,
            amount=form.amount.data,
            issue_date=form.issue_date.data,
            due_date=form.due_date.data,
            status=form.status.data,
            description=form.description.data,
            user_id=current_user.id,
            ip_address=request.remote_addr or ''
        )
        if err:
            flash(err, 'danger')
            return render_template('finance/invoice_form.html', form=form, title='Edit Invoice', invoice=invoice)
        db.session.commit()
        flash(f'Invoice {updated_invoice.invoice_number} updated.', 'success')
        return redirect(url_for('finance.invoices'))
    return render_template('finance/invoice_form.html', form=form, title='Edit Invoice', invoice=invoice)


@bp.route('/invoices/<int:invoice_id>/detail')
@module_required('finance')
def invoice_detail(invoice_id):
    invoice = Invoice.query.get_or_404(invoice_id)
    payment_form = PaymentForm()
    payment_form.payment_date.data = date.today()
    payment_form.amount.data = invoice.balance_due
    return render_template('finance/invoice_detail.html',
                           invoice=invoice,
                           form=payment_form)


@bp.route('/invoices/<int:invoice_id>/record-payment', methods=['POST'])
@module_required('finance')
def record_payment(invoice_id):
    form = PaymentForm()
    if form.validate_on_submit():
        services.record_payment(
            invoice_id=invoice_id,
            amount=form.amount.data,
            payment_date=form.payment_date.data,
            payment_method=form.payment_method.data,
            reference_number=form.reference_number.data,
            notes=form.notes.data,
            user_id=current_user.id,
            ip_address=request.remote_addr or ''
        )
        db.session.commit()
        flash('Payment recorded.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in field '{field}': {error}", 'danger')
    return redirect(url_for('finance.invoice_detail', invoice_id=invoice_id))


@bp.route('/invoices/<int:invoice_id>/delete', methods=['POST'])
@module_required('finance')
def delete_invoice(invoice_id):
    success, err = services.delete_invoice(invoice_id, current_user.id, request.remote_addr or '')
    if err:
        flash(err, 'danger')
    else:
        db.session.commit()
        flash('Invoice deleted.', 'success')
    return redirect(url_for('finance.invoices'))


# ── Salaries ─────────────────────────────────────────────────────────────────
@bp.route('/salaries')
@module_required('finance')
def salaries():
    status = request.args.get('status', '').strip()
    employee_id = request.args.get('employee_id', type=int)
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    page = request.args.get('page', 1, type=int)

    filters = {
        'status': status,
        'employee_id': employee_id,
        'date_from': date_from,
        'date_to': date_to
    }
    paginated_records = services.get_salaries(filters, page=page, per_page=20)
    employees = Employee.query.order_by(Employee.emp_code).all()
    return render_template('finance/salaries.html',
                           records=paginated_records,
                           employees=employees,
                           selected_status=status,
                           selected_employee=employee_id,
                           date_from=date_from,
                           date_to=date_to)


@bp.route('/salaries/add', methods=['GET', 'POST'])
@module_required('finance')
def add_salary():
    form = SalaryForm()
    employees = Employee.query.order_by(Employee.emp_code).all()

    if form.validate_on_submit():
        emp_id = request.form.get('employee_id', type=int)
        if not emp_id:
            flash('Please select an employee.', 'danger')
            return render_template('finance/salary_form.html', form=form,
                                   employees=employees, title='Add Salary Record')
        services.create_salary(
            employee_id=emp_id,
            month=form.month.data,
            year=form.year.data,
            basic=form.basic.data,
            hra=form.hra.data or 0,
            deductions=form.deductions.data or 0,
            status=form.status.data,
            user_id=current_user.id,
            ip_address=request.remote_addr or ''
        )
        db.session.commit()
        flash('Salary record created.', 'success')
        return redirect(url_for('finance.salaries'))
    return render_template('finance/salary_form.html', form=form,
                           employees=employees, title='Add Salary Record')


@bp.route('/salaries/<int:salary_id>/edit', methods=['GET', 'POST'])
@module_required('finance')
def edit_salary(salary_id):
    record = SalaryRecord.query.get_or_404(salary_id)
    if record.status != 'Pending':
        flash(f"Cannot edit a salary record with status '{record.status}'. Only Pending records can be edited.", 'danger')
        return redirect(url_for('finance.salaries'))

    form = SalaryForm(obj=record)
    employees = Employee.query.order_by(Employee.emp_code).all()

    if form.validate_on_submit():
        updated_record, err = services.update_salary(
            salary_id=salary_id,
            month=form.month.data,
            year=form.year.data,
            basic=form.basic.data,
            hra=form.hra.data or 0,
            deductions=form.deductions.data or 0,
            status=form.status.data,
            user_id=current_user.id,
            ip_address=request.remote_addr or ''
        )
        if err:
            flash(err, 'danger')
            return render_template('finance/salary_form.html', form=form,
                                   employees=employees, title='Edit Salary Record', record=record)
        db.session.commit()
        flash('Salary record updated.', 'success')
        return redirect(url_for('finance.salaries'))
    return render_template('finance/salary_form.html', form=form,
                           employees=employees, title='Edit Salary Record', record=record)


@bp.route('/salaries/<int:salary_id>/process', methods=['POST'])
@module_required('finance')
def process_salary_record(salary_id):
    record, err = services.process_salary(salary_id, current_user.id, request.remote_addr or '')
    if err:
        flash(err, 'danger')
    else:
        db.session.commit()
        flash(f'Salary for {record.employee.user.full_name} marked as Processed.', 'success')
    return redirect(url_for('finance.salaries'))


@bp.route('/salaries/<int:salary_id>/mark-paid', methods=['POST'])
@module_required('finance')
def mark_salary_paid(salary_id):
    record, err = services.mark_salary_paid(salary_id, current_user.id, request.remote_addr or '')
    if err:
        flash(err, 'danger')
    else:
        db.session.commit()
        flash(f'Salary for {record.employee.user.full_name} marked as Paid.', 'success')
    return redirect(url_for('finance.salaries'))


@bp.route('/salaries/bulk-pay', methods=['POST'])
@module_required('finance')
def bulk_pay_salaries():
    month = request.form.get('month', '').strip()
    year_val = request.form.get('year', '').strip()
    try:
        year = int(year_val) if year_val else None
    except ValueError:
        year = None

    if not month or not year:
        flash('Please select a specific month and year to bulk pay.', 'danger')
        return redirect(url_for('finance.salaries'))

    count, err = services.bulk_pay_salaries(
        month=month,
        year=year,
        user_id=current_user.id,
        ip_address=request.remote_addr or ''
    )
    if err:
        flash(err, 'warning')
    else:
        db.session.commit()
        flash(f'Successfully marked {count} salary records as Paid for {month} {year}.', 'success')
    return redirect(url_for('finance.salaries'))


@bp.route('/salaries/<int:salary_id>/payslip')
@module_required('finance')
def payslip_view(salary_id):
    record = SalaryRecord.query.get_or_404(salary_id)
    return render_template('finance/payslip_view.html', record=record)


# ── Payroll Pipeline ──────────────────────────────────────────────────────────
@bp.route('/payroll-inputs')
@module_required('finance')
def payroll_inputs():
    month = request.args.get('month', '').strip()
    year_val = request.args.get('year', None)
    try:
        year = int(year_val) if year_val else None
    except ValueError:
        year = None
    
    query = PayrollInput.query.filter_by(status='Submitted')
    if month:
        query = query.filter_by(month=month)
    if year:
        query = query.filter_by(year=year)
        
    pending_inputs = query.order_by(PayrollInput.year.desc(), PayrollInput.month.desc()).all()
    
    # Get distinct months/years from submitted inputs for filter dropdowns
    months = db.session.query(PayrollInput.month).filter_by(status='Submitted').distinct().all()
    years = db.session.query(PayrollInput.year).filter_by(status='Submitted').distinct().all()
    
    distinct_months = [m[0] for m in months]
    distinct_years = [y[0] for y in years]
    
    return render_template('finance/payroll_pipeline.html',
                           inputs=pending_inputs,
                           distinct_months=distinct_months,
                           distinct_years=distinct_years,
                           selected_month=month,
                           selected_year=year)


@bp.route('/payroll-inputs/<int:input_id>/process', methods=['POST'])
@module_required('finance')
def process_payroll(input_id):
    record, err = services.process_payroll_input(input_id, current_user.id, request.remote_addr or '')
    if err:
        flash(err, 'danger')
    else:
        db.session.commit()
        flash(f'Salary record created for {record.employee.user.full_name}.', 'success')
    return redirect(url_for('finance.payroll_inputs'))


@bp.route('/payroll-inputs/bulk-process', methods=['POST'])
@module_required('finance')
def bulk_process_payroll():
    month = request.form.get('month', '').strip()
    year_val = request.form.get('year', '').strip()
    try:
        year = int(year_val) if year_val else None
    except ValueError:
        year = None
    
    if not month or not year:
        flash('Please select a specific month and year to bulk process.', 'danger')
        return redirect(url_for('finance.payroll_inputs'))
        
    success_count, errors = services.bulk_process_payroll_inputs(
        month=month,
        year=year,
        user_id=current_user.id,
        ip_address=request.remote_addr or ''
    )
    
    if success_count > 0:
        db.session.commit()
        flash(f'Successfully bulk-processed {success_count} payroll inputs.', 'success')
    
    if errors:
        for err in errors[:5]:  # Limit flash messages to avoid cluttering
            flash(err, 'warning')
            
    return redirect(url_for('finance.payroll_inputs'))

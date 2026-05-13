"""HR payroll input routes."""

from datetime import date
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, PayrollInput
from app.hr.forms import PayrollInputForm, PayrollGenerateForm
from app.hr import services


@bp.route('/payroll')
@module_required('hr')
def payroll():
    year = request.args.get('year', date.today().year, type=int)
    month_name = request.args.get('month', '')
    query = PayrollInput.query.filter_by(year=year)
    if month_name:
        query = query.filter_by(month=month_name)
    inputs = query.join(Employee).order_by(Employee.emp_code).all()
    months = ['January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    return render_template('hr/payroll_input.html', inputs=inputs, year=year,
                           months=months, selected_month=month_name)


@bp.route('/payroll/generate', methods=['GET', 'POST'])
@module_required('hr')
def payroll_generate():
    form = PayrollGenerateForm()
    month_choices = [(i, m) for i, m in enumerate(
        ['', 'January', 'February', 'March', 'April', 'May', 'June',
         'July', 'August', 'September', 'October', 'November', 'December']
    ) if i > 0]
    form.month.choices = month_choices
    form.year.data = form.year.data or date.today().year

    if form.validate_on_submit():
        created, skipped = services.generate_payroll_inputs(form.year.data, form.month.data)
        services.log_audit(current_user.id, 'CREATE', 'PayrollInput', None,
                          f'Generated payroll: {created} created, {skipped} skipped',
                          request.remote_addr or '')
        db.session.commit()
        flash(f'Payroll inputs generated: {created} created, {skipped} already existed.', 'success')
        month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']
        return redirect(url_for('hr.payroll', year=form.year.data,
                                month=month_names[form.month.data]))
    return render_template('hr/payroll_generate.html', form=form, title='Generate Payroll Inputs')


@bp.route('/payroll/<int:payroll_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def payroll_edit(payroll_id):
    pi = PayrollInput.query.get_or_404(payroll_id)
    if pi.status == 'Submitted':
        flash('Cannot edit submitted payroll input.', 'danger')
        return redirect(url_for('hr.payroll'))
    form = PayrollInputForm(obj=pi)
    if form.validate_on_submit():
        pi.overtime_hours = form.overtime_hours.data or 0
        pi.bonus = form.bonus.data or 0
        pi.deduction_notes = form.deduction_notes.data or ''
        services.log_audit(current_user.id, 'UPDATE', 'PayrollInput', pi.id,
                          f'Updated payroll for emp#{pi.employee_id}', request.remote_addr or '')
        db.session.commit()
        flash('Payroll input updated.', 'success')
        return redirect(url_for('hr.payroll', year=pi.year, month=pi.month))
    return render_template('hr/payroll_form.html', form=form, payroll=pi,
                           title=f'Edit Payroll — {pi.employee.user.full_name}')


@bp.route('/payroll/submit', methods=['POST'])
@module_required('hr')
def payroll_submit():
    """Bulk submit all Draft payroll inputs for a month."""
    year = request.form.get('year', type=int)
    month = request.form.get('month', '')
    if not year or not month:
        flash('Invalid month/year.', 'danger')
        return redirect(url_for('hr.payroll'))

    drafts = PayrollInput.query.filter_by(year=year, month=month, status='Draft').all()
    count = 0
    for pi in drafts:
        pi.status = 'Submitted'
        pi.submitted_by = current_user.id
        count += 1

    if count > 0:
        services.log_audit(current_user.id, 'SUBMIT', 'PayrollInput', None,
                          f'Submitted {count} payroll inputs for {month} {year}',
                          request.remote_addr or '')
        db.session.commit()
        flash(f'{count} payroll inputs submitted to Finance.', 'success')
    else:
        flash('No draft payroll inputs to submit.', 'warning')
    return redirect(url_for('hr.payroll', year=year, month=month))

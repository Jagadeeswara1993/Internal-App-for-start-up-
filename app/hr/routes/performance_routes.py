"""HR performance management routes."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, Department, PerformanceReview
from app.hr.forms import PerformanceReviewForm
from app.hr import services


@bp.route('/performance')
@module_required('hr')
def performance():
    period_filter = request.args.get('period', '')
    dept_filter = request.args.get('department', type=int)
    query = PerformanceReview.query
    if period_filter:
        query = query.filter_by(review_period=period_filter)
    if dept_filter:
        query = query.join(Employee).filter(Employee.department_id == dept_filter)

    reviews = query.order_by(PerformanceReview.created_at.desc()).all()
    departments = Department.query.filter_by(is_active=True).order_by(Department.name).all()
    periods = services.get_review_periods()
    return render_template('hr/performance.html', reviews=reviews,
                           departments=departments, periods=periods,
                           selected_period=period_filter, selected_dept=dept_filter)


@bp.route('/performance/add', methods=['GET', 'POST'])
@module_required('hr')
def add_performance():
    form = PerformanceReviewForm()
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(0, '— Select Employee —')] + [
        (e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees
    ]
    form.review_period.choices = services.get_review_periods()

    if form.validate_on_submit():
        if form.employee_id.data == 0:
            flash('Please select an employee.', 'danger')
            return render_template('hr/performance_form.html', form=form, title='Add Review')
        review = PerformanceReview(
            employee_id=form.employee_id.data, reviewer_id=current_user.id,
            review_period=form.review_period.data, rating=form.rating.data,
            strengths=form.strengths.data or '', improvements=form.improvements.data or '',
            comments=form.comments.data or '', status='Submitted'
        )
        db.session.add(review)
        services.log_audit(current_user.id, 'CREATE', 'PerformanceReview', None,
                          f'Submitted review for emp#{review.employee_id}', request.remote_addr or '')
        db.session.commit()
        flash('Performance review submitted.', 'success')
        return redirect(url_for('hr.performance'))
    return render_template('hr/performance_form.html', form=form, title='Add Performance Review')


@bp.route('/performance/<int:review_id>')
@module_required('hr')
def performance_detail(review_id):
    review = PerformanceReview.query.get_or_404(review_id)
    return render_template('hr/performance_detail.html', review=review)


@bp.route('/performance/<int:review_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def edit_performance(review_id):
    review = PerformanceReview.query.get_or_404(review_id)
    form = PerformanceReviewForm(obj=review)
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees]
    form.review_period.choices = services.get_review_periods()

    if form.validate_on_submit():
        review.employee_id = form.employee_id.data
        review.review_period = form.review_period.data
        review.rating = form.rating.data
        review.strengths = form.strengths.data or ''
        review.improvements = form.improvements.data or ''
        review.comments = form.comments.data or ''
        review.status = 'Submitted'
        services.log_audit(current_user.id, 'UPDATE', 'PerformanceReview', review.id,
                          f'Updated review for emp#{review.employee_id}', request.remote_addr or '')
        db.session.commit()
        flash('Performance review updated.', 'success')
        return redirect(url_for('hr.performance'))
    return render_template('hr/performance_form.html', form=form,
                           title='Edit Performance Review', review=review)

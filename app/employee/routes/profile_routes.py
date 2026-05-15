"""Employee profile route."""

from datetime import datetime
from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.employee import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, ProfileUpdateRequest, Notification
from app.hr import services


@bp.route('/profile', methods=['GET', 'POST'])
@module_required('employee')
def profile():
    emp = Employee.query.filter_by(user_id=current_user.id).first_or_404()
    leave_balances = services.get_all_leave_balances(emp.id)

    pending_requests = ProfileUpdateRequest.query.filter_by(
        employee_id=emp.id, status='Pending'
    ).order_by(ProfileUpdateRequest.created_at.desc()).all()

    from app.employee.forms import ProfileUpdateBatchForm
    form = ProfileUpdateBatchForm()

    if request.method == 'POST':
        ALLOWED_FIELDS = {
            'phone': ('Phone Number', lambda v: v),
            'bank_account': ('Bank Account Number', lambda v: v),
            'pan_number': ('PAN Number', lambda v: v.upper()),
            'aadhar_number': ('Aadhaar Number', lambda v: v),
            'location': ('Location', lambda v: v),
            'date_of_birth': ('Date of Birth', lambda v: v),
        }

        changes_submitted = 0
        for field_name, (label, sanitize) in ALLOWED_FIELDS.items():
            new_value = request.form.get(field_name, '').strip()
            if not new_value:
                continue

            if field_name == 'phone':
                current_value = current_user.phone or ''
            elif field_name == 'date_of_birth':
                current_value = emp.date_of_birth.strftime('%Y-%m-%d') if emp.date_of_birth else ''
            else:
                current_value = getattr(emp, field_name, '') or ''

            sanitized = sanitize(new_value)
            if sanitized != current_value:
                existing_pending = ProfileUpdateRequest.query.filter_by(
                    employee_id=emp.id, field_name=field_name, status='Pending'
                ).first()
                if existing_pending:
                    existing_pending.new_value = sanitized
                    existing_pending.created_at = datetime.utcnow()
                else:
                    req = ProfileUpdateRequest(
                        employee_id=emp.id, field_name=field_name,
                        old_value=current_value, new_value=sanitized
                    )
                    db.session.add(req)
                changes_submitted += 1

        if changes_submitted > 0:
            hr_notif = Notification(
                user_id=1,
                title='Profile Update Request',
                message=f'{current_user.full_name} has submitted {changes_submitted} profile update(s) for HR review.',
                category='info', link='/hr/profile-update-requests'
            )
            db.session.add(hr_notif)
            db.session.commit()
            flash(f'{changes_submitted} change(s) submitted for HR approval.', 'success')
        else:
            flash('No changes detected.', 'info')
        return redirect(url_for('employee.profile'))

    return render_template('employee/profile.html', employee=emp,
                           leave_balances=leave_balances,
                           pending_requests=pending_requests,
                           form=form)

"""Admin user management routes — CRUD, module assignment, password reset, login history."""

import secrets
import string
from flask import render_template, redirect, url_for, flash, request, session
from app.admin import bp
from app.decorators import admin_required
from app.extensions import db
from app.models import (User, Module, UserModule, Employee, AuditLog,
                        LoginHistory, validate_password_complexity)
from app.admin.forms import UserCreateForm, UserEditForm, ModuleAssignForm


from app.admin import services


from app.utils.audit import log_audit


@bp.route('/users')
@admin_required
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    new_user_info = session.pop('new_user_info', None)
    from app.hr import services as hr_services
    return render_template('admin/users.html', users=all_users,
                           new_user_info=new_user_info,
                           is_profile_complete=hr_services.is_employee_profile_complete)


@bp.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    form = UserCreateForm()
    all_modules = Module.query.order_by(Module.name).all()
    form.modules.choices = [(m.id, m.name) for m in all_modules]

    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Username already exists.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Add User', all_modules=all_modules)
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already exists.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Add User', all_modules=all_modules)

        data = {
            'username': form.username.data,
            'email': form.email.data,
            'full_name': form.full_name.data,
            'phone': form.phone.data,
            'modules': form.modules.data
        }
        user, temp_password = services.create_user_and_employee(data, current_user.id)
        db.session.commit()

        session['new_user_info'] = {
            'username': user.username, 'full_name': user.full_name,
            'password': temp_password
        }
        flash(f'User "{user.username}" created successfully.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='Add User', all_modules=all_modules)


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)
    all_modules = Module.query.order_by(Module.name).all()
    form.modules.choices = [(m.id, m.name) for m in all_modules]

    if request.method == 'GET':
        form.is_active.data = user.is_active_user
        form.modules.data = [m.id for m in user.modules]

    if form.validate_on_submit():
        existing = User.query.filter(User.username == form.username.data, User.id != user.id).first()
        if existing:
            flash('Username already taken.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user, all_modules=all_modules)
        existing = User.query.filter(User.email == form.email.data, User.id != user.id).first()
        if existing:
            flash('Email already taken.', 'danger')
            return render_template('admin/user_form.html', form=form, title='Edit User', user=user, all_modules=all_modules)

        data = {
            'username': form.username.data,
            'email': form.email.data,
            'full_name': form.full_name.data,
            'phone': form.phone.data,
            'is_active_user': form.is_active.data,
            'password': form.password.data,
            'modules': form.modules.data
        }
        
        services.update_user(user, data, current_user.id)
        db.session.commit()
        flash(f'User "{user.username}" updated.', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/user_form.html', form=form, title='Edit User', user=user, all_modules=all_modules)


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete an admin user.', 'danger')
        return redirect(url_for('admin.users'))
    user.is_active_user = False
    from flask_login import current_user
    log_audit(current_user.id, 'DEACTIVATE', 'User', user.id, f'Deactivated user {user.username}')
    db.session.commit()
    flash(f'User "{user.username}" deactivated.', 'warning')
    return redirect(url_for('admin.users'))


@bp.route('/users/<int:user_id>/modules', methods=['GET', 'POST'])
@admin_required
def assign_modules(user_id):
    user = User.query.get_or_404(user_id)
    form = ModuleAssignForm()
    all_modules = Module.query.order_by(Module.name).all()
    form.modules.choices = [(m.id, m.name) for m in all_modules]
    if request.method == 'GET':
        form.modules.data = [m.id for m in user.modules]
    if form.validate_on_submit():
        UserModule.query.filter_by(user_id=user.id).delete()
        for mod_id in form.modules.data:
            db.session.add(UserModule(user_id=user.id, module_id=mod_id))
        db.session.commit()
        flash(f'Permissions updated for "{user.username}".', 'success')
        return redirect(url_for('admin.users'))
    return render_template('admin/assign_modules.html', form=form, user=user, modules=all_modules)


@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    temp_password = services.generate_readable_password()
    user.set_password(temp_password)
    user.must_change_password = True
    db.session.commit()
    session['new_user_info'] = {
        'username': user.username, 'full_name': user.full_name, 'password': temp_password
    }
    flash(f'Password reset for "{user.username}". See the credentials below.', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/login-history')
@admin_required
def login_history():
    """View all login attempts across the system."""
    user_filter = request.args.get('user', type=int)
    status_filter = request.args.get('status', '')
    page = request.args.get('page', 1, type=int)
    query = LoginHistory.query
    if user_filter:
        query = query.filter_by(user_id=user_filter)
    if status_filter:
        query = query.filter_by(status=status_filter)
    records = query.order_by(LoginHistory.login_at.desc()).paginate(
        page=page, per_page=30, error_out=False
    )
    users_list = User.query.order_by(User.full_name).all()
    return render_template('admin/login_history.html', records=records,
                           users=users_list, selected_user=user_filter,
                           selected_status=status_filter)


@bp.route('/users/<int:user_id>/unlock', methods=['POST'])
@admin_required
def unlock_user(user_id):
    """Manually unlock a locked user account."""
    user = User.query.get_or_404(user_id)
    user.reset_failed_logins()
    from flask_login import current_user
    log_audit(current_user.id, 'UNLOCK', 'User', user.id,
              f'Manually unlocked {user.username}')
    db.session.commit()
    flash(f'Account "{user.username}" has been unlocked.', 'success')
    return redirect(url_for('admin.login_history'))

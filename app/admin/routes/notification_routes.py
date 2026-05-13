"""Admin notification management routes."""

from flask import render_template, redirect, url_for, flash, request
from flask_login import current_user
from app.admin import bp
from app.decorators import admin_required
from app.extensions import db
from app.models import User, Notification, AuditLog


from app.utils.audit import log_audit
from app.admin import services


@bp.route('/notifications')
@admin_required
def notifications():
    """Admin notification management — view and send notifications."""
    page = request.args.get('page', 1, type=int)
    target = request.args.get('target', '')
    query = Notification.query
    if target:
        query = query.filter_by(user_id=target)
    notifs = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=30, error_out=False
    )
    users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    return render_template('admin/notifications.html', notifications=notifs,
                           users=users, selected_target=target)


@bp.route('/notifications/send', methods=['POST'])
@admin_required
def send_notification():
    """Send a notification to one user or all users."""
    target = request.form.get('target', '')
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    category = request.form.get('category', 'info')

    if not title or not message:
        flash('Title and message are required.', 'danger')
        return redirect(url_for('admin.notifications'))

    count = services.broadcast_notification(title, message, category, target, current_user.id)
    db.session.commit()
    flash(f'Notification sent to {count} user(s).', 'success')
    return redirect(url_for('admin.notifications'))


@bp.route('/notifications/<int:notif_id>/delete', methods=['POST'])
@admin_required
def delete_notification(notif_id):
    """Delete a notification."""
    notif = Notification.query.get_or_404(notif_id)
    db.session.delete(notif)
    db.session.commit()
    flash('Notification deleted.', 'warning')
    return redirect(url_for('admin.notifications'))

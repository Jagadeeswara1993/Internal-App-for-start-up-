from flask import request
from app.extensions import db
from app.models import AuditLog

def log_audit(user_id, action, entity_type, entity_id=None, details='', ip=''):
    """Write an audit log entry to the database."""
    # If no IP is provided, try to get it from the Flask request context
    if not ip:
        try:
            ip = request.remote_addr or ''
        except RuntimeError:
            ip = ''

    log = AuditLog(
        user_id=user_id, 
        action=action, 
        entity_type=entity_type,
        entity_id=entity_id, 
        details=details, 
        ip_address=ip
    )
    db.session.add(log)
    # The caller is responsible for db.session.commit()

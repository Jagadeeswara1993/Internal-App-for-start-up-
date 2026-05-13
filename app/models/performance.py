import re
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db



# ---------------------------------------------------------------------------
# PerformanceReview (Batch 2)
# ---------------------------------------------------------------------------
class PerformanceReview(db.Model):
    __tablename__ = 'performance_reviews'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id', ondelete='CASCADE'), nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    review_period = db.Column(db.String(30), nullable=False)        # Q1-2026, Annual-2025, etc.
    rating = db.Column(db.Integer, default=3)                       # 1-5
    strengths = db.Column(db.Text, default='')
    improvements = db.Column(db.Text, default='')
    comments = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Draft')              # Draft, Submitted, Acknowledged
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee = db.relationship('Employee', backref='performance_reviews')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id])

    def __repr__(self):
        return f'<PerformanceReview {self.review_period} emp#{self.employee_id}>'



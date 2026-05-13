import re
from datetime import datetime, date, time
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db



# ---------------------------------------------------------------------------
# JobPosting (Recruitment — Batch 2)
# ---------------------------------------------------------------------------
class JobPosting(db.Model):
    __tablename__ = 'job_postings'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    designation_id = db.Column(db.Integer, db.ForeignKey('designations.id'), nullable=True)
    description = db.Column(db.Text, default='')
    requirements = db.Column(db.Text, default='')
    vacancies = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='Open')        # Open, Closed, On Hold
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    creator = db.relationship('User', foreign_keys=[created_by])
    department = db.relationship('Department', foreign_keys=[department_id])
    designation = db.relationship('Designation', foreign_keys=[designation_id])
    candidates = db.relationship('Candidate', backref='job', lazy='dynamic')

    def __repr__(self):
        return f'<JobPosting {self.title}>'


# ---------------------------------------------------------------------------
# Candidate (Recruitment — Batch 2)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Candidate (Recruitment — Batch 2)
# ---------------------------------------------------------------------------
class Candidate(db.Model):
    __tablename__ = 'candidates'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_postings.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), default='')
    resume_file = db.Column(db.String(250), default='')
    status = db.Column(db.String(30), default='Applied')     # Applied, Screening, Interview, Offer, Hired, Rejected
    notes = db.Column(db.Text, default='')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    interviews = db.relationship('Interview', backref='candidate', lazy='dynamic')

    def __repr__(self):
        return f'<Candidate {self.name}>'


# ---------------------------------------------------------------------------
# Interview (Recruitment — Batch 2)
# ---------------------------------------------------------------------------




# ---------------------------------------------------------------------------
# Interview (Recruitment — Batch 2)
# ---------------------------------------------------------------------------
class Interview(db.Model):
    __tablename__ = 'interviews'

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('candidates.id', ondelete='CASCADE'), nullable=False)
    interviewer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration_mins = db.Column(db.Integer, default=60)
    interview_type = db.Column(db.String(30), default='Technical')  # Technical, HR, Managerial
    rating = db.Column(db.Integer, nullable=True)                   # 1-5
    feedback = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='Scheduled')          # Scheduled, Completed, Cancelled

    interviewer = db.relationship('User', foreign_keys=[interviewer_id])

    def __repr__(self):
        return f'<Interview #{self.id} for candidate#{self.candidate_id}>'


# ---------------------------------------------------------------------------
# PerformanceReview (Batch 2)
# ---------------------------------------------------------------------------



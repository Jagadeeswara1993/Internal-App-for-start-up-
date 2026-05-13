"""HR recruitment routes — job postings, candidates, interviews."""

import os
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import User, JobPosting, Candidate, Interview
from app.hr.forms import (JobPostingForm, CandidateForm, InterviewForm,
                          InterviewFeedbackForm)
from app.hr import services


@bp.route('/recruitment')
@module_required('hr')
def recruitment():
    status_filter = request.args.get('status', '')
    query = JobPosting.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    jobs = query.order_by(JobPosting.created_at.desc()).all()

    total_candidates = Candidate.query.count()
    pipeline = {}
    for status in ['Applied', 'Screening', 'Interview', 'Offer', 'Hired', 'Rejected']:
        pipeline[status] = Candidate.query.filter_by(status=status).count()

    return render_template('hr/recruitment.html', jobs=jobs, pipeline=pipeline,
                           total_candidates=total_candidates, selected_status=status_filter)


@bp.route('/recruitment/jobs/add', methods=['GET', 'POST'])
@module_required('hr')
def add_job():
    form = JobPostingForm()
    form.department_id.choices = [(0, '— Select —')] + services.get_departments_for_dropdown()
    form.designation_id.choices = [(0, '— Optional —')] + services.get_designations_for_dropdown()

    if form.validate_on_submit():
        job = JobPosting(
            title=form.title.data,
            department_id=form.department_id.data if form.department_id.data != 0 else None,
            designation_id=form.designation_id.data if form.designation_id.data != 0 else None,
            description=form.description.data or '', requirements=form.requirements.data or '',
            vacancies=form.vacancies.data, status=form.status.data,
            created_by=current_user.id
        )
        db.session.add(job)
        services.log_audit(current_user.id, 'CREATE', 'JobPosting', None,
                          f'Created job posting: {job.title}', request.remote_addr or '')
        db.session.commit()
        flash(f'Job posting "{job.title}" created.', 'success')
        return redirect(url_for('hr.recruitment'))
    return render_template('hr/job_form.html', form=form, title='Create Job Posting')


@bp.route('/recruitment/jobs/<int:job_id>')
@module_required('hr')
def job_detail(job_id):
    job = JobPosting.query.get_or_404(job_id)
    candidates = Candidate.query.filter_by(job_id=job.id).order_by(Candidate.applied_at.desc()).all()
    return render_template('hr/job_detail.html', job=job, candidates=candidates)


@bp.route('/recruitment/jobs/<int:job_id>/candidates/add', methods=['GET', 'POST'])
@module_required('hr')
def add_candidate(job_id):
    job = JobPosting.query.get_or_404(job_id)
    form = CandidateForm()

    if form.validate_on_submit():
        resume_filename = ''
        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
                os.makedirs(upload_folder, exist_ok=True)
                import uuid
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'pdf'
                safe_name = f"resume_{uuid.uuid4().hex[:8]}.{ext}"
                file.save(os.path.join(upload_folder, safe_name))
                resume_filename = safe_name

        candidate = Candidate(
            job_id=job.id, name=form.name.data, email=form.email.data,
            phone=form.phone.data or '', status=form.status.data,
            notes=form.notes.data or '', resume_file=resume_filename
        )
        db.session.add(candidate)
        services.log_audit(current_user.id, 'CREATE', 'Candidate', None,
                          f'Added candidate {candidate.name} for {job.title}', request.remote_addr or '')
        db.session.commit()
        flash(f'Candidate "{candidate.name}" added.', 'success')
        return redirect(url_for('hr.job_detail', job_id=job.id))
    return render_template('hr/candidate_form.html', form=form, job=job, title='Add Candidate')


@bp.route('/recruitment/candidates/<int:candidate_id>/edit', methods=['GET', 'POST'])
@module_required('hr')
def edit_candidate(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    form = CandidateForm(obj=candidate)

    if form.validate_on_submit():
        old_status = candidate.status
        candidate.name = form.name.data
        candidate.email = form.email.data
        candidate.phone = form.phone.data or ''
        candidate.status = form.status.data
        candidate.notes = form.notes.data or ''

        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename:
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
                os.makedirs(upload_folder, exist_ok=True)
                import uuid
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'pdf'
                safe_name = f"resume_{uuid.uuid4().hex[:8]}.{ext}"
                file.save(os.path.join(upload_folder, safe_name))
                candidate.resume_file = safe_name

        services.log_audit(current_user.id, 'UPDATE', 'Candidate', candidate.id,
                          f'Status: {old_status} → {candidate.status}', request.remote_addr or '')
        db.session.commit()
        flash(f'Candidate "{candidate.name}" updated.', 'success')
        return redirect(url_for('hr.job_detail', job_id=candidate.job_id))
    return render_template('hr/candidate_form.html', form=form, job=candidate.job,
                           title='Edit Candidate', candidate=candidate)


@bp.route('/recruitment/candidates/<int:candidate_id>/interview', methods=['GET', 'POST'])
@module_required('hr')
def schedule_interview(candidate_id):
    candidate = Candidate.query.get_or_404(candidate_id)
    form = InterviewForm()
    users = User.query.filter_by(is_active_user=True).order_by(User.full_name).all()
    form.interviewer_id.choices = [(0, '— Select —')] + [(u.id, u.full_name) for u in users]

    if form.validate_on_submit():
        scheduled_dt = datetime.combine(form.scheduled_date.data,
                                        datetime.strptime(form.scheduled_time.data, '%H:%M').time())
        interview = Interview(
            candidate_id=candidate.id, interviewer_id=form.interviewer_id.data,
            scheduled_at=scheduled_dt, duration_mins=form.duration_mins.data,
            interview_type=form.interview_type.data, status='Scheduled'
        )
        db.session.add(interview)
        if candidate.status in ('Applied', 'Screening'):
            candidate.status = 'Interview'
        services.log_audit(current_user.id, 'CREATE', 'Interview', None,
                          f'Scheduled {interview.interview_type} for {candidate.name}',
                          request.remote_addr or '')
        db.session.commit()
        flash(f'Interview scheduled for {candidate.name}.', 'success')
        return redirect(url_for('hr.job_detail', job_id=candidate.job_id))
    return render_template('hr/interview_form.html', form=form, candidate=candidate,
                           title='Schedule Interview')


@bp.route('/recruitment/interviews/<int:interview_id>/feedback', methods=['GET', 'POST'])
@module_required('hr')
def interview_feedback(interview_id):
    interview = Interview.query.get_or_404(interview_id)
    form = InterviewFeedbackForm()
    if form.validate_on_submit():
        interview.rating = form.rating.data
        interview.feedback = form.feedback.data
        interview.status = 'Completed'
        services.log_audit(current_user.id, 'UPDATE', 'Interview', interview.id,
                          f'Feedback rating: {interview.rating}/5', request.remote_addr or '')
        db.session.commit()
        flash('Interview feedback submitted.', 'success')
        return redirect(url_for('hr.job_detail', job_id=interview.candidate.job_id))
    return render_template('hr/interview_feedback.html', form=form, interview=interview,
                           title='Interview Feedback')


@bp.route('/recruitment/candidates/<int:candidate_id>/resume')
@module_required('hr')
def download_resume(candidate_id):
    """Download a candidate's resume file."""
    candidate = Candidate.query.get_or_404(candidate_id)
    if not candidate.resume_file:
        flash('No resume uploaded for this candidate.', 'warning')
        return redirect(url_for('hr.job_detail', job_id=candidate.job_id))
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
    return send_from_directory(upload_folder, candidate.resume_file,
                               as_attachment=True,
                               download_name=f'{candidate.name}_resume.pdf')

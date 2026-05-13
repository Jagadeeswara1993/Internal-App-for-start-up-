"""HR document management routes."""

import os
from flask import render_template, redirect, url_for, flash, request, current_app, send_from_directory
from flask_login import current_user
from app.hr import bp
from app.decorators import module_required
from app.extensions import db
from app.models import Employee, EmployeeDocument
from app.hr.forms import DocumentUploadForm
from app.hr import services


@bp.route('/documents')
@module_required('hr')
def documents():
    emp_filter = request.args.get('employee', type=int)
    query = EmployeeDocument.query
    if emp_filter:
        query = query.filter_by(employee_id=emp_filter)
    docs = query.order_by(EmployeeDocument.uploaded_at.desc()).all()
    employees = Employee.query.order_by(Employee.emp_code).all()
    return render_template('hr/documents.html', documents=docs, employees=employees,
                           selected_emp=emp_filter)


@bp.route('/documents/upload', methods=['GET', 'POST'])
@module_required('hr')
def document_upload():
    form = DocumentUploadForm()
    employees = Employee.query.order_by(Employee.emp_code).all()
    form.employee_id.choices = [(0, '— Select Employee —')] + [
        (e.id, f'{e.emp_code} — {e.user.full_name}') for e in employees
    ]

    if form.validate_on_submit():
        if form.employee_id.data == 0:
            flash('Please select an employee.', 'danger')
            return render_template('hr/document_upload.html', form=form, title='Upload Document')

        file = form.document.data
        emp = Employee.query.get(form.employee_id.data)
        if not emp:
            flash('Employee not found.', 'danger')
            return redirect(url_for('hr.documents'))

        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
        os.makedirs(upload_folder, exist_ok=True)
        safe_name = services.generate_safe_filename(file.filename, emp.emp_code)
        filepath = os.path.join(upload_folder, safe_name)
        file.save(filepath)

        doc = EmployeeDocument(
            employee_id=emp.id, doc_type=form.doc_type.data,
            filename=safe_name, original_name=file.filename,
            uploaded_by=current_user.id
        )
        db.session.add(doc)
        services.log_audit(current_user.id, 'CREATE', 'EmployeeDocument', None,
                          f'Uploaded {form.doc_type.data} for {emp.emp_code}',
                          request.remote_addr or '')
        db.session.commit()
        flash(f'Document "{file.filename}" uploaded for {emp.emp_code}.', 'success')
        return redirect(url_for('hr.documents', employee=emp.id))
    return render_template('hr/document_upload.html', form=form, title='Upload Document')


@bp.route('/documents/<int:doc_id>/download')
@module_required('hr')
def document_download(doc_id):
    doc = EmployeeDocument.query.get_or_404(doc_id)
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
    return send_from_directory(upload_folder, doc.filename,
                               as_attachment=True,
                               download_name=doc.original_name)


@bp.route('/documents/<int:doc_id>/delete', methods=['POST'])
@module_required('hr')
def document_delete(doc_id):
    doc = EmployeeDocument.query.get_or_404(doc_id)
    emp_id = doc.employee_id
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/uploads/documents')
    filepath = os.path.join(upload_folder, doc.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    services.log_audit(current_user.id, 'DELETE', 'EmployeeDocument', doc.id,
                      f'Deleted {doc.doc_type} ({doc.original_name})',
                      request.remote_addr or '')
    db.session.delete(doc)
    db.session.commit()
    flash('Document deleted.', 'warning')
    return redirect(url_for('hr.documents', employee=emp_id))

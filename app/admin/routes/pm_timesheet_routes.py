"""Admin PM overview, timesheet management, and organization analytics routes."""

import csv
import io
from collections import defaultdict
from datetime import date as date_cls, timedelta
from flask import render_template, redirect, url_for, flash, request, session, Response
from flask_login import current_user
from app.admin import bp
from app.decorators import admin_required
from app.extensions import db
from app.models import (User, Employee, Project, Task, Notification,
                        AuditLog, Timesheet, Department)


from app.utils.audit import log_audit


# ===========================================================================
# PM OVERVIEW (Admin as PM Lead)
# ===========================================================================
@bp.route('/pm-overview')
@admin_required
def pm_overview():
    """Admin PM overview — all projects grouped by assigned PM."""
    all_projects = Project.query.order_by(Project.assigned_pm, Project.created_at.desc()).all()

    pm_groups = {}
    unassigned = []
    for p in all_projects:
        if p.assigned_pm:
            pm_user = User.query.get(p.assigned_pm)
            if pm_user not in pm_groups:
                pm_groups[pm_user] = []
            pm_groups[pm_user].append(p)
        else:
            unassigned.append(p)

    pm_stats = []
    for pm_user, projects in pm_groups.items():
        total_tasks = sum(p.tasks.count() for p in projects)
        pending = sum(p.tasks.filter_by(status='Pending').count() for p in projects)
        in_progress = sum(p.tasks.filter_by(status='In Progress').count() for p in projects)
        done = sum(p.tasks.filter_by(status='Done').count() for p in projects)
        overdue = sum(p.tasks.filter(Task.due_date < db.func.current_date(), Task.status != 'Done').count() for p in projects)
        team_count = len(set(m.user_id for p in projects for m in p.members))
        pm_stats.append({
            'pm': pm_user, 'projects': projects, 'total_tasks': total_tasks,
            'pending': pending, 'in_progress': in_progress, 'done': done,
            'overdue': overdue, 'team_count': team_count,
        })

    total = len(all_projects)
    active = sum(1 for p in all_projects if p.status == 'In Progress')
    completed = sum(1 for p in all_projects if p.status == 'Completed')
    delayed = sum(1 for p in all_projects if p.is_delayed)

    return render_template('admin/pm_overview.html',
                           pm_stats=pm_stats, unassigned_projects=unassigned,
                           total_projects=total, active_projects=active,
                           completed_projects=completed, delayed_projects=delayed)


# ===========================================================================
# TIMESHEET MANAGEMENT (Admin Override)
# ===========================================================================
@bp.route('/timesheets')
@admin_required
def timesheets():
    """Global timesheet report — all entries, all projects."""
    status_filter = request.args.get('status', '')
    project_filter = request.args.get('project', type=int)
    employee_filter = request.args.get('employee', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Timesheet.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if project_filter:
        query = query.filter_by(project_id=project_filter)
    if employee_filter:
        query = query.filter_by(employee_id=employee_filter)
    if date_from:
        try:
            from datetime import datetime
            query = query.filter(Timesheet.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import datetime
            query = query.filter(Timesheet.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    page = request.args.get('page', 1, type=int)
    records = query.order_by(Timesheet.date.desc()).paginate(page=page, per_page=25, error_out=False)
    projects = Project.query.order_by(Project.name).all()
    employees = Employee.query.order_by(Employee.emp_code).all()

    total_hours = db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).filter(query.whereclause).scalar() if query.whereclause is not None else db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).scalar()
    approved_hours = db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).filter(query.whereclause, Timesheet.status == 'Approved').scalar() if query.whereclause is not None else db.session.query(db.func.coalesce(db.func.sum(Timesheet.hours_worked), 0)).filter(Timesheet.status == 'Approved').scalar()

    return render_template('admin/timesheets.html', records=records,
                           projects=projects, employees=employees,
                           selected_status=status_filter,
                           selected_project=project_filter,
                           selected_employee=employee_filter,
                           date_from=date_from, date_to=date_to,
                           total_hours=total_hours, approved_hours=approved_hours)


@bp.route('/timesheets/<int:ts_id>/force-approve', methods=['POST'])
@admin_required
def force_approve_timesheet(ts_id):
    """Admin overrides: force-approve a timesheet."""
    from datetime import datetime
    ts = Timesheet.query.get_or_404(ts_id)
    if ts.status == 'Approved':
        flash('Timesheet is already approved.', 'warning')
        return redirect(url_for('admin.timesheets'))

    old_status = ts.status
    ts.status = 'Approved'
    ts.approved_by = session.get('user_id') or 1
    ts.approved_at = datetime.utcnow()

    if ts.task_id:
        task = Task.query.get(ts.task_id)
        if task:
            task.actual_hours = (task.actual_hours or 0) + ts.hours_worked

    log_audit(current_user.id, 'FORCE_APPROVE', 'Timesheet', ts.id,
              f'Admin force-approved (was {old_status}): {ts.hours_worked}h emp#{ts.employee_id}')

    notif = Notification(user_id=ts.employee.user_id,
                        title='Timesheet Force-Approved',
                        message=f'Admin force-approved your timesheet for {ts.date.strftime("%d %b %Y")} ({ts.hours_worked}h).',
                        category='success', link='/employee/timesheets')
    db.session.add(notif)
    if ts.project.assigned_pm:
        pm_notif = Notification(user_id=ts.project.assigned_pm,
                               title='Admin Override: Timesheet Approved',
                               message=f'Admin force-approved timesheet #{ts.id} for {ts.employee_name}.',
                               category='info', link='/pm/timesheet-approvals')
        db.session.add(pm_notif)

    db.session.commit()
    flash(f'Timesheet #{ts.id} force-approved by Admin.', 'success')
    return redirect(url_for('admin.timesheets'))


@bp.route('/timesheets/<int:ts_id>/force-reject', methods=['POST'])
@admin_required
def force_reject_timesheet(ts_id):
    """Admin overrides: force-reject a timesheet."""
    ts = Timesheet.query.get_or_404(ts_id)
    reason = request.form.get('rejection_reason', 'Admin override').strip()
    old_status = ts.status

    if old_status == 'Approved' and ts.task_id:
        task = Task.query.get(ts.task_id)
        if task:
            task.actual_hours = max(0, (task.actual_hours or 0) - ts.hours_worked)

    ts.status = 'Rejected'
    ts.rejection_reason = reason

    log_audit(current_user.id, 'FORCE_REJECT', 'Timesheet', ts.id,
              f'Admin force-rejected (was {old_status}): {reason}')

    notif = Notification(user_id=ts.employee.user_id,
                        title='Timesheet Force-Rejected',
                        message=f'Admin rejected your timesheet for {ts.date.strftime("%d %b %Y")}: {reason}',
                        category='danger', link='/employee/timesheets')
    db.session.add(notif)
    db.session.commit()
    flash(f'Timesheet #{ts.id} force-rejected.', 'warning')
    return redirect(url_for('admin.timesheets'))


@bp.route('/timesheets/export')
@admin_required
def export_timesheets():
    """Export timesheets as CSV or Excel."""
    fmt = request.args.get('format', 'csv')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = Timesheet.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if date_from:
        try:
            from datetime import datetime
            query = query.filter(Timesheet.date >= datetime.strptime(date_from, '%Y-%m-%d').date())
        except ValueError:
            pass
    if date_to:
        try:
            from datetime import datetime
            query = query.filter(Timesheet.date <= datetime.strptime(date_to, '%Y-%m-%d').date())
        except ValueError:
            pass

    records = query.order_by(Timesheet.date.desc()).all()
    headers = ['ID', 'Employee Code', 'Employee Name', 'Date', 'Project',
               'Task', 'Hours', 'Description', 'Status', 'Approved By', 'Approved At']
    rows = []
    for r in records:
        rows.append([
            r.id, r.employee.emp_code, r.employee_name,
            r.date.strftime('%Y-%m-%d'), r.project_name, r.task_title,
            r.hours_worked, r.description, r.status,
            r.approver.full_name if r.approver else '',
            r.approved_at.strftime('%Y-%m-%d %H:%M') if r.approved_at else ''
        ])

    if fmt == 'xlsx':
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Timesheets'
            ws.append(headers)
            for row in rows:
                ws.append(row)
            for cell in ws[1]:
                cell.font = openpyxl.styles.Font(bold=True)
            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={'Content-Disposition': 'attachment; filename=timesheets_export.xlsx'}
            )
        except ImportError:
            flash('Excel export requires openpyxl. Falling back to CSV.', 'warning')

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        output.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=timesheets_export.csv'}
    )


# ===========================================================================
# ORGANIZATION ANALYTICS
# ===========================================================================
@bp.route('/analytics')
@admin_required
def analytics():
    """Organization-wide analytics — all projects, employees, hours."""
    from app.utils.analytics import get_organization_analytics_data
    data = get_organization_analytics_data()
    return render_template('admin/analytics.html', **data)

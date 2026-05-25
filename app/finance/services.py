"""Finance Services — Business logic for expenses, invoices, and salary actions.

Extracts database transactions, validation checks, audit logging, and notification creation
from the finance controllers, supporting robust search filtering and pagination.
"""

from datetime import datetime, date
from app.extensions import db
from app.models import Expense, Invoice, SalaryRecord, Employee, EmployeeExpense, Notification, PayrollInput
from app.utils.audit import log_audit


# ===========================================================================
# EXPENSES SERVICES
# ===========================================================================

def get_expenses(filters=None, page=1, per_page=20):
    """Retrieve filtered, paginated expenses ordered by date descending."""
    query = Expense.query
    if filters:
        if filters.get('category'):
            query = query.filter(Expense.category == filters['category'])
        if filters.get('status'):
            query = query.filter(Expense.status == filters['status'])
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(Expense.date >= date_from)
            except (ValueError, TypeError):
                pass
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(Expense.date <= date_to)
            except (ValueError, TypeError):
                pass
    return query.order_by(Expense.date.desc()).paginate(page=page, per_page=per_page, error_out=False)


def create_expense(category, amount, date_val, description, user_id, ip_address=''):
    """Create a new expense and record an audit log entry."""
    expense = Expense(
        category=category,
        amount=amount,
        date=date_val or date.today(),
        description=description or '',
        submitted_by=user_id
    )
    db.session.add(expense)
    db.session.flush()  # Populates expense.id for audit log
    
    log_audit(
        user_id=user_id,
        action='CREATE',
        entity_type='Expense',
        entity_id=expense.id,
        details=f"Recorded expense of ₹{amount:.2f} under {category}",
        ip=ip_address
    )
    return expense


def update_expense(expense_id, category, amount, date_val, description, user_id, ip_address=''):
    """Update an existing expense and record an audit log entry."""
    expense = Expense.query.get_or_404(expense_id)
    old_amount = expense.amount
    old_category = expense.category
    
    expense.category = category
    expense.amount = amount
    expense.date = date_val or date.today()
    expense.description = description or ''
    
    log_audit(
        user_id=user_id,
        action='UPDATE',
        entity_type='Expense',
        entity_id=expense.id,
        details=f"Updated expense from ₹{old_amount:.2f} ({old_category}) to ₹{amount:.2f} ({category})",
        ip=ip_address
    )
    return expense


def approve_expense(expense_id, user_id, ip_address=''):
    """Approve a company expense claim."""
    expense = Expense.query.get_or_404(expense_id)
    expense.status = 'Approved'
    
    log_audit(
        user_id=user_id,
        action='APPROVE',
        entity_type='Expense',
        entity_id=expense.id,
        details=f"Approved expense of ₹{expense.amount:.2f} (Category: {expense.category})",
        ip=ip_address
    )
    return expense


def reject_expense(expense_id, user_id, ip_address=''):
    """Reject a company expense claim."""
    expense = Expense.query.get_or_404(expense_id)
    expense.status = 'Rejected'
    
    log_audit(
        user_id=user_id,
        action='REJECT',
        entity_type='Expense',
        entity_id=expense.id,
        details=f"Rejected expense of ₹{expense.amount:.2f} (Category: {expense.category})",
        ip=ip_address
    )
    return expense


# ===========================================================================
# EMPLOYEE EXPENSE CLAIMS SERVICES (WITH NOTIFICATIONS)
# ===========================================================================

def get_employee_expenses(filters=None, page=1, per_page=20):
    """Retrieve filtered, paginated employee expense claims."""
    query = EmployeeExpense.query.join(Employee)
    if filters:
        if filters.get('category'):
            query = query.filter(EmployeeExpense.category == filters['category'])
        if filters.get('status'):
            query = query.filter(EmployeeExpense.status == filters['status'])
        if filters.get('employee_id'):
            query = query.filter(EmployeeExpense.employee_id == filters['employee_id'])
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(EmployeeExpense.date >= date_from)
            except (ValueError, TypeError):
                pass
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(EmployeeExpense.date <= date_to)
            except (ValueError, TypeError):
                pass
    return query.order_by(EmployeeExpense.date.desc()).paginate(page=page, per_page=per_page, error_out=False)


def approve_employee_expense(claim_id, user_id, ip_address=''):
    """Approve employee expense claim, notify employee, log audit."""
    claim = EmployeeExpense.query.get_or_404(claim_id)
    claim.status = 'Approved'
    claim.reviewed_by = user_id
    
    log_audit(
        user_id=user_id,
        action='APPROVE',
        entity_type='EmployeeExpense',
        entity_id=claim.id,
        details=f"Approved claim of ₹{claim.amount:.2f} for employee ID {claim.employee_id}",
        ip=ip_address
    )
    
    # Notify the employee
    notif = Notification(
        user_id=claim.employee.user_id,
        title='Expense Claim Approved',
        message=f'Your expense claim of ₹{claim.amount:,.2f} for category "{claim.category}" has been approved.',
        category='success',
        link='/employee/expenses'
    )
    db.session.add(notif)
    return claim


def reject_employee_expense(claim_id, user_id, ip_address=''):
    """Reject employee expense claim, notify employee, log audit."""
    claim = EmployeeExpense.query.get_or_404(claim_id)
    claim.status = 'Rejected'
    claim.reviewed_by = user_id
    
    log_audit(
        user_id=user_id,
        action='REJECT',
        entity_type='EmployeeExpense',
        entity_id=claim.id,
        details=f"Rejected claim of ₹{claim.amount:.2f} for employee ID {claim.employee_id}",
        ip=ip_address
    )
    
    # Notify the employee
    notif = Notification(
        user_id=claim.employee.user_id,
        title='Expense Claim Rejected',
        message=f'Your expense claim of ₹{claim.amount:,.2f} for category "{claim.category}" has been rejected.',
        category='warning',
        link='/employee/expenses'
    )
    db.session.add(notif)
    return claim


def update_employee_expense(claim_id, category, amount, date_val, description, user_id, ip_address=''):
    """Update an existing employee expense claim and record an audit log entry."""
    claim = EmployeeExpense.query.get_or_404(claim_id)
    old_amount = claim.amount
    old_category = claim.category
    
    claim.category = category
    claim.amount = amount
    claim.date = date_val or date.today()
    claim.description = description or ''
    
    log_audit(
        user_id=user_id,
        action='UPDATE',
        entity_type='EmployeeExpense',
        entity_id=claim.id,
        details=f"Updated employee claim from ₹{old_amount:.2f} ({old_category}) to ₹{amount:.2f} ({category}) for employee ID {claim.employee_id}",
        ip=ip_address
    )
    return claim


def process_payroll_input(input_id, user_id, ip_address=''):
    """Convert a submitted PayrollInput into a SalaryRecord."""
    pi = PayrollInput.query.get_or_404(input_id)
    if pi.status != 'Submitted':
        return None, "Payroll input is not in Submitted status."
        
    emp = pi.employee
    basic = emp.salary
    hra = basic * 0.4
    
    # Calculate deductions: (salary / working_days) * leaves_taken
    if pi.working_days and pi.working_days > 0:
        deductions = (basic / pi.working_days) * pi.leaves_taken
    else:
        deductions = 0.0
        
    # Round calculations
    basic = round(basic, 2)
    hra = round(hra, 2)
    deductions = round(deductions, 2)
    net_salary = round(basic + hra - deductions + (pi.bonus or 0.0), 2)
    
    # Check if a SalaryRecord already exists for this employee, month, and year
    existing = SalaryRecord.query.filter_by(
        employee_id=pi.employee_id,
        month=pi.month,
        year=pi.year
    ).first()
    
    if existing:
        return None, f"Salary record already exists for {emp.user.full_name} for {pi.month}/{pi.year}."
        
    # Create SalaryRecord
    salary_record = SalaryRecord(
        employee_id=pi.employee_id,
        month=pi.month,
        year=pi.year,
        basic=basic,
        hra=hra,
        deductions=deductions,
        net_salary=net_salary,
        status='Pending'
    )
    db.session.add(salary_record)
    
    # Mark PayrollInput as Processed
    pi.status = 'Processed'
    db.session.flush()
    
    log_audit(
        user_id=user_id,
        action='PROCESS_PAYROLL',
        entity_type='PayrollInput',
        entity_id=pi.id,
        details=f"Processed payroll input for {emp.user.full_name} ({pi.month}/{pi.year}) -> Net: ₹{net_salary:.2f}",
        ip=ip_address
    )
    
    return salary_record, None


def bulk_process_payroll_inputs(month, year, user_id, ip_address=''):
    """Bulk convert all submitted PayrollInputs for a given month and year into SalaryRecords."""
    inputs = PayrollInput.query.filter_by(month=month, year=year, status='Submitted').all()
    
    success_count = 0
    errors = []
    
    for pi in inputs:
        # Check if already processed/exists
        existing = SalaryRecord.query.filter_by(
            employee_id=pi.employee_id,
            month=pi.month,
            year=pi.year
        ).first()
        if existing:
            errors.append(f"Salary record already exists for employee ID {pi.employee_id}.")
            continue
            
        emp = pi.employee
        basic = emp.salary
        hra = basic * 0.4
        
        if pi.working_days and pi.working_days > 0:
            deductions = (basic / pi.working_days) * pi.leaves_taken
        else:
            deductions = 0.0
            
        basic = round(basic, 2)
        hra = round(hra, 2)
        deductions = round(deductions, 2)
        net_salary = round(basic + hra - deductions + (pi.bonus or 0.0), 2)
        
        salary_record = SalaryRecord(
            employee_id=pi.employee_id,
            month=pi.month,
            year=pi.year,
            basic=basic,
            hra=hra,
            deductions=deductions,
            net_salary=net_salary,
            status='Pending'
        )
        db.session.add(salary_record)
        pi.status = 'Processed'
        success_count += 1
        
    if success_count > 0:
        db.session.flush()
        log_audit(
            user_id=user_id,
            action='BULK_PROCESS_PAYROLL',
            entity_type='PayrollInput',
            entity_id=0,
            details=f"Bulk processed {success_count} payroll inputs for {month}/{year}",
            ip=ip_address
        )
        
    return success_count, errors


# ===========================================================================
# INVOICES SERVICES
# ===========================================================================

def get_invoices(filters=None, page=1, per_page=20):
    """Retrieve filtered, paginated invoices."""
    query = Invoice.query
    if filters:
        if filters.get('status'):
            query = query.filter(Invoice.status == filters['status'])
        if filters.get('client_name'):
            query = query.filter(Invoice.client_name.ilike(f"%{filters['client_name']}%"))
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(Invoice.issue_date >= date_from)
            except (ValueError, TypeError):
                pass
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(Invoice.issue_date <= date_to)
            except (ValueError, TypeError):
                pass
    return query.order_by(Invoice.issue_date.desc()).paginate(page=page, per_page=per_page, error_out=False)


def check_duplicate_invoice(invoice_number, exclude_id=None):
    """Check if an invoice number already exists."""
    query = Invoice.query.filter_by(invoice_number=invoice_number)
    if exclude_id:
        query = query.filter(Invoice.id != exclude_id)
    return query.first() is not None


def create_invoice(invoice_number, client_name, amount, issue_date, due_date, status, description, user_id, ip_address=''):
    """Create a new invoice and record audit log."""
    if check_duplicate_invoice(invoice_number):
        return None, "Invoice number already exists."
        
    invoice = Invoice(
        invoice_number=invoice_number,
        client_name=client_name,
        amount=amount,
        issue_date=issue_date or date.today(),
        due_date=due_date,
        status=status,
        description=description or ''
    )
    db.session.add(invoice)
    db.session.flush()
    
    log_audit(
        user_id=user_id,
        action='CREATE',
        entity_type='Invoice',
        entity_id=invoice.id,
        details=f"Created invoice {invoice_number} for {client_name} (₹{amount:.2f})",
        ip=ip_address
    )
    return invoice, None


def update_invoice(invoice_id, invoice_number, client_name, amount, issue_date, due_date, status, description, user_id, ip_address=''):
    """Update an existing invoice and record audit log."""
    if check_duplicate_invoice(invoice_number, exclude_id=invoice_id):
        return None, "Invoice number already exists."
        
    invoice = Invoice.query.get_or_404(invoice_id)
    old_number = invoice.invoice_number
    old_amount = invoice.amount
    
    invoice.invoice_number = invoice_number
    invoice.client_name = client_name
    invoice.amount = amount
    invoice.issue_date = issue_date or date.today()
    invoice.due_date = due_date
    invoice.status = status
    invoice.description = description or ''
    
    log_audit(
        user_id=user_id,
        action='UPDATE',
        entity_type='Invoice',
        entity_id=invoice.id,
        details=f"Updated invoice {old_number} (was ₹{old_amount:.2f}) -> {invoice_number} (now ₹{amount:.2f})",
        ip=ip_address
    )
    return invoice, None


# ===========================================================================
# SALARY RECORDS SERVICES
# ===========================================================================

def get_salaries(filters=None, page=1, per_page=20):
    """Retrieve filtered, paginated salary records ordered chronologically by year and month."""
    query = SalaryRecord.query.join(Employee)
    month_map = {
        'January': 1, 'February': 2, 'March': 3, 'April': 4,
        'May': 5, 'June': 6, 'July': 7, 'August': 8,
        'September': 9, 'October': 10, 'November': 11, 'December': 12
    }
    # SQLite/Dialect-safe ordering using case statement mapping
    case_stmt = db.case(whens={m: n for m, n in month_map.items()}, value=SalaryRecord.month, else_=0)
    
    if filters:
        if filters.get('status'):
            query = query.filter(SalaryRecord.status == filters['status'])
        if filters.get('employee_id'):
            query = query.filter(SalaryRecord.employee_id == filters['employee_id'])
        if filters.get('date_from'):
            try:
                date_from = datetime.strptime(filters['date_from'], '%Y-%m-%d').date()
                query = query.filter(
                    db.or_(
                        SalaryRecord.year > date_from.year,
                        db.and_(
                            SalaryRecord.year == date_from.year,
                            case_stmt >= date_from.month
                        )
                    )
                )
            except (ValueError, TypeError):
                pass
        if filters.get('date_to'):
            try:
                date_to = datetime.strptime(filters['date_to'], '%Y-%m-%d').date()
                query = query.filter(
                    db.or_(
                        SalaryRecord.year < date_to.year,
                        db.and_(
                            SalaryRecord.year == date_to.year,
                            case_stmt <= date_to.month
                        )
                    )
                )
            except (ValueError, TypeError):
                pass
    return query.order_by(SalaryRecord.year.desc(), case_stmt.desc()).paginate(page=page, per_page=per_page, error_out=False)


def create_salary(employee_id, month, year, basic, hra, deductions, status, user_id, ip_address=''):
    """Create a new salary record, computing net salary, and logging audit details."""
    net_salary = float(basic) + float(hra or 0) - float(deductions or 0)
    
    record = SalaryRecord(
        employee_id=employee_id,
        month=month,
        year=year,
        basic=basic,
        hra=hra or 0.0,
        deductions=deductions or 0.0,
        net_salary=net_salary,
        status=status
    )
    db.session.add(record)
    db.session.flush()
    
    log_audit(
        user_id=user_id,
        action='CREATE',
        entity_type='SalaryRecord',
        entity_id=record.id,
        details=f"Created salary record for employee ID {employee_id} ({month}/{year}, Net: ₹{net_salary:.2f})",
        ip=ip_address
    )
    return record


def update_salary(salary_id, month, year, basic, hra, deductions, status, user_id, ip_address=''):
    """Update an existing salary record (only allowed for Pending records)."""
    record = SalaryRecord.query.get_or_404(salary_id)
    if record.status != 'Pending':
        return None, f"Cannot edit a salary record with status '{record.status}'. Only Pending records can be edited."

    old_net = record.net_salary
    record.month = month
    record.year = year
    record.basic = float(basic)
    record.hra = float(hra or 0)
    record.deductions = float(deductions or 0)
    record.net_salary = record.basic + record.hra - record.deductions
    record.status = status

    log_audit(
        user_id=user_id,
        action='UPDATE',
        entity_type='SalaryRecord',
        entity_id=record.id,
        details=f"Updated salary record for employee ID {record.employee_id} ({month}/{year}) — Net changed from ₹{old_net:.2f} to ₹{record.net_salary:.2f}",
        ip=ip_address
    )
    return record, None


def process_salary(salary_id, user_id, ip_address=''):
    """Transition a salary record from Pending → Processed."""
    record = SalaryRecord.query.get_or_404(salary_id)
    if record.status != 'Pending':
        return None, f"Cannot process a salary record with status '{record.status}'. Only Pending records can be processed."

    record.status = 'Processed'
    log_audit(
        user_id=user_id,
        action='PROCESS_SALARY',
        entity_type='SalaryRecord',
        entity_id=record.id,
        details=f"Processed salary for {record.employee.user.full_name} ({record.month}/{record.year}), Net: ₹{record.net_salary:.2f}",
        ip=ip_address
    )

    # Notify the employee
    notif = Notification(
        user_id=record.employee.user_id,
        title='Salary Processed',
        message=f'Your salary for {record.month} {record.year} (₹{record.net_salary:,.2f}) has been processed and is awaiting payment.',
        category='info',
        link='/employee/salary'
    )
    db.session.add(notif)
    return record, None


def mark_salary_paid(salary_id, user_id, ip_address=''):
    """Transition a salary record from Processed → Paid."""
    record = SalaryRecord.query.get_or_404(salary_id)
    if record.status != 'Processed':
        return None, f"Cannot mark as paid a salary record with status '{record.status}'. Only Processed records can be marked paid."

    record.status = 'Paid'
    log_audit(
        user_id=user_id,
        action='MARK_PAID',
        entity_type='SalaryRecord',
        entity_id=record.id,
        details=f"Marked salary paid for {record.employee.user.full_name} ({record.month}/{record.year}), Net: ₹{record.net_salary:.2f}",
        ip=ip_address
    )

    # Notify the employee
    notif = Notification(
        user_id=record.employee.user_id,
        title='Salary Paid',
        message=f'Your salary for {record.month} {record.year} (₹{record.net_salary:,.2f}) has been credited.',
        category='success',
        link='/employee/salary'
    )
    db.session.add(notif)
    return record, None


def bulk_pay_salaries(month, year, user_id, ip_address=''):
    """Bulk mark all Processed salary records for a given month/year as Paid."""
    records = SalaryRecord.query.filter_by(month=month, year=year, status='Processed').all()
    if not records:
        return 0, "No processed salary records found for the selected month and year."

    count = 0
    for rec in records:
        rec.status = 'Paid'
        # Notify each employee
        notif = Notification(
            user_id=rec.employee.user_id,
            title='Salary Paid',
            message=f'Your salary for {rec.month} {rec.year} (₹{rec.net_salary:,.2f}) has been credited.',
            category='success',
            link='/employee/salary'
        )
        db.session.add(notif)
        count += 1

    db.session.flush()
    log_audit(
        user_id=user_id,
        action='BULK_PAY',
        entity_type='SalaryRecord',
        entity_id=0,
        details=f"Bulk marked {count} salary records as Paid for {month}/{year}",
        ip=ip_address
    )
    return count, None

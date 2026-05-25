# Phase 1: Fix Foundations (Finance Module)

This plan details the technical steps to extract business logic from the finance routes into a dedicated services layer, add explicit ORM relations, implement extensive audit logging and notifications, and introduce advanced query filtering and pagination to all finance views.

## User Review Required

> [!IMPORTANT]
> **No Database Migrations Required:** Adding the `submitter` relationship is handled at the SQLAlchemy ORM layer using the existing foreign key `submitted_by`. No changes to the database schema are required, making this a zero-downtime, safe change.

> [!NOTE]
> **ORM Alignment:** We will update both `app/models/finance.py` (defining `submitter` on `Expense`) and `app/models/core.py` (adjusting `User.expenses` to use `back_populates='submitter'`) to ensure a modern, clean bidirectional mapping without conflict warnings.

## Open Questions

*No critical open questions exist; requirements are fully aligned and conform to established patterns seen in the HR module (e.g., pagination template sharing and audit logs).*

---

## Proposed Changes

### 1. Database & ORM Layer

#### [MODIFY] [core.py](file:///c:/JGpc/app_at_present/app/models/core.py)
- Change `expenses = db.relationship('Expense', backref='submitter', foreign_keys='Expense.submitted_by')` to:
  `expenses = db.relationship('Expense', back_populates='submitter', foreign_keys='Expense.submitted_by')`

#### [MODIFY] [finance.py](file:///c:/JGpc/app_at_present/app/models/finance.py)
- Add explicit relationship in class `Expense`:
  `submitter = db.relationship('User', back_populates='expenses', foreign_keys=[submitted_by])`

---

### 2. Services Layer

#### [NEW] [services.py](file:///c:/JGpc/app_at_present/app/finance/services.py)
Implement standard plain-function service layer doing DB queries, mutations, logging, and notifications:
- **Expenses**:
  - `get_expenses(filters, page, per_page)`: handles querying with filters (date range, status, category) and paginates.
  - `create_expense(category, amount, date, description, user_id, ip)`: creates expense and logs audit action.
  - `update_expense(expense_id, category, amount, date, description, user_id, ip)`: updates expense and logs audit action.
  - `approve_expense(expense_id, user_id, ip)`: updates status to `Approved` and logs audit action.
  - `reject_expense(expense_id, user_id, ip)`: updates status to `Rejected` and logs audit action.
- **Employee Expenses Claims**:
  - `get_employee_expenses(filters, page, per_page)`: fetches employee expense claims with pagination/filters.
  - `approve_employee_expense(claim_id, user_id, ip)`: approves claim, creates audit log, and creates `Notification` to notify the employee user.
  - `reject_employee_expense(claim_id, user_id, ip)`: rejects claim, creates audit log, and creates `Notification` to notify the employee user.
- **Invoices**:
  - `get_invoices(filters, page, per_page)`: queries invoices with filters (date range, status, client name search) and paginates.
  - `create_invoice(...)` and `update_invoice(...)`: database operations for adding/editing invoices, preventing duplicate numbers, and logging audit entries.
- **Salary Records**:
  - `get_salaries(filters, page, per_page)`: queries salary records with filters (status, specific month/year, date range, employee) and paginates. Orders results chronologically by mapping month names to numbers in the database using `db.case()`.
  - `create_salary(...)`: records basic/hra/deductions, computes net salary, and logs audit.

---

### 3. Controller Layer

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/finance/routes.py)
- Refactor routes to call the services inside `app.finance.services` instead of performing DB transactions inline.
- Pass filter inputs from `request.args` (e.g. `date_from`, `date_to`, `status`, `category`, `client_name`, `employee_id`) and the current page to the service functions.
- Inject IP addresses (`request.remote_addr`) to all audit-logged actions.

---

### 4. Presentation & Template Layer

#### [MODIFY] [expenses.html](file:///c:/JGpc/app_at_present/app/templates/finance/expenses.html)
- Add filter card containing dropdowns for category and status, and date inputs for date range.
- Use paginated object `expenses.items` instead of the raw list, and include the shared `includes/pagination.html` template.

#### [MODIFY] [invoices.html](file:///c:/JGpc/app_at_present/app/templates/finance/invoices.html)
- Add status, date range, and client search filters.
- Support pagination.

#### [MODIFY] [salaries.html](file:///c:/JGpc/app_at_present/app/templates/finance/salaries.html)
- Add status, date range / month / year, and employee filters.
- Support pagination.

#### [MODIFY] [employee_expenses.html](file:///c:/JGpc/app_at_present/app/templates/finance/employee_expenses.html)
- Add status, category, date range, and employee filters.
- Support pagination.

---

### 5. Documentation Layer

#### [NEW] [manual_testing_finance_phase1.md](file:///c:/JGpc/app_at_present/manual_testing_finance_phase1.md)
- Provide step-by-step instructions to manually verify audit logs, notifications, filtering, pagination, and services functionality.

---

## Verification Plan

### Automated Tests
- We will execute the existing test suite (if present) to confirm no regressions are introduced:
  ```powershell
  pytest
  ```

### Manual Verification
1. **Expenses List & Action Verification**:
   - Create and edit an expense; verify the record in the UI.
   - Verify Audit Logs in Admin interface to see the corresponding `CREATE` and `UPDATE` records.
   - Approve / Reject an expense, verifying the state and the `APPROVE`/`REJECT` audit log.
2. **Employee Expense Claims Approval / Rejection Notification**:
   - As an employee, submit a claim (if routes exist).
   - As a finance user, approve/reject the claim.
   - Login as the employee and verify that a new system notification is displayed in the notifications list.
3. **Filtering**:
   - Test category filters, status filters, and date range filters (from/to) across all views.
4. **Pagination**:
   - Populate mock data (at least 21 items) to verify pagination links appear and display 20 items per page.

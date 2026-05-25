# 💰 Finance Module — Complete Overhaul Plan

## Current State Analysis

The Finance module is the **thinnest module** in the entire application (226 lines of routes, 50 lines of forms, 125 lines of models) — compared to HR (40K+ service lines), PM (12K+ models), and Employee (44K+ services). It's essentially a CRUD shell with no real financial logic.

### What Exists Today

| Feature | Status | Quality |
|---------|--------|---------|
| **Company Expenses** (CRUD + approve/reject) | ✅ Working | 🟡 Basic — no approval notes, no budget tracking, no categories analytics |
| **Employee Expense Claims** (review from finance) | ✅ Working | 🟡 Basic — no receipt viewer, no reimbursement tracking, no payment status |
| **Invoices** (CRUD with unique numbers) | ✅ Working | 🟡 Basic — no auto-numbering, no payment recording, no overdue alerts, no line items |
| **Salary Records** (manual entry) | ✅ Working | 🔴 Poor — completely disconnected from HR payroll pipeline |
| **Dashboard** (summary cards) | ✅ Working | 🟡 Basic — static numbers, no charts, no trends, no period filters |

### What's Broken or Missing

| # | Issue | Severity | Impact |
|---|-------|----------|--------|
| 1 | **HR Payroll → Finance salary pipeline is DISCONNECTED** | 🔴 Critical | HR submits PayrollInput, but Finance has NO route to consume/view it. Salary records are created manually from scratch. The entire `PayrollInput` workflow dead-ends. |
| 2 | **No receipt/attachment viewer** for employee expenses | 🔴 Critical | `receipt_filename` column exists but Finance has no route to download/preview receipts |
| 3 | **No reimbursement payment tracking** | 🟠 Major | Expense claims get Approved but there's no way to mark them as "Paid" / "Reimbursed" |
| 4 | **No salary edit/status workflow** | 🟠 Major | Salary records can only be added, never edited or moved through Pending→Processed→Paid |
| 5 | **No services layer** | 🟠 Major | Finance is the ONLY module with no `services.py` — all logic is in routes |
| 6 | **No audit logging** | 🟠 Major | Every other module logs actions to AuditLog. Finance does zero audit logging. |
| 7 | **No notifications** | 🟠 Major | Expense approval/rejection sends no notification to the employee who submitted it |
| 8 | **No filters/search** on any listing page | 🟡 Moderate | All pages dump all records with no date range, status, or category filters |
| 9 | **No pagination** | 🟡 Moderate | All queries use `.all()` — will break with real data volume |
| 10 | **Invoice has no payment recording** | 🟡 Moderate | Status can only be changed via edit form — no "Record Payment" action |
| 11 | **No overdue invoice detection** | 🟡 Moderate | Invoices past due_date don't auto-flag as Overdue |
| 12 | **No financial analytics/charts** | 🟡 Moderate | Every other module has analytics. Finance has none. |
| 13 | **No CSV/PDF export** | 🟡 Moderate | No export on any finance page |
| 14 | **No delete capability** | 🟢 Minor | No delete routes for expenses, invoices, or salary records |
| 15 | **`Expense.submitter` relationship missing in model** | 🟢 Minor | Template uses `exp.submitter.full_name` but model has no `submitter` relationship defined — likely relies on lazy backref from User |

---

## Ready-to-Use Prompt

> **Copy the prompt below and paste it to start implementation:**

---

```
I need you to do a complete overhaul of the Finance module in my Flask Enterprise Portal app.
The finance module is at `app/finance/` and its models are in `app/models/finance.py`.

Here's what I need you to build, phase by phase:

## PHASE 1 — Fix Foundations (Priority: Critical)
1. Create `app/finance/services.py` — extract all business logic from routes, add audit logging
2. Add `submitter` relationship to the Expense model in `app/models/finance.py`
3. Add audit logging to ALL finance actions (create/edit/approve/reject expenses, invoices, salary)
4. Add notifications when employee expense claims are approved/rejected (notify the employee)
5. Add filters (date range, status, category) to expenses list, invoices list, and salary records
6. Add pagination to all listing pages (20 items per page)

## PHASE 2 — HR → Finance Payroll Pipeline (Priority: Critical)
1. Build a route `GET /finance/payroll-inputs` to view all PayrollInput records submitted by HR (status='Submitted')
2. Build a route `POST /finance/payroll-inputs/<id>/process` to convert a PayrollInput into a SalaryRecord:
   - Auto-calculate: basic = employee.salary, HRA = salary * 0.4, deductions based on leaves_taken
   - Create the SalaryRecord with status='Pending'
   - Mark PayrollInput as 'Processed'
3. Build a route `POST /finance/payroll-inputs/bulk-process` to process all submitted payroll inputs for a given month/year at once
4. Add a "Payroll Pipeline" button to the finance dashboard quick actions
5. Create template `app/templates/finance/payroll_pipeline.html` with the payroll inputs table and process buttons

## PHASE 3 — Salary Record Enhancements (Priority: High)  
1. Add salary edit route `GET/POST /finance/salaries/<id>/edit`
2. Add salary status transition routes:
   - `POST /finance/salaries/<id>/process` (Pending → Processed)
   - `POST /finance/salaries/<id>/mark-paid` (Processed → Paid)
   - `POST /finance/salaries/bulk-pay` to mark all Processed records for a month as Paid
3. Add payslip generation: `GET /finance/salaries/<id>/payslip` renders a printable payslip view
4. Update `salaries.html` to show action buttons (Edit, Process, Mark Paid) based on current status
5. Add month/year filter to salary listing page

## PHASE 4 — Invoice Enhancements (Priority: High)
1. Add `InvoiceLineItem` model: invoice_id, description, quantity, unit_price, amount
2. Add `InvoicePayment` model: invoice_id, amount, payment_date, payment_method, reference_number, notes
3. Add `payment_received` (total payments), `balance_due` (amount - payment_received) computed properties to Invoice
4. Build route `POST /finance/invoices/<id>/record-payment` to record partial/full payments
5. Build route `GET /finance/invoices/<id>/detail` to show invoice detail with line items + payment history
6. Auto-detect overdue invoices: add a scheduled check or dashboard query that flags invoices past due_date as 'Overdue'
7. Add invoice delete route (only for Unpaid invoices with no payments)

## PHASE 5 — Employee Expense Enhancements (Priority: High)
1. Add receipt download/preview route: `GET /finance/employee-expenses/<id>/receipt`
2. Add reimbursement tracking: new columns `payment_status` (Unpaid/Paid), `paid_date`, `payment_reference`
3. Add route `POST /finance/employee-expenses/<id>/mark-paid` to mark approved expenses as reimbursed
4. Add rejection reason: add a modal or form field for rejection notes when rejecting claims
5. Add expense detail view: `GET /finance/employee-expenses/<id>` showing full details + receipt preview

## PHASE 6 — Analytics & Reporting Dashboard (Priority: Medium)
1. Add `GET /finance/analytics` route with:
   - Monthly expense trend chart (last 12 months)
   - Expense breakdown by category (pie chart)
   - Invoice collection rate (paid vs unpaid bar chart)
   - Monthly salary outflow trend
   - Cash flow summary (invoices collected − expenses − salaries)
2. Add `GET /finance/reports/profit-loss` — simple P&L statement for a given period
3. Add CSV export buttons on all listing pages (expenses, invoices, salaries, employee expenses)
4. Update finance dashboard to show period comparison (this month vs last month) and mini sparkline charts

## Cross-Module Integration Needed:
- **Employee module**: When finance approves/rejects an expense claim, send a Notification to the employee
- **HR module**: Add a "View in Finance" link on the HR payroll page once payroll inputs are submitted
- **Admin module**: Finance actions should appear in admin audit logs
- **Employee module**: Add payslip download button on employee payslip detail page (link to finance-generated payslip)

## Technical Requirements:
- Follow the existing pattern: Blueprint → routes.py → services.py → forms.py
- Use Flask-WTF forms for all data entry
- Add CSRF protection on all POST forms
- Use the existing `@module_required('finance')` decorator
- Log every action to AuditLog via services
- Use the existing Notification model for cross-module notifications
- All templates should extend `base.html` and use existing CSS classes (stat-card, data-card, badge-status, etc.)
- Add proper error handling and flash messages
- Use `db.session.query` for complex aggregations, not Python loops

Please implement these phases in order. After each phase, confirm the changes before moving to the next.
```

---

## Detailed Implementation Plan (File-by-File)

---

### Phase 1 — Fix Foundations

#### [NEW] [services.py](file:///c:/JGpc/app_at_present/app/finance/services.py)
- Extract business logic from routes into service functions
- `create_expense()`, `approve_expense()`, `reject_expense()`
- `create_invoice()`, `update_invoice()`
- `create_salary_record()`
- `log_audit()` wrapper — calls `AuditLog` for every finance action
- `notify_employee()` — creates Notification when expense claims are approved/rejected

#### [MODIFY] [finance.py](file:///c:/JGpc/app_at_present/app/models/finance.py)
- Add `submitter = db.relationship('User', foreign_keys=[submitted_by])` to `Expense` model
- Add `created_at` timestamp to Expense and Invoice models

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/finance/routes.py)
- Refactor to call `services.*` instead of inline DB logic
- Add `request.args` filters (date_from, date_to, status, category) to listing routes
- Add pagination using Flask-SQLAlchemy `.paginate()`
- Fix duplicate "Invoices" section comment (line 97 says "Invoices" but contains employee expenses)

#### [MODIFY] [expenses.html](file:///c:/JGpc/app_at_present/app/templates/finance/expenses.html)
- Add filter bar (date range picker, status dropdown, category dropdown)
- Add pagination controls

#### [MODIFY] [invoices.html](file:///c:/JGpc/app_at_present/app/templates/finance/invoices.html)
- Add filter bar (date range, status dropdown, client search)
- Add pagination controls

#### [MODIFY] [salaries.html](file:///c:/JGpc/app_at_present/app/templates/finance/salaries.html)
- Add month/year filter
- Add status filter
- Add pagination controls

---

### Phase 2 — HR → Finance Payroll Pipeline

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/finance/routes.py)
- Add `GET /payroll-inputs` — list PayrollInput records with status='Submitted'
- Add `POST /payroll-inputs/<id>/process` — convert PayrollInput → SalaryRecord
- Add `POST /payroll-inputs/bulk-process` — bulk convert for a month

#### [NEW] [payroll_pipeline.html](file:///c:/JGpc/app_at_present/app/templates/finance/payroll_pipeline.html)
- Table of submitted payroll inputs with employee name, month/year, working days, present days, overtime, bonus
- "Process" button per row, "Process All" bulk button
- Status badges showing which are already processed

#### [MODIFY] [dashboard.html](file:///c:/JGpc/app_at_present/app/templates/finance/dashboard.html)
- Add "Payroll Pipeline" quick action button
- Add "Pending Payroll" count stat card

---

### Phase 3 — Salary Record Enhancements

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/finance/routes.py)
- Add `GET/POST /salaries/<id>/edit`
- Add `POST /salaries/<id>/process` (Pending → Processed)
- Add `POST /salaries/<id>/mark-paid` (Processed → Paid)
- Add `POST /salaries/bulk-pay`
- Add `GET /salaries/<id>/payslip` — printable payslip view

#### [MODIFY] [salaries.html](file:///c:/JGpc/app_at_present/app/templates/finance/salaries.html)
- Add action column with Edit/Process/Mark Paid buttons (conditional on status)
- Add "Bulk Pay" button for month

#### [NEW] [payslip_view.html](file:///c:/JGpc/app_at_present/app/templates/finance/payslip_view.html)
- Printable payslip layout: company header, employee details, earnings breakdown, deductions, net salary

---

### Phase 4 — Invoice Enhancements

#### [MODIFY] [finance.py](file:///c:/JGpc/app_at_present/app/models/finance.py)
- Add `InvoiceLineItem` model: `id`, `invoice_id` (FK), `description`, `quantity`, `unit_price`, `amount`
- Add `InvoicePayment` model: `id`, `invoice_id` (FK), `amount`, `payment_date`, `payment_method`, `reference_number`, `notes`
- Add computed properties to Invoice: `total_paid`, `balance_due`

#### [MODIFY] [forms.py](file:///c:/JGpc/app_at_present/app/finance/forms.py)
- Add `PaymentForm`: amount, payment_date, payment_method (Bank Transfer/Cheque/Cash/UPI), reference_number, notes

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/finance/routes.py)
- Add `GET /invoices/<id>/detail` — full invoice detail view
- Add `POST /invoices/<id>/record-payment` — record payment
- Add `DELETE /invoices/<id>` — delete unpaid invoice with no payments
- Add overdue detection logic in dashboard query

#### [NEW] [invoice_detail.html](file:///c:/JGpc/app_at_present/app/templates/finance/invoice_detail.html)
- Invoice header (number, client, dates)
- Line items table
- Payment history table
- "Record Payment" form
- Balance due display

---

### Phase 5 — Employee Expense Enhancements

#### [MODIFY] [employee.py](file:///c:/JGpc/app_at_present/app/models/employee.py)
- Add to `EmployeeExpense`: `payment_status` (Unpaid/Paid), `paid_date`, `payment_reference`, `rejection_notes`

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/finance/routes.py)
- Add `GET /employee-expenses/<id>` — detail view with receipt preview
- Add `GET /employee-expenses/<id>/receipt` — serve receipt file for download
- Add `POST /employee-expenses/<id>/mark-paid` — mark as reimbursed
- Modify reject route to accept rejection_notes

#### [NEW] [employee_expense_detail.html](file:///c:/JGpc/app_at_present/app/templates/finance/employee_expense_detail.html)
- Full claim details (employee info, category, amount, description)
- Receipt image/PDF preview
- Approval/rejection history
- Reimbursement status

#### [MODIFY] [employee_expenses.html](file:///c:/JGpc/app_at_present/app/templates/finance/employee_expenses.html)
- Add "View Details" link per row
- Add payment status column
- Add filters (status, date range, employee search)

---

### Phase 6 — Analytics & Reporting

#### [MODIFY] [routes.py](file:///c:/JGpc/app_at_present/app/finance/routes.py)
- Add `GET /analytics` — aggregate queries for charts
- Add `GET /reports/profit-loss` — P&L summary
- Add `GET /export/<entity>` — CSV export for expenses, invoices, salaries, employee-expenses

#### [NEW] [analytics.html](file:///c:/JGpc/app_at_present/app/templates/finance/analytics.html)
- Monthly expense trend (line chart)
- Category breakdown (doughnut chart)
- Invoice collection rate (stacked bar)
- Salary outflow trend (area chart)
- Cash flow summary (revenue − expenses − salaries)

#### [NEW] [profit_loss.html](file:///c:/JGpc/app_at_present/app/templates/finance/profit_loss.html)
- Period selector (month/quarter/year)
- Revenue (paid invoices)
- Expenses (approved company expenses)
- Salaries (paid salary records)
- Employee reimbursements (paid expense claims)
- Net profit/loss

#### [MODIFY] [dashboard.html](file:///c:/JGpc/app_at_present/app/templates/finance/dashboard.html)
- Add "Analytics" quick action button
- Add mini sparkline charts in stat cards
- Add period comparison (vs last month)

---

### Cross-Module Changes

#### [MODIFY] Employee Module — [work_routes.py](file:///c:/JGpc/app_at_present/app/employee/routes/work_routes.py)
- Employee expense submission currently creates `Expense` (company expense) instead of `EmployeeExpense` — **this is a bug**. It should create `EmployeeExpense` linked to the employee.

#### [MODIFY] HR Module — [payroll_routes.py](file:///c:/JGpc/app_at_present/app/hr/routes/payroll_routes.py)
- After "Submit to Finance", show a status indicator and link to Finance's payroll pipeline page

---

## Open Questions

> [!IMPORTANT]
> **1. Employee expense bug**: The employee `submit_expense` route in [work_routes.py](file:///c:/JGpc/app_at_present/app/employee/routes/work_routes.py#L46-L71) creates an `Expense` (company-level expense) instead of an `EmployeeExpense` (employee reimbursement claim). Should I fix this? It means the Finance "Employee Expenses" page may be showing incomplete data — employee submissions land in the company expenses table instead.

> [!IMPORTANT]
> **2. Salary calculation formula**: For auto-generating salary records from payroll inputs, what salary structure should I use? Currently the form has Basic + HRA − Deductions. Should I add more components (DA, Special Allowance, PF, ESI, Professional Tax, TDS)?

> [!WARNING]
> **3. Database migration**: Several new models (InvoiceLineItem, InvoicePayment) and columns (EmployeeExpense.payment_status, etc.) will require a database migration. Since you're on SQLite, I can use Flask-Migrate or recreate the DB. Which do you prefer?

> [!IMPORTANT]
> **4. Phase priority**: Do you want me to implement all 6 phases, or start with specific phases? My recommendation is Phases 1→2→3 first (foundations + payroll pipeline + salary workflow), then 4→5→6.

---

## Verification Plan

### Automated Tests
- After each phase, verify all new routes return HTTP 200
- Test payroll pipeline: HR generates payroll → HR submits → Finance processes → SalaryRecord created
- Test expense workflow: Employee submits → Finance approves → Notification sent → Mark paid

### Manual Verification
- Log in as `finance_head` / `fin123` and verify all new pages
- Log in as employee, submit expense, then verify it appears in Finance module
- Verify audit logs capture all finance actions in Admin audit page
- Test CSV export downloads

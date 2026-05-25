# Phase 1: Fix Foundations — Manual Testing Guide

This document provides complete step-by-step testing instructions to manually verify all the features built during Phase 1 (Fix Foundations) of the Finance Module.

---

## Prerequisite: Logins & Navigation

1. Start the Flask application (it should be running on `http://127.0.0.1:5000` via `python app.py`).
2. Log in as an Administrator/Finance officer:
   - **Username/Email**: `admin` or a user configured with access to the **Finance** module.
3. Open the sidebar and click on **Finance** to access the Finance Dashboard.

---

## Test Scenario 1: Expense Operations & Audit Logging

### Step 1.1: Record a New Expense
1. From the Finance Dashboard, click the **Expenses** link in the navigation menu (or go to `/finance/expenses`).
2. Click the **Add Expense** button.
3. Complete the form:
   - **Category**: Select `Software`
   - **Amount**: Enter `15000`
   - **Date**: Select today's date
   - **Description**: Enter `Subscription for developer tools`
4. Click **Save Expense**.
5. **Expected Result**: You are redirected back to the Expenses list. A flash message says `Expense recorded.` and the new record is visible in the list.

### Step 1.2: Edit the Expense
1. Find the newly created expense in the list and click the **Edit** (pencil) icon under Actions.
2. Change the Amount to `18500` and append to the description: `(Upgraded plan)`.
3. Click **Save Expense**.
4. **Expected Result**: Redirected back to the Expenses list with a flash message saying `Expense updated.` and the amount reflects the updated ₹18,500.00.

### Step 1.3: Verify Audit Logs
1. Navigate to the Admin Panel (usually `/admin/config` or the Config/Audit Logs tab if available, or query the `audit_logs` table directly using SQLite).
2. **Expected Result**: Two new audit entries should exist for entity type `Expense`:
   - An entry for `CREATE` showing: `"Recorded expense of ₹15000.00 under Software"`
   - An entry for `UPDATE` showing: `"Updated expense from ₹15000.00 (Software) to ₹18500.00 (Software)"`
   - Both entries must capture your `user_id` and the client's `ip_address` correctly.

---

## Test Scenario 2: Expense Approval Workflow

1. Navigate to the **Expenses** list `/finance/expenses`.
2. Locate a `Pending` expense record.
3. Click the **Approve** (green checkmark) button.
4. **Expected Result**: The status badge immediately updates to `Approved` and the action buttons vanish. An audit entry with action `APPROVE` and entity `Expense` is logged.
5. Record another expense and click the **Reject** (red cross) button.
6. **Expected Result**: The status badge immediately updates to `Rejected`. An audit entry with action `REJECT` and entity `Expense` is logged.

---

## Test Scenario 3: Employee Expense Claims & Notifications

### Step 3.1: Submit Employee Claim (As Employee)
1. Log out, then log in as a standard Employee user (or navigate directly to `/employee/expenses/submit`).
2. Click **Submit Expense Claim** or complete the claim form:
   - **Category**: Select `Travel`
   - **Amount**: Enter `3500`
   - **Description**: Enter `Client meeting travel fare`
3. Submit the claim.

### Step 3.2: Review & Approve Claim (As Finance User)
1. Log out, then log back in as the Administrator/Finance user.
2. Navigate to **Employee Expenses** in the Finance section (`/finance/employee-expenses`).
3. Locate the employee's claim (Status: `Pending`).
4. Click the **Approve** (check) button.
5. **Expected Result**: Redirected with a `Employee expense claim approved.` flash message. Status changes to `Approved`.
6. An audit entry with action `APPROVE` and entity `EmployeeExpense` is recorded with current user ID and IP address.

### Step 3.3: Verify Employee Notification
1. Log out, and log back in as the Employee who submitted the claim.
2. Look at the top navigation bar or the notification bell.
3. **Expected Result**: A new notification will be visible:
   - **Title**: `Expense Claim Approved`
   - **Message**: `Your expense claim of ₹3,500.00 for category "Travel" has been approved.`
   - **Action**: Clicking on the notification redirects you to `/employee/expenses`.

---

## Test Scenario 4: Invoice Creation & Duplicate Protection

### Step 4.1: Create a New Invoice
1. Navigate to the **Invoices** list (`/finance/invoices`).
2. Click the **New Invoice** button.
3. Enter Details:
   - **Invoice Number**: `INV-2026-001`
   - **Client**: `Acme Corp`
   - **Amount**: `250000`
   - **Issue Date**: Select today
   - **Status**: `Unpaid`
4. Click **Save Invoice**.
5. **Expected Result**: Invoice is created, a flash message shows `Invoice INV-2026-001 created.`, and a `CREATE` audit log for the `Invoice` is recorded.

### Step 4.2: Test Duplicate Validation
1. Click **New Invoice** again.
2. Enter the same Invoice Number: `INV-2026-001`.
3. Fill in other fields and click **Save Invoice**.
4. **Expected Result**: The form fails with a flash message: `Invoice number already exists.` and does not write to the database.

---

## Test Scenario 5: Salary Recording & Net Compiling

1. Navigate to the **Salary Records** list (`/finance/salaries`).
2. Click **Add Record**.
3. Select an Employee from the dropdown.
4. Set Month: `May`, Year: `2026`.
5. Enter:
   - **Basic**: `50000`
   - **HRA**: `20000`
   - **Deductions**: `5000`
6. Click **Save Record**.
7. **Expected Result**: The page redirects to the list. The new salary record is displayed.
   - The Net Salary is compiled automatically: `50000 + 20000 - 5000 = ₹65,000`.
   - A `CREATE` audit log for `SalaryRecord` is added to the database.

---

## Test Scenario 6: Advanced Filters & Query Logic

On each list view, verify the search filters:
1. **Expenses List (`/finance/expenses`)**:
   - Filter by **Category** (e.g. choose `Software`). Confirm only `Software` records remain.
   - Filter by **Status** (e.g. choose `Pending`).
   - Filter by **From/To dates**. Choose a range that excludes some records and verify they disappear.
2. **Invoices List (`/finance/invoices`)**:
   - Search by **Client Name** (e.g. enter `Acme`).
   - Filter by **Status** and **Date Range**.
3. **Salary Records (`/finance/salaries`)**:
   - Filter by **Employee** and **Status**.
   - Filter by **From/To dates** (this maps month names to integer dates dynamically in SQLite). Verify records outside the range are filtered out.

---

## Test Scenario 7: Pagination Verification

1. Navigate to any finance listing page.
2. **Expected Result**: A maximum of 20 records is displayed per page.
3. If there are more than 20 records in the database, a small pagination control block (with Previous, Next, Page Numbers) appears at the bottom.
4. Click on **Page 2** or **Next** to confirm items flow correctly and maintain filter parameters in their URL query string.

# Manual Testing Guide — Phase 3: Salary Record Enhancements

> **Module**: Finance → Salary Records  
> **URL Base**: `http://localhost:5000/finance/salaries`  
> **Login Required**: Finance Manager / System Admin  

---

## Prerequisites

| Step | Action |
|------|--------|
| 1 | Ensure the application is running (`python app.py`) |
| 2 | Log in as **Finance Head** → Username: `finance_head`, Password: `Finance_head@123` (or **Admin** → `admin` / `Admin@123`) |
| 3 | From the left sidebar, navigate to **Finance → Salary Records** (or go to `/finance/salaries`) |
| 4 | Ensure at least one salary record exists with status **Pending**. If none exist, first process a payroll input from the Payroll Pipeline (Phase 2), or click **Add Record** to create one manually |

---

## Test Scenario 1: Edit a Pending Salary Record

### Step 1.1: Navigate to Edit

1. On the Salary Records page, locate a record with status **Pending** (shown as a yellow badge).
2. In the **Actions** column for that record, you should see three buttons:
   - 📄 **Payslip** (blue outline — always visible)
   - ✏️ **Edit** (yellow/orange outline — only for Pending)
   - ✅ **Process** (teal outline — only for Pending)
3. Click the **Edit** (pencil) icon.
4. **Expected Result**: You are taken to the **Edit Salary Record** page with the form pre-filled with the record's current values. The **Employee** dropdown is disabled (greyed out) because the employee cannot be changed.

### Step 1.2: Modify the Record

1. Change the **Basic Pay** to `45000`.
2. Change the **HRA** to `18000`.
3. Change the **Deductions** to `3000`.
4. Observe the **Net Salary** field at the bottom — it should auto-calculate to **₹60,000.00** (45000 + 18000 − 3000) in real-time as you type.
5. Click **Save Record**.
6. **Expected Result**: 
   - Redirected to the Salary Records list.
   - A flash message says: **`Salary record updated.`**
   - The row now shows the updated Basic (₹45,000), HRA (₹18,000), Deductions (₹3,000), and Net Salary (₹60,000).

### Step 1.3: Verify Edit is Blocked for Non-Pending Records

1. Find a record with status **Processed** or **Paid**.
2. Confirm that the **Edit (pencil) button is NOT visible** in the Actions column for these records.
3. **Additionally**: Try navigating directly to `/finance/salaries/<id>/edit` in the browser address bar using the ID of a Processed or Paid record.
4. **Expected Result**: You are redirected back to the Salary Records list with a red flash message: **`Cannot edit a salary record with status 'Processed'. Only Pending records can be edited.`**

---

## Test Scenario 2: Process a Salary Record (Pending → Processed)

### Step 2.1: Process a Single Record

1. On the Salary Records page, find a record with status **Pending**.
2. In the **Actions** column, click the **Process** button (✅ check icon, teal outline).
3. A browser confirmation dialog appears: **"Mark this salary as Processed?"**
4. Click **OK** to confirm.
5. **Expected Result**:
   - Redirected back to the Salary Records list.
   - Flash message: **`Salary for [Employee Name] marked as Processed.`**
   - The record's status badge now shows **Processed** (blue badge).
   - The **Edit** and **Process** buttons are no longer visible for this record.
   - A new **Mark Paid** button (💰 coins icon, green outline) now appears in the Actions column.

### Step 2.2: Verify Employee Notification

1. Log out of the Finance account.
2. Log in as the employee whose salary was just processed (e.g., `john_doe` / `John_doe@123`).
3. Check the **Notifications** bell icon in the top navigation bar.
4. **Expected Result**: A notification appears:
   - **Title**: `Salary Processed`
   - **Message**: `Your salary for [Month] [Year] (₹XX,XXX.XX) has been processed and is awaiting payment.`

---

## Test Scenario 3: Mark a Salary as Paid (Processed → Paid)

### Step 3.1: Mark Individual Record as Paid

1. Log back in as `finance_head` (or `admin`).
2. Navigate to **Finance → Salary Records** (`/finance/salaries`).
3. Find a record with status **Processed** (blue badge).
4. In the **Actions** column, click the **Mark Paid** button (💰 coins icon, green outline).
5. A browser confirmation dialog appears: **"Mark this salary as Paid?"**
6. Click **OK** to confirm.
7. **Expected Result**:
   - Redirected back to the Salary Records list.
   - Flash message: **`Salary for [Employee Name] marked as Paid.`**
   - The record's status badge now shows **Paid** (green badge).
   - The Actions column shows only the **Payslip** button and a "✓ Completed" label.

### Step 3.2: Verify Employee Notification

1. Log out and log in as the employee whose salary was marked paid.
2. Check the **Notifications** bell icon.
3. **Expected Result**: A notification appears:
   - **Title**: `Salary Paid`
   - **Message**: `Your salary for [Month] [Year] (₹XX,XXX.XX) has been credited.`

---

## Test Scenario 4: Bulk Pay All Processed Records

### Step 4.1: Prepare Multiple Processed Records

1. Log in as `finance_head` (or `admin`).
2. Ensure there are **at least 2 salary records** with status **Processed** for the **same month and year** (e.g., May 2026).
   - If needed, create or process additional records from the Payroll Pipeline or by adding manually and then processing them.

### Step 4.2: Bulk Pay

1. On the Salary Records page, locate the **Bulk Pay** form section (below the search filters).
2. Select the **Month** (e.g., `May`) from the dropdown.
3. Enter the **Year** (e.g., `2026`).
4. Click the **Bulk Pay All Processed** button (green).
5. A browser confirmation dialog appears: **"Are you sure you want to mark ALL Processed salary records for this month/year as Paid?"**
6. Click **OK** to confirm.
7. **Expected Result**:
   - Redirected back to the Salary Records list.
   - Flash message: **`Successfully marked X salary records as Paid for May 2026.`**
   - All previously Processed records for that month/year now show status **Paid** (green badge).

### Step 4.3: Bulk Pay — No Records Found

1. Select a **Month** and **Year** that has no Processed records (e.g., `January 2025`).
2. Click **Bulk Pay All Processed**.
3. **Expected Result**: A yellow/orange warning flash message: **`No processed salary records found for the selected month and year.`**

---

## Test Scenario 5: View & Print Payslip

### Step 5.1: Open a Payslip

1. On the Salary Records page, find **any** salary record (Pending, Processed, or Paid).
2. Click the **Payslip** button (📄 document icon, blue outline) in the Actions column.
3. **Expected Result**: A **new browser tab** opens with a professional payslip document containing:

| Section | Expected Content |
|---------|-----------------|
| **Header** | Company name ("Enterprise Portal"), "PAYSLIP" label, Month/Year, Status badge |
| **Employee Details** | Employee Name, Employee Code, Department, Designation, Bank Account, PAN |
| **Earnings** | Basic Pay, HRA, Total Earnings |
| **Deductions** | Deductions amount, Total Deductions |
| **Net Salary** | Large highlighted box showing the net payable amount |
| **Footer** | "This is a system-generated payslip and does not require a signature." |

### Step 5.2: Print the Payslip

1. On the payslip page, click the **Print Payslip** button at the bottom.
2. **Expected Result**: The browser's print dialog opens. The payslip is formatted cleanly for printing — the print/close buttons are hidden, and the gradient colors are preserved.

---

## Test Scenario 6: Verify Status Transition Rules

This scenario tests that the system correctly prevents invalid status transitions.

| Action Attempted | Current Status | Expected Result |
|-----------------|----------------|-----------------|
| Edit | Pending | ✅ Allowed — form opens |
| Edit | Processed | ❌ Blocked — redirect with error flash |
| Edit | Paid | ❌ Blocked — redirect with error flash |
| Process | Pending | ✅ Allowed — transitions to Processed |
| Process | Processed | ❌ Blocked — error flash message |
| Process | Paid | ❌ Blocked — error flash message |
| Mark Paid | Pending | ❌ Blocked — error flash message |
| Mark Paid | Processed | ✅ Allowed — transitions to Paid |
| Mark Paid | Paid | ❌ Blocked — error flash message |
| View Payslip | Any | ✅ Always allowed |

To manually test blocked transitions, try accessing the URLs directly in the address bar:
- `POST /finance/salaries/<id>/process` (use a form or browser extension to send POST)
- `POST /finance/salaries/<id>/mark-paid`

---

## Test Scenario 7: Verify Audit Logs

1. After performing Edit, Process, and Mark Paid actions above, navigate to the Admin Panel audit logs (usually `/admin/config` or query the `audit_logs` table directly using SQLite).
2. **Expected Result**: New audit entries exist for entity type `SalaryRecord`:

| Action | Expected Detail Message |
|--------|------------------------|
| `UPDATE` | `"Updated salary record for employee ID X (...) — Net changed from ₹... to ₹..."` |
| `PROCESS_SALARY` | `"Processed salary for [Name] (Month/Year), Net: ₹..."` |
| `MARK_PAID` | `"Marked salary paid for [Name] (Month/Year), Net: ₹..."` |
| `BULK_PAY` | `"Bulk marked N salary records as Paid for Month/Year"` |

All entries must capture the `user_id` and `ip_address` correctly.

---

## Quick Reference — Action Buttons Per Status

| Status | Edit ✏️ | Process ✅ | Mark Paid 💰 | Payslip 📄 | Label |
|--------|---------|-----------|-------------|-----------|-------|
| **Pending** | ✅ | ✅ | ❌ | ✅ | — |
| **Processed** | ❌ | ❌ | ✅ | ✅ | — |
| **Paid** | ❌ | ❌ | ❌ | ✅ | ✓ Completed |

---

## Login Credentials for Testing

| Role | Username | Password |
|------|----------|----------|
| Finance Head | `finance_head` | `Finance_head@123` |
| System Admin | `admin` | `Admin@123` |
| Standard Employee | `john_doe` | `John_doe@123` |

# Phase 2: HR → Finance Payroll Pipeline — Manual Testing Guide

This document provides step-by-step testing instructions to manually verify the HR-to-Finance Payroll Pipeline features implemented during Phase 2.

---

## Scenario A: HR Generates & Submits Payroll (As HR Manager)

1. Start the Flask application (ensure it's running on `http://127.0.0.1:5000` via `python app.py`).
2. Log in as the HR Manager:
   - **Username**: `hr_manager`
   - **Password**: `Hr_manager@123`
3. In the sidebar, navigate to **HR** space, then click **Payroll Inputs** (or go directly to `/hr/payroll-inputs` if the link is available).
4. Click **Generate Payroll Inputs** for **May 2026** (or select the current month/year).
5. Verify that draft inputs are generated for all active employees.
6. Review the draft inputs (e.g. adjust a bonus or add deduction notes for a specific employee if needed).
7. Select the generated inputs and click the **Submit to Finance** button.
   - **Expected Result**: The status of these inputs transitions from `Draft` to `Submitted`. A success message states that the payroll inputs have been submitted to the Finance department.
8. Log out.

---

## Scenario B: Process Payroll & Verify Calculations (As Finance Head)

1. Log in as the Finance Head:
   - **Username**: `finance_head`
   - **Password**: `Finance_head@123`
2. On the **Finance Dashboard** (`/finance/`):
   - **Expected Result**: A new **Pending Payroll** stat card is visible showing the number of payroll inputs waiting to be processed (e.g., `9 pending`).
   - A new quick action button **Payroll Pipeline** is visible in the Quick Actions card.
3. Click the **Payroll Pipeline** button (or navigate directly to `/finance/payroll-inputs`).
   - **Expected Result**: You are redirected to the **Payroll Pipeline** page displaying the table of submitted inputs.

### Step B.1: Process a Single Employee Claim
1. Locate **John Doe (EMP004)** in the list.
2. Verify his stats (e.g., Working Days, leaves taken, any bonus).
3. Click the **Process** button in his row.
4. **Expected Result**: 
   - A success message appears: `Salary record created for John Doe.`
   - John Doe's row vanishes from the pending pipeline (or its status badge updates to `Processed`).
   - Go to **Salary Records** (`/finance/salaries`) in the sidebar.
   - Confirm a new record exists for John Doe (May 2026) with status **Pending**.
   - Check the calculations:
     - **Basic**: Should match John Doe's base salary (₹70,000.00).
     - **HRA**: Should be exactly 40% of his basic (₹28,000.00).
     - **Deductions**: Calculated based on leaves taken: `(basic / working_days) * leaves_taken`. (e.g., if he took 2 days leave with 22 working days: `(70000 / 22) * 2 = ₹6,363.64`).
     - **Net Salary**: `Basic + HRA - Deductions` should compile perfectly.

---

## Scenario C: Bulk Processing Verification

1. Go back to the **Payroll Pipeline** page (`/finance/payroll-inputs`).
2. Verify that the remaining employees are still listed as `Submitted`.
3. Locate the **Process All** button at the top of the card or page.
4. Click **Process All**.
5. **Expected Result**:
   - The page reloads with a success message: `Successfully bulk-processed X payroll inputs.`
   - The table is now empty (or shows "No pending payroll inputs to process").
   - Go to **Salary Records** (`/finance/salaries`) and confirm that all remaining employees now have a `Pending` salary record generated automatically with exact calculations.
6. Verify that an audit log entry was created:
   - Run a query or view the Admin Panel's Config page. Two `CREATE` and `BULK_PROCESS_PAYROLL` logs should be recorded with correct metadata.

# Phase 5: Employee Expense Enhancements — Manual Testing Guide

This document provides step-by-step testing instructions to manually verify the Employee Expense Enhancement features implemented during Phase 5.

---

## Prerequisites

1. Start the Flask application (ensure it's running on `http://127.0.0.1:5000` via `python app.py`).
2. You will need two accounts:
   - **Finance Head**: `finance_head` / `Finance_head@123`
   - **Employee**: Any employee account that can submit expense claims
3. Ensure at least one employee expense claim exists. If not, log in as an employee and submit one via **Employee Portal → Submit Expense** with a receipt attachment (image or PDF).

---

## Scenario A: Employee Expenses List — New Columns & Filters

1. Log in as **Finance Head**.
2. Navigate to **Finance → Employee Expenses** (`/finance/employee-expenses`).
3. **Expected Result**:
   - The table now has **8 columns**: Employee, Category, Amount, Date, Description, Status, **Payment**, Actions.
   - Each row has a **View Details** (eye icon) link in the Actions column.
   - For claims with status `Approved`, the **Payment** column shows either a `Unpaid` or `Paid` badge.
   - For claims with status `Pending` or `Rejected`, the Payment column shows `—`.

---

## Scenario B: Employee Search Filter

1. On the **Employee Expenses** page (`/finance/employee-expenses`):
2. In the **Employee Search** text input, type part of an employee's name (e.g., `Rag`) or employee code (e.g., `EMP`).
3. Click the **search icon** button.
4. **Expected Result**:
   - Only expense claims from employees whose name or code matches the search term are displayed.
   - The search input retains the entered value after the page reloads.
5. Click **Clear** to reset all filters.
6. **Expected Result**: All claims are shown again, all filter fields are cleared.

---

## Scenario C: Payment Status Filter

1. On the **Employee Expenses** page:
2. Set the **Payment** dropdown to `Unpaid` and click search.
3. **Expected Result**: Only claims with `payment_status = Unpaid` are shown (these will be Approved but not yet reimbursed, or Pending/Rejected claims with default Unpaid status).
4. Change the **Payment** dropdown to `Paid` and click search.
5. **Expected Result**: Only claims that have been marked as reimbursed are shown (if any exist at this point — likely none yet).

---

## Scenario D: View Details — Detail Page

1. On the **Employee Expenses** page, locate any expense claim.
2. Click the **eye icon** (View Details) in the Actions column.
3. **Expected Result**:
   - You are redirected to the **Employee Expense Detail** page (`/finance/employee-expenses/<id>`).
   - The page shows:
     - **Header**: Category + "Expense" title, employee name/code, and status badge(s).
     - **Summary Row**: Claim Amount (₹), Category (with icon), Expense Date, and Submitted On timestamp.
     - **Description**: If provided, shown in a light grey box.
     - **Employee Information Card**: Full Name, Employee Code, Department, and Designation.
     - **Approval History**: A timeline starting with "Submitted" entry.
   - A **Back to Employee Expenses** button at the top.

---

## Scenario E: Receipt Preview & Download

1. Navigate to the detail page of a claim that has a **receipt attached** (an image or PDF file).
2. **Expected Result**:
   - A **Receipt / Attachment** card is displayed.
   - If the receipt is an **image** (JPG, PNG, etc.), an inline image preview is shown.
   - If the receipt is a **PDF**, an inline PDF viewer (iframe) is shown.
   - For other file types, a "Preview not available" message is shown.
   - A **Download** button is visible in the card header.
3. Click the **Download** button.
4. **Expected Result**:
   - The browser downloads the receipt file with its original filename.

---

## Scenario F: Receipt Download — No Receipt Attached

1. Navigate to the detail page of a claim that has **no receipt** attached.
2. **Expected Result**:
   - The **Receipt / Attachment** card is **not displayed**.
3. Manually visit the receipt URL: `/finance/employee-expenses/<id>/receipt` for this claim.
4. **Expected Result**:
   - A warning flash message: `No receipt attached to this claim.`
   - You are redirected back to the detail page.

---

## Scenario G: Approve an Expense Claim (from Detail Page)

1. Navigate to the detail page of a **Pending** expense claim.
2. **Expected Result**:
   - A **Review Actions** card is visible with Edit, Approve, and Reject buttons.
3. Click **Approve**.
4. A browser confirmation dialog appears.
5. Click **OK**.
6. **Expected Result**:
   - A success message: `Employee expense claim approved.`
   - The page reloads and shows:
     - **Status**: `Approved` (green badge).
     - **Payment Status**: `Unpaid` badge appears below the Approved badge.
     - **Approval History** timeline: Now shows both "Submitted" and "Approved" entries with reviewer name and timestamp.
     - The **Review Actions** card is **no longer visible**.
     - A new **Mark as Reimbursed** card appears with a payment reference input and "Mark as Paid" button.

---

## Scenario H: Reject an Expense Claim (with Rejection Notes)

1. Navigate to the detail page of a **Pending** expense claim.
2. Click **Reject**.
3. **Expected Result**: A modal dialog opens titled "Reject Expense Claim".
   - It shows the claim amount and employee name.
   - It has a **Rejection Reason** textarea.
4. Enter a rejection reason, e.g., `Receipt is illegible. Please resubmit with a clearer copy.`
5. Click **Confirm Rejection**.
6. **Expected Result**:
   - A warning message: `Employee expense claim rejected.`
   - The page reloads and shows:
     - **Status**: `Rejected` (red badge).
     - **Approval History** timeline: Shows "Submitted" and "Rejected" entries.
     - The **Rejected** entry includes a **red callout box** displaying: `Rejection Reason: Receipt is illegible. Please resubmit with a clearer copy.`
     - The **Review Actions** card is **no longer visible**.
     - The **Mark as Reimbursed** card is **not visible** (only shown for Approved claims).

---

## Scenario I: Reject Without Reason

1. Navigate to the detail page of another **Pending** expense claim.
2. Click **Reject**.
3. Leave the **Rejection Reason** textarea **empty**.
4. Click **Confirm Rejection**.
5. **Expected Result**:
   - The claim is rejected successfully (rejection notes are optional).
   - The Approval History shows "Rejected" but **no** rejection reason callout box.

---

## Scenario J: Mark Expense as Reimbursed

1. Navigate to the detail page of an **Approved** claim with `Unpaid` payment status.
2. **Expected Result**: The **Mark as Reimbursed** card is visible with:
   - A label showing `Awaiting Reimbursement: ₹XX,XXX.XX`.
   - A **Payment Reference** text input.
   - A **Mark as Paid** button.
3. Enter a payment reference: `TXN-2026-0601` and click **Mark as Paid**.
4. A browser confirmation dialog appears showing the claim amount.
5. Click **OK**.
6. **Expected Result**:
   - A success message: `Expense claim for <employee name> marked as reimbursed.`
   - The page reloads and shows:
     - **Payment Status**: Changes to `Paid` (green badge) below the `Approved` badge.
     - **Approval History** timeline: Now shows three entries — Submitted → Approved → Reimbursed.
     - The **Reimbursed** entry shows the date and **Reference: `TXN-2026-0601`**.
     - The **Mark as Reimbursed** card is **no longer visible**.

---

## Scenario K: Mark Paid — Without Reference

1. Navigate to the detail page of another **Approved + Unpaid** claim.
2. Leave the **Payment Reference** field empty and click **Mark as Paid**.
3. **Expected Result**:
   - The claim is marked as paid successfully (payment reference is optional).
   - The Reimbursed timeline entry does **not** show a reference line.

---

## Scenario L: Mark Paid — Protection Against Double Payment

1. Navigate to the detail page of a claim already marked as **Paid** (from Scenario J).
2. **Expected Result**:
   - The **Mark as Reimbursed** card is **not visible**.
   - The Payment Status badge shows `Paid`.
3. Manually POST to `/finance/employee-expenses/<id>/mark-paid` (e.g., via browser dev tools or curl).
4. **Expected Result**:
   - A danger flash message: `This claim has already been marked as paid.`

---

## Scenario M: Mark Paid — Only for Approved Claims

1. Navigate to the detail page of a **Rejected** claim.
2. **Expected Result**: The **Mark as Reimbursed** card is **not visible**.
3. Manually POST to `/finance/employee-expenses/<id>/mark-paid`.
4. **Expected Result**:
   - A danger flash message: `Cannot mark as paid — claim status is 'Rejected'. Only Approved claims can be reimbursed.`

---

## Scenario N: Employee Notification Verification

1. Log in as the **employee** whose claims were approved, rejected, and reimbursed in the scenarios above.
2. Check the **Notifications** panel.
3. **Expected Result** — the following notifications should be present:
   - `Expense Claim Approved` — for the approved claim.
   - `Expense Claim Rejected` — for the rejected claim(s), including rejection reason if provided.
   - `Expense Reimbursed` — for the paid claim, including payment reference if provided.

---

## Scenario O: Audit Log Verification

1. Log in as an **Admin** user and navigate to the Admin audit logs.
2. **Expected Result**: The following audit entries should be recorded from the tests above:
   - `APPROVE` entries for `EmployeeExpense` with reviewer details.
   - `REJECT` entries for `EmployeeExpense` with rejection reason in the details (if provided).
   - `MARK_PAID` entries for `EmployeeExpense` with payment reference in the details (if provided).
   - All entries include correct metadata (user ID, IP address, entity type, entity ID, and description).

---

## Scenario P: List Page — Payment Column After Reimbursement

1. Log in as **Finance Head** and navigate to **Finance → Employee Expenses**.
2. **Expected Result**:
   - The claim from Scenario J now shows a **`Paid`** badge in the Payment column.
   - Other Approved claims still show **`Unpaid`** in the Payment column.
   - Pending and Rejected claims show **`—`** in the Payment column.
3. Use the **Payment** filter dropdown to select `Paid`.
4. **Expected Result**: Only the reimbursed claim(s) appear in the filtered results.

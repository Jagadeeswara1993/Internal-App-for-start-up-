# Phase 4: Invoice Enhancements — Manual Testing Guide

This document provides step-by-step testing instructions to manually verify the Invoice Enhancement features implemented during Phase 4.

---

## Prerequisites

1. Start the Flask application (ensure it's running on `http://127.0.0.1:5000` via `python app.py`).
2. Log in as the Finance Head:
   - **Username**: `finance_head`
   - **Password**: `Finance_head@123`

---

## Scenario A: Invoice Detail View

1. Navigate to **Finance → Invoices** (`/finance/invoices`).
2. Locate any invoice in the list (e.g., `INV-2026-001`).
3. Click the **eye icon** (View Details) in the Actions column.
4. **Expected Result**:
   - You are redirected to the **Invoice Detail** page (`/finance/invoices/<id>/detail`).
   - The page shows:
     - **Header**: Invoice number, client name, and status badge.
     - **Summary Row**: Invoice Amount, Total Paid (₹0.00 initially), Balance Due (equals Invoice Amount), and Issue/Due dates.
     - **Line Items Table**: Either lists existing line items or shows "No line items added for this invoice."
     - **Payment History Table**: Shows "No payments recorded yet."
     - **Record New Payment Form**: A form with Amount, Payment Date, Payment Method, Reference No., and Notes fields.
     - **Action Buttons**: Edit Invoice and Delete Invoice buttons at the bottom.

---

## Scenario B: Record a Partial Payment

1. On the **Invoice Detail** page for an Unpaid invoice (e.g., `INV-2026-001` with amount ₹250,000):
2. In the **Record New Payment** form:
   - **Amount**: Enter `100000` (₹1,00,000)
   - **Payment Date**: Select today's date
   - **Payment Method**: Select `Bank Transfer`
   - **Reference No.**: Enter `TXN-2026-0501`
   - **Notes**: Enter `First partial payment`
3. Click **Record Payment**.
4. **Expected Result**:
   - A success message: `Payment of ₹1,00,000.00 recorded successfully.`
   - The page reloads and shows:
     - **Total Paid**: ₹1,00,000.00
     - **Balance Due**: ₹1,50,000.00
     - **Status**: Still `Unpaid` (partial payment)
     - **Payment History Table**: Shows 1 row with the payment details (date, Bank Transfer, TXN-2026-0501, ₹1,00,000.00, "First partial payment").
   - The **Record New Payment** form is still visible (since balance > 0).

---

## Scenario C: Record Final Payment (Full Settlement)

1. Still on the same invoice detail page:
2. In the **Record New Payment** form:
   - **Amount**: Enter `150000` (₹1,50,000 — the remaining balance)
   - **Payment Date**: Select today's date
   - **Payment Method**: Select `UPI`
   - **Reference No.**: Enter `UPI-REF-9876`
   - **Notes**: Enter `Final settlement`
3. Click **Record Payment**.
4. **Expected Result**:
   - A success message: `Payment of ₹1,50,000.00 recorded successfully.`
   - The page reloads and shows:
     - **Total Paid**: ₹2,50,000.00
     - **Balance Due**: ₹0.00
     - **Status**: Automatically updated to **`Paid`** (green badge).
     - **Payment History Table**: Shows 2 rows with both payment records.
   - The **Record New Payment** form is **no longer visible** (invoice is fully paid).

---

## Scenario D: Payment Validation — Overpayment Prevention

1. Navigate to a different Unpaid invoice (e.g., `INV-2026-002` with amount ₹1,50,000).
2. Go to its Detail page.
3. In the **Record New Payment** form:
   - **Amount**: Enter `200000` (₹2,00,000 — more than the balance due)
4. Click **Record Payment**.
5. **Expected Result**:
   - A danger flash message: `Payment amount (₹2,00,000.00) exceeds the balance due (₹1,50,000.00).`
   - No payment is recorded. The payment history remains unchanged.

---

## Scenario E: Delete an Unpaid Invoice (No Payments)

1. Navigate to **Finance → Invoices** (`/finance/invoices`).
2. Locate an Unpaid invoice that has **no payments recorded** (a red trash icon should be visible in its Actions column).
3. Click the **trash icon** (Delete).
4. A browser confirmation dialog appears: "Delete invoice INV-XXXX-XXX?"
5. Click **OK**.
6. **Expected Result**:
   - A success message: `Invoice deleted successfully.`
   - The invoice is removed from the list.
   - An audit log entry is created with action `DELETE` and entity type `Invoice`.

---

## Scenario F: Delete Protection — Paid Invoice

1. Navigate to the invoice that was fully paid in Scenario C.
2. **Expected Result**:
   - The **trash icon** (Delete button) is **not visible** in the Actions column for this invoice.
   - On its Detail page, the Delete Invoice button is also **not visible**.

---

## Scenario G: Delete Protection — Invoice with Partial Payments

1. If you have an invoice with partial payments recorded (but not fully paid):
   - Navigate to its Detail page.
   - **Expected Result**: The Delete Invoice button is **not visible** because payments have been recorded.
   - On the Invoices list page, the trash icon is also **not visible** for this invoice.

---

## Scenario H: Overdue Invoice Auto-Detection

1. Create a new invoice with a past due date:
   - Navigate to **Finance → Invoices → New Invoice**.
   - **Invoice Number**: `INV-TEST-OVERDUE`
   - **Client Name**: `Test Client`
   - **Amount**: `50000`
   - **Status**: `Unpaid`
   - **Issue Date**: Any past date (e.g., `2026-04-01`)
   - **Due Date**: A past date (e.g., `2026-05-01`)
   - Click **Save Invoice**.
2. Navigate to the **Finance Dashboard** (`/finance/`).
3. **Expected Result**:
   - The invoice `INV-TEST-OVERDUE` is automatically flagged as **Overdue**.
   - A new **red stat card** appears on the dashboard showing **"Overdue Invoices"** with a count ≥ 1.
   - On the Invoices list page, this invoice now shows an **`Overdue`** status badge.

---

## Scenario I: Dashboard Integration Verification

1. Navigate to the **Finance Dashboard** (`/finance/`).
2. **Expected Result**:
   - All existing stat cards (Total Invoiced, Unpaid Invoices, Total Expenses, etc.) are still present and correct.
   - If there are any overdue invoices, the **Overdue Invoices** stat card is displayed with a red warning icon.
   - The **Pending Payroll** stat card is still present.

---

## Scenario J: Audit Log Verification

1. Log in as an Admin user and navigate to the Admin audit logs.
2. **Expected Result**: The following audit entries should be recorded from the tests above:
   - `RECORD_PAYMENT` entries for each payment recorded.
   - `DELETE` entry for the deleted invoice.
   - All entries include correct metadata (user ID, IP address, entity type, entity ID, and description).

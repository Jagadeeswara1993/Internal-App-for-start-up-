# 🚀 Enterprise Portal — Feature Recommendations

> **Scope**: All modules except Finance  
> **Based on**: Full codebase analysis of models, routes, templates, and services  
> **Date**: May 2026

---

## What Already Exists (Your Current Feature Set)

Before recommending new features, here's what your app **already has**:

| Module | Existing Features |
|--------|-------------------|
| **Auth** | Login, logout, password reset (email), forced password change, account lockout, login history, password complexity |
| **Admin** | User CRUD, module assignment, departments, designations, shifts, holidays, leave policies, leave cycle settings, attendance rules, audit logs, PM overview, timesheets, notifications (broadcast), analytics, login history |
| **HR** | Employee management, profile completion, leave management (multi-step: manager→HR), attendance (check-in/out, override, auto-absent), payroll (input + generate), recruitment (jobs, candidates, interviews + feedback), performance reviews, timesheets, shift swaps, comp-offs, profile update approvals, attendance regularization approvals, documents, analytics |
| **PM** | Projects (with PM assignment), tasks (with hierarchy: epics → tasks → sub-tasks), milestones, Kanban board view, timesheet approvals, notifications, analytics |
| **Employee** | Dashboard, profile (with update requests), attendance (check-in/out), leaves (request + cancel + half-day), leave balance, holiday calendar, timesheets, payslips, expenses, documents, notifications, my tasks, projects view, performance view, shift swap requests, comp-offs, attendance regularization, team management (for managers), team leaves, analytics |

---

## 🔴 Incomplete / Half-Built Features (Fix First)

These features have **backend models or partial code** but are missing UI or key functionality:

| # | Feature | What Exists | What's Missing | Effort |
|---|---------|-------------|----------------|--------|
| 1 | **Candidate Resume Upload** | `Candidate.resume_file` column exists in DB | No file upload handler in recruitment routes, no file viewer in job detail page | 🟡 1 day |
| 2 | **Expense Receipt Viewer** | `EmployeeExpense.receipt_filename` column exists | Employee can upload, but HR/Admin has **no route to view/approve/reject** employee expenses | 🟡 1-2 days |
| 3 | **Leave Cancellation by Employee** | `Leave.cancelled_at` and `cancelled_reason` columns exist | Employee can't cancel their own pending leave requests from the UI (no cancel button/route) | 🟢 0.5 day |
| 4 | **Payslip PDF Download** | Payslip detail page exists (`payslip_detail.html`) | No export-to-PDF button — employees can only view on screen | 🟢 0.5 day |
| 5 | **Expense Edit/Delete Before Approval** | Expense form exists | Once submitted, employee cannot edit or withdraw pending expense claims | 🟢 0.5 day |

---

## 🟠 High-Value New Features

### 1. 📢 Company Announcements / News Board
**What**: Admin/HR can post company-wide announcements (policy changes, events, celebrations) that appear on every employee's dashboard.

**Why**: Currently, the only way to communicate is via individual notifications. There's no broadcast "pinned" content.

**How it works**:
- New `Announcement` model: title, body (rich text), author, pinned, category (General/Policy/Event), publish_date, expiry_date
- Admin route to create/edit/pin announcements
- Employee dashboard shows latest announcements in a card carousel
- Optional: "Acknowledge" button so HR can track who read important policies

**Effort**: 🟡 2-3 days

---

### 2. 👥 Employee Directory & Org Chart
**What**: A searchable company directory showing all employees with their departments, designations, locations, and reporting chain.

**Why**: Employees currently have no way to find colleagues or understand the organizational hierarchy.

**How it works**:
- New route: `/employee/directory` — searchable grid/list of all active employees
- Filter by department, designation, location
- Click on a person → mini profile card (name, emp code, department, email, reporting manager)
- Org chart view: tree visualization using the existing `reporting_manager_id` relationship
- No new models needed — uses existing `Employee`, `Department`, `Designation` data

**Effort**: 🟡 2 days

---

### 3. 📎 Task Comments & Activity Feed
**What**: Allow users to write comments and track activity on tasks (who changed status, who was assigned, etc.)

**Why**: Currently tasks have no discussion thread. Team members must use external tools (WhatsApp, email) to discuss task details.

**How it works**:
- New `TaskComment` model: task_id, user_id, body, created_at
- New `TaskActivity` model: task_id, user_id, action ("changed status to In Progress"), created_at
- Task detail page shows a timeline of comments + auto-logged activities
- @mention support (optional, tag team members)
- Notifications when someone comments on your task

**Effort**: 🟠 2-3 days

---

### 4. 📊 Weekly/Monthly Timesheet Summary Report
**What**: A consolidated view that shows each employee's weekly hours across all projects, with comparison against expected working hours.

**Why**: Currently timesheets are individual entries. Managers and HR have no quick "this week" summary to check if hours are being logged properly.

**How it works**:
- New route for PM: `/pm/weekly-report` — shows current week's hours per team member
- New route for HR: `/hr/weekly-utilization` — company-wide utilization percentage
- Color-coded: green (8h+/day), yellow (4-8h), red (<4h or no entry)
- Auto-flag employees who haven't logged timesheets for 3+ days
- Export as CSV/PDF

**Effort**: 🟡 2 days

---

### 5. 📅 Interactive Leave Calendar
**What**: A visual calendar view (month grid) showing who is on leave, who is present, and upcoming holidays — all on one screen.

**Why**: The current leave view is a table. Managers planning sprints or deadlines need a calendar view to see team availability at a glance.

**How it works**:
- Calendar grid (built with CSS grid or a lightweight JS library like FullCalendar)
- Color-coded dots: 🟢 present, 🔴 on leave, 🟡 half-day, ⬜ holiday, 🔵 weekend
- Click on a day → popup showing who is absent
- Filter by department or team
- No new models needed — uses existing `Leave`, `Attendance`, `Holiday` data

**Effort**: 🟡 2-3 days

---

### 6. 🎯 Goal Setting & OKR Tracking
**What**: Let managers set quarterly goals/objectives for employees and track key results.

**Why**: The existing `PerformanceReview` model only captures periodic reviews (ratings + comments). There's no way to set forward-looking goals and track progress.

**How it works**:
- New `Goal` model: employee_id, title, description, target_metric, current_metric, due_date, status (Not Started/In Progress/Achieved/Missed), quarter, year
- Manager sets goals → employee updates progress → reviewed in performance cycle
- Dashboard widget: "My Goals" progress bar

**Effort**: 🟠 3 days

---

### 7. 🔔 Real-Time Notification System (WebSocket or Polling)
**What**: Live notification badge updates without page refresh.

**Why**: Currently, the notification count only updates when the page reloads. If a PM assigns a task to an employee, the employee won't see the badge until they navigate to a new page.

**How it works**:
- Option A (simple): JavaScript polling every 30 seconds to `/api/notification-count`
- Option B (advanced): Flask-SocketIO for real-time push
- Toast notification popup when a new notification arrives
- Sound alert (optional, toggleable)

**Effort**: 🟢 Option A: 0.5 day | 🟠 Option B: 2 days

---

### 8. 📱 Employee Self-Service: Work From Home (WFH) Requests
**What**: Employees can request WFH days, which go through manager/HR approval (similar to leave flow).

**Why**: Hybrid/remote work is now standard. There's no way to formally track WFH vs office attendance.

**How it works**:
- New `WFHRequest` model: employee_id, date, reason, status (Pending/Approved/Rejected), approved_by
- Employee submits from their dashboard
- Manager approval → auto-marks attendance as "WFH" instead of "Absent"
- HR dashboard shows WFH statistics per department

**Effort**: 🟡 2 days

---

### 9. 📋 Meeting Room / Asset Booking
**What**: Employees can book conference rooms, projectors, or shared equipment through a simple calendar interface.

**Why**: Common startup need — avoids double-booking and Excel-based tracking.

**How it works**:
- New `Resource` model: name, type (Room/Equipment), capacity, location
- New `Booking` model: resource_id, booked_by, date, start_time, end_time, purpose
- Calendar view showing availability slots
- Conflict detection (prevent double-booking)

**Effort**: 🟠 3 days

---

### 10. 📈 Employee Onboarding Checklist
**What**: When a new user is created, auto-generate a checklist of onboarding tasks (submit documents, complete profile, read policies, etc.) and track completion.

**Why**: Currently, new employees are created with a blank profile and no guidance. HR has to manually follow up.

**How it works**:
- New `OnboardingTask` model: title, description, is_required, order
- New `OnboardingProgress` model: employee_id, task_id, completed, completed_at
- Admin configures the checklist template
- New employee sees "Getting Started" widget on their dashboard
- HR dashboard shows onboarding completion percentage per new hire

**Effort**: 🟡 2-3 days

---

## 🟢 Quick Wins (Small Effort, Big Impact)

| # | Feature | Description | Effort |
|---|---------|-------------|--------|
| 1 | **Confirmation Dialogs** | Add SweetAlert2 confirmation popups before destructive actions (delete project, deactivate user, reject leave) | 0.5 day |
| 2 | **Breadcrumb Navigation** | Add breadcrumbs on deep pages like `HR → Recruitment → Job Detail → Add Candidate` | 0.5 day |
| 3 | **Dark Mode Toggle** | CSS variables are already defined — just add a toggle button in the navbar | 0.5 day |
| 4 | **Bulk User CSV Import** | Admin uploads CSV → system creates users + employees + assigns modules in batch | 1 day |
| 5 | **Health Check Endpoint** | `/health` route that checks DB connectivity — needed for deployment monitoring | 0.5 hour |
| 6 | **Data Export (CSV)** | Add "Export CSV" buttons to employee list, attendance report, leave report tables | 1 day |
| 7 | **Dashboard Customization** | Let employees reorder/hide dashboard widgets (store preferences in a JSON column) | 1-2 days |
| 8 | **Email Notifications** | Send emails when leave is approved/rejected, task is assigned, performance review is shared | 1 day |

---

## 📋 Recommended Priority Order

If I were building these in order of business value:

| Priority | Feature | Why First |
|----------|---------|-----------|
| 🥇 1 | Fix incomplete features (resume upload, leave cancel, expense approval) | Finish what's half-built before adding new things |
| 🥈 2 | Company Announcements | Every company needs internal communication |
| 🥉 3 | Employee Directory + Org Chart | Zero new models, huge usability win |
| 4 | Task Comments & Activity Feed | Makes PM module actually useful for collaboration |
| 5 | Interactive Leave Calendar | Visual planning tool for managers |
| 6 | Quick Wins (confirmations, breadcrumbs, dark mode) | Polish that makes the app feel professional |
| 7 | Weekly Timesheet Summary | Management reporting need |
| 8 | WFH Requests | Modern workplace requirement |
| 9 | Real-Time Notifications | UX enhancement |
| 10 | Goal Setting / OKR | Extends performance management |

---

> **Which features interest you the most?** Tell me which ones you'd like to build, and I'll create a detailed implementation plan with exact file changes, models, routes, and templates needed.

"""HR routes package — split from monolithic routes.py for maintainability."""

from app.hr.routes import (  # noqa: F401
    dashboard_routes,
    employee_routes,
    attendance_routes,
    leave_routes,
    performance_routes,
    recruitment_routes,
    payroll_routes,
    document_routes,
    timesheet_routes,
)

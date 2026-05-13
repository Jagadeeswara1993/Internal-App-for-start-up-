"""Employee routes package — split from monolithic routes.py for maintainability."""

from app.employee.routes import (  # noqa: F401
    dashboard_routes,
    profile_routes,
    attendance_routes,
    leave_routes,
    work_routes,
    timesheet_routes,
    team_routes,
)

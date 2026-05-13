"""Admin routes package — split from monolithic routes.py for maintainability."""

from app.admin.routes import (  # noqa: F401
    dashboard_routes,
    user_routes,
    config_routes,
    notification_routes,
    pm_timesheet_routes,
)

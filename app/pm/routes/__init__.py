"""PM routes package — split from monolithic routes.py for maintainability."""

from app.pm.routes import (  # noqa: F401
    helpers,
    dashboard_routes,
    project_routes,
    team_routes,
    task_routes,
    api_routes,
)

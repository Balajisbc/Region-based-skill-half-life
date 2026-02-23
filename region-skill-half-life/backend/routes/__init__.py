from .auth_routes import router as auth_routes
from .analytics_routes import router as analytics_routes
from .region_routes import router as region_routes
from .chat_routes import router as chat_routes
from .report_routes import router as report_routes
from .comparison_routes import router as comparison_routes
from .simulation_routes import router as simulation_routes

__all__ = [
    "auth_routes",
    "analytics_routes",
    "region_routes",
    "chat_routes",
    "report_routes",
    "comparison_routes",
    "simulation_routes",
]

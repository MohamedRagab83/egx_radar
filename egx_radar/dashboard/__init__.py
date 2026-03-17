"""Dashboard API module - Flask-based web interface for EGX Radar."""

from egx_radar.dashboard.app import create_app
from egx_radar.dashboard.routes import api_bp, dashboard_bp
from egx_radar.dashboard.websocket import socketio

__all__ = [
    'create_app',
    'api_bp',
    'dashboard_bp',
    'socketio',
]

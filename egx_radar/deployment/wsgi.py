"""WSGI entry point for the Railway web service."""

from __future__ import annotations

import os

from egx_radar.dashboard.app import create_app


app = create_app(os.environ.get("EGX_RADAR_ENV", "production"))

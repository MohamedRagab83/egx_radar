"""Main entry point for EGX Radar Dashboard server."""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from egx_radar.dashboard.app import create_app
from egx_radar.dashboard.websocket import socketio


def run_dashboard(host: str = '0.0.0.0', port: int = 5000, debug: bool = False):
    """
    Run the dashboard server.
    
    Args:
        host: Server host address
        port: Server port
        debug: Enable debug mode
    """
    app = create_app(config_name='development' if debug else 'production')
    socketio.init_app(app)
    
    print(f"""
    ╔══════════════════════════════════════════════════════════╗
    ║       EGX Radar Dashboard Server                         ║
    ║       Version 0.8.3                                      ║
    ╚══════════════════════════════════════════════════════════╝
    
    Starting server...
    
    Dashboard: http://{host}:{port}
    API: http://{host}:{port}/api
    WebSocket: ws://{host}:{port}/socket.io
    
    Press Ctrl+C to stop
    """)
    
    socketio.run(
        app,
        host=host,
        port=port,
        debug=debug,
        allow_unsafe_werkzeug=debug
    )


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='EGX Radar Dashboard Server')
    parser.add_argument('--host', default='0.0.0.0', help='Server host address')
    parser.add_argument('--port', type=int, default=5000, help='Server port')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    run_dashboard(host=args.host, port=args.port, debug=args.debug)

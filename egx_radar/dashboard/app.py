"""Flask application factory and configuration."""

import os
from flask import Flask
from flask_cors import CORS

from egx_radar.database import DatabaseManager
from egx_radar.database.config import DatabaseConfig


def create_app(config_name: str = 'production') -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        config_name: Environment (development, testing, production)
    
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    
    # Configuration
    if config_name == 'development':
        app.config['DEBUG'] = True
        app.config['TESTING'] = False
        app.config['DATABASE_URL'] = 'sqlite:///egx_radar.db'
    elif config_name == 'testing':
        app.config['DEBUG'] = True
        app.config['TESTING'] = True
        app.config['DATABASE_URL'] = 'sqlite:///:memory:'
    else:  # production
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
        app.config['DATABASE_URL'] = DatabaseConfig.get_production_url()
    
    # CORS support
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Database initialization
    db_url = os.environ.get('DATABASE_URL', app.config['DATABASE_URL'])
    app.db_manager = DatabaseManager(database_url=db_url)
    
    # Ensure database tables exist
    app.db_manager.init_db()
    
    # Register blueprints
    from egx_radar.dashboard.routes import api_bp, dashboard_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'version': '0.8.3'}, 200
    
    return app


if __name__ == '__main__':
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000, debug=True)

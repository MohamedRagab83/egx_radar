"""Flask application factory and configuration."""

import os
from flask import Flask
from flask_cors import CORS
from flask_login import LoginManager

from egx_radar.database import DatabaseManager
from egx_radar.database.config import DatabaseConfig
from egx_radar.database.models import User


def create_app(config_name: str = 'production') -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        config_name: Environment (development, testing, production)
    
    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    secret_key = os.environ.get('SECRET_KEY')
    if not secret_key:
        if config_name == 'production':
            raise RuntimeError('SECRET_KEY is required in production')
        secret_key = 'egx-radar-dev-secret'
    app.config['SECRET_KEY'] = secret_key
    
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
        if not os.environ.get('DATABASE_URL') and not os.environ.get('DB_TYPE'):
            raise RuntimeError('DATABASE_URL is required in production')
        app.config['DATABASE_URL'] = DatabaseConfig.get_production_url()

    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    if config_name == 'production':
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['REMEMBER_COOKIE_SECURE'] = True
    
    # CORS support
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Database initialization
    db_url = os.environ.get('DATABASE_URL', app.config['DATABASE_URL'])
    app.db_manager = DatabaseManager(database_url=db_url)
    
    # Ensure database tables exist
    app.db_manager.init_db()

    # Authentication
    login_manager = LoginManager()
    login_manager.login_view = 'dashboard.login'
    login_manager.login_message = 'Please log in to access the dashboard.'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str):
        try:
            user_pk = int(user_id)
        except (TypeError, ValueError):
            return None
        with app.db_manager.get_session() as session:
            return session.query(User).filter(User.id == user_pk).first()
    
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
    config_name = os.environ.get('EGX_RADAR_ENV', 'development')
    app = create_app(config_name)
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', '5000')),
        debug=app.config.get('DEBUG', False),
    )

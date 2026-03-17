"""Database configuration for different environments."""

import os
from typing import Optional
from enum import Enum


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = 'sqlite'
    POSTGRESQL = 'postgresql'


class DatabaseConfig:
    """Database configuration manager."""
    
    @staticmethod
    def get_url(
        db_type: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> str:
        """
        Get database connection URL.
        
        Priority:
        1. Environment variable DATABASE_URL
        2. Provided parameters
        3. Default SQLite
        
        Args:
            db_type: Database type (sqlite, postgresql)
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        
        Returns:
            Connection URL string
        """
        # Check environment variable first
        if 'DATABASE_URL' in os.environ:
            return os.environ['DATABASE_URL']
        
        # Use provided parameters
        db_type = db_type or os.environ.get('DB_TYPE', 'sqlite')
        
        if db_type.lower() == 'postgresql':
            host = host or os.environ.get('DB_HOST', 'localhost')
            port = port or int(os.environ.get('DB_PORT', 5432))
            database = database or os.environ.get('DB_NAME', 'egx_radar')
            user = user or os.environ.get('DB_USER', 'postgres')
            password = password or os.environ.get('DB_PASSWORD', '')
            
            if password:
                url = f'postgresql://{user}:{password}@{host}:{port}/{database}'
            else:
                url = f'postgresql://{user}@{host}:{port}/{database}'
            
            return url
        
        elif db_type.lower() == 'sqlite':
            db_path = database or os.environ.get('DB_PATH', 'egx_radar.db')
            return f'sqlite:///{db_path}'
        
        else:
            raise ValueError(f'Unsupported database type: {db_type}')
    
    @staticmethod
    def get_development_url() -> str:
        """Get development database URL (SQLite in-memory)."""
        return 'sqlite:///:memory:'
    
    @staticmethod
    def get_testing_url() -> str:
        """Get testing database URL (SQLite temporary file)."""
        return 'sqlite:///test_egx_radar.db'
    
    @staticmethod
    def get_production_url() -> str:
        """
        Get production database URL from environment.
        
        Requires:
        - DATABASE_URL or
        - DB_TYPE=postgresql with DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            return db_url
        
        # Try to construct from individual env vars
        return DatabaseConfig.get_url(
            db_type=os.environ.get('DB_TYPE'),
            host=os.environ.get('DB_HOST'),
            port=int(os.environ.get('DB_PORT', 5432)) if os.environ.get('DB_PORT') else None,
            database=os.environ.get('DB_NAME'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
        )


# Recommended environment setup:
"""
DEVELOPMENT:
    export DATABASE_URL=sqlite:///egx_radar.db

TESTING:
    export DATABASE_URL=sqlite:///:memory:
    or use DatabaseConfig.get_testing_url()

PRODUCTION:
    export DATABASE_URL=postgresql://user:password@host:5432/egx_radar
    
    OR set individual variables:
    export DB_TYPE=postgresql
    export DB_HOST=db.example.com
    export DB_PORT=5432
    export DB_NAME=egx_radar
    export DB_USER=app_user
    export DB_PASSWORD=secure_password
"""

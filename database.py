"""
Database configuration - separating db instance from app to avoid circular imports
"""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
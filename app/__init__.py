from flask import Flask, render_template
from config import Config
from app.extensions import db, migrate, login_manager, csrf
from app.models import User
from seed import seed_database
import os

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize Extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    
    # Ensure static directories and uploads directory exist
    upload_dir = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    # Register Blueprints
    from app.auth import auth_bp
    from app.dashboard import dashboard_bp
    from app.vehicles import vehicles_bp
    from app.drivers import drivers_bp
    from app.trips import trips_bp
    from app.maintenance import maintenance_bp
    from app.fuel import fuel_bp
    from app.expenses import expenses_bp
    from app.reports import reports_bp
    from app.settings import settings_bp
    from app.notifications import notifications_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(dashboard_bp, url_prefix='/')
    app.register_blueprint(vehicles_bp, url_prefix='/vehicles')
    app.register_blueprint(drivers_bp, url_prefix='/drivers')
    app.register_blueprint(trips_bp, url_prefix='/trips')
    app.register_blueprint(maintenance_bp, url_prefix='/maintenance')
    app.register_blueprint(fuel_bp, url_prefix='/fuel')
    app.register_blueprint(expenses_bp, url_prefix='/expenses')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(notifications_bp, url_prefix='/notifications')
    
    # Context Processor for layout templates (current year, etc.)
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime_now_helper
        }
        
    def datetime_now_helper():
        import datetime
        return datetime.datetime.now()

    # Custom Error Handlers for professional ERP styling
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Auto-seed database if empty (great for deployment/hackathon startup!)
    with app.app_context():
        # Check if database is empty (no users table or 0 users)
        try:
            db.create_all()
            if User.query.count() == 0:
                print("Database is empty. Automatic seeding started...")
                seed_database()
        except Exception as e:
            print(f"Error checking/seeding database: {e}")
            db.session.rollback()

    return app

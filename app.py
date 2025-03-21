
import os
import logging
from flask import Flask
from flask_login import LoginManager
from werkzeug.security import generate_password_hash
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# create the app
app = Flask(__name__)
app.secret_key ="56a4a3feb9f75756c7bb8b6c183d519cce83542731be7924d570a61a74f6a969"

# configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://postgres:Mukal*2024@localhost/license_manager"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

from models import db, User, load_user
db.init_app(app)

with app.app_context():
    db.create_all()

    # Create default admin user if it doesn't exist
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            id=str(uuid.uuid4()),
            username='mafia',
            password_hash=generate_password_hash('Mukal*2019'),
            role='admin',
            balance=0
        )
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created! Username: mafia, Password: Mukal*2019")

# Import routes after app initialization to avoid circular imports
from auth import auth_bp
from admin import admin_bp
from reseller import reseller_bp

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(reseller_bp)

# Set up login manager loader
login_manager.user_loader(load_user)

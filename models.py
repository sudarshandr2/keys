
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase
from flask_sqlalchemy import SQLAlchemy

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

    def get_id(self):
        return str(self.id)

class Hack(db.Model):
    __tablename__ = 'hacks'

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

    prices = db.relationship('HackPrice', backref='hack', lazy=True)
    keys = db.relationship('LicenseKey', backref='hack', lazy=True)

class HackPrice(db.Model):
    __tablename__ = 'hack_prices'

    id = db.Column(db.String(36), primary_key=True)
    hack_id = db.Column(db.String(36), db.ForeignKey('hacks.id'), nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)

class LicenseKey(db.Model):
    __tablename__ = 'license_keys'

    id = db.Column(db.String(36), primary_key=True)
    hack_id = db.Column(db.String(36), db.ForeignKey('hacks.id'), nullable=False)
    key = db.Column(db.String(64), unique=True, nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='available')
    reseller_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    customer_ref = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sold_at = db.Column(db.DateTime)

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.String(36), primary_key=True)
    reseller_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    key_id = db.Column(db.String(36), db.ForeignKey('license_keys.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

def load_user(user_id):
    return User.query.get(user_id)

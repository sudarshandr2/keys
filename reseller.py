from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from models import User, LicenseKey, Transaction, Hack, HackPrice
from app import db
import uuid

reseller_bp = Blueprint('reseller', __name__)

def reseller_required(f):
    """Decorator to require reseller role for routes"""
    @login_required
    def decorated_view(*args, **kwargs):
        if not current_user.role == 'reseller':
            flash('Access denied. Reseller account required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_view.__name__ = f.__name__
    return decorated_view

@reseller_bp.route('/reseller/dashboard')
@reseller_required
def dashboard():
    # Get monthly keys count
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_keys = Transaction.query.filter(
        Transaction.reseller_id == current_user.id,
        Transaction.type == 'key_purchase',
        Transaction.created_at >= month_start
    ).count()

    # Get recent transactions
    recent_transactions = db.session.query(Transaction, LicenseKey)\
        .outerjoin(LicenseKey, Transaction.key_id == LicenseKey.id)\
        .filter(Transaction.reseller_id == current_user.id)\
        .order_by(Transaction.created_at.desc())\
        .limit(10).all()

    return render_template('reseller/dashboard.html',
                         monthly_keys=monthly_keys,
                         recent_transactions=recent_transactions)

@reseller_bp.route('/reseller/generate')
@reseller_required
def generate():
    # Get active hacks and their prices
    hacks = Hack.query.filter_by(active=True).all()
    for hack in hacks:
        hack.prices = HackPrice.query.filter_by(hack_id=hack.id).all()
    return render_template('reseller/generate.html', hacks=hacks, current_user=current_user)

@reseller_bp.route('/reseller/generate_key', methods=['POST'])
@reseller_required
def generate_key():
    try:
        duration = request.form.get('duration')
        customer = request.form.get('customer', '')
        hack_id = request.form.get('hack_id')

        if not duration or not hack_id:
            flash('Duration and hack must be selected', 'danger')
            return redirect(url_for('reseller.generate'))

        # Get hack price
        hack_price = HackPrice.query.filter_by(
            hack_id=hack_id,
            duration=duration
        ).first()

        if not hack_price:
            flash('Invalid price configuration', 'danger')
            return redirect(url_for('reseller.generate'))

        if current_user.balance < hack_price.price:
            flash('Insufficient balance', 'danger')
            return redirect(url_for('reseller.generate'))

        # Get available key
        available_key = LicenseKey.query.filter_by(
            status='available',
            duration=duration,
            hack_id=hack_id
        ).first()

        if not available_key:
            flash('No keys available for selected duration', 'danger')
            return redirect(url_for('reseller.generate'))

        # Update key status
        available_key.status = 'sold'
        available_key.reseller_id = current_user.id
        available_key.customer_ref = customer
        available_key.sold_at = datetime.utcnow()

        # Update user balance
        current_user.balance -= hack_price.price

        # Record transaction
        transaction = Transaction(
            id=str(uuid.uuid4()),
            reseller_id=current_user.id,
            type='key_purchase',
            key_id=available_key.id,
            amount=hack_price.price,
            created_at=datetime.utcnow()
        )
        db.session.add(transaction)
        db.session.commit()

        # Get updated hack prices for template
        hacks = Hack.query.filter_by(active=True).all()
        for hack in hacks:
            hack.prices = HackPrice.query.filter_by(hack_id=hack.id).all()

        return render_template('reseller/generate.html',
                            generated_key=available_key.key,
                            hacks=hacks,
                            current_user=current_user)

    except Exception as e:
        db.session.rollback()
        flash(f'Error generating key: {str(e)}', 'danger')
        return redirect(url_for('reseller.generate'))

@reseller_bp.route('/reseller/history')
@reseller_required
def history():
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    duration = request.args.get('duration')

    query = db.session.query(Transaction, LicenseKey)\
        .outerjoin(LicenseKey, Transaction.key_id == LicenseKey.id)\
        .filter(Transaction.reseller_id == current_user.id)\
        .filter(Transaction.type == 'key_purchase')\
        .order_by(Transaction.created_at.desc())

    if date_from:
        date_from = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(Transaction.created_at >= date_from)

    if date_to:
        date_to = datetime.strptime(date_to, '%Y-%m-%d')
        query = query.filter(Transaction.created_at <= date_to)

    transactions = query.all()
    
    # Convert to list of transaction objects with license key attribute
    transactions = [
        type('Transaction', (), {
            'created_at': t.created_at,
            'amount': t.amount,
            'key_id': t.key_id,
            'license_key': k if k else type('Empty', (), {'key': '', 'duration': '', 'status': ''})()
        })() for t, k in transactions
    ]

    if duration:
        transactions = [t for t in transactions if t.license_key.duration == duration]

    return render_template('reseller/history.html', transactions=transactions)
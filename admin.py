from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from models import User, LicenseKey, Transaction, Hack, HackPrice
from app import db
from datetime import datetime
import uuid

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    """Decorator to require admin role for routes"""
    @login_required
    def decorated_view(*args, **kwargs):
        if not current_user.role == 'admin':
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_view.__name__ = f.__name__
    return decorated_view

@admin_bp.route('/admin/dashboard')
@admin_required
def dashboard():
    # Calculate statistics
    resellers = User.query.filter_by(role='reseller').all()
    admin = User.query.filter_by(role='admin').first()

    # Get keys by duration
    keys_by_duration = {}
    for duration in ['day', 'week', 'month']:
        available = LicenseKey.query.filter_by(status='available', duration=duration).count()
        sold = LicenseKey.query.filter_by(status='sold', duration=duration).count()
        keys_by_duration[duration] = {'available': available, 'sold': sold}

    total_revenue = db.session.query(db.func.sum(Transaction.amount)).filter_by(type='key_purchase').scalar() or 0

    stats = {
        'total_resellers': len(resellers),
        'keys_by_duration': keys_by_duration,
        'total_revenue': total_revenue,
        'admin_balance': admin.balance if admin else 0
    }

    # Get recent transactions
    transactions = db.session.query(Transaction, LicenseKey)\
        .outerjoin(LicenseKey, Transaction.key_id == LicenseKey.id)\
        .order_by(Transaction.created_at.desc())\
        .limit(10).all()
    recent_transactions = []
    for t, key in transactions:
        reseller = User.query.get(t.reseller_id)
        recent_transactions.append({
            'date': t.created_at.strftime('%Y-%m-%d %H:%M'),
            'reseller': reseller.username if reseller else 'Unknown',
            'type': t.type,
            'amount': t.amount,
            'key': key.key if key else None
        })

    return render_template('admin/dashboard.html', stats=stats, recent_transactions=recent_transactions)

@admin_bp.route('/admin/hacks')
@admin_required
def hacks():
    hacks = Hack.query.all()
    for hack in hacks:
        hack.prices = HackPrice.query.filter_by(hack_id=hack.id).all()
    return render_template('admin/hacks.html', hacks=hacks)

@admin_bp.route('/admin/add_hack', methods=['POST'])
@admin_required
def add_hack():
    name = request.form.get('name')
    description = request.form.get('description')
    day_price = float(request.form.get('day_price', 0))
    week_price = float(request.form.get('week_price', 0))
    month_price = float(request.form.get('month_price', 0))

    if not name or not all([day_price, week_price, month_price]):
        flash('All fields are required', 'danger')
        return redirect(url_for('admin.hacks'))

    try:
        hack = Hack(
            id=str(uuid.uuid4()),
            name=name,
            description=description
        )
        db.session.add(hack)
        db.session.flush()

        # Add prices for different durations
        prices = [
            ('day', day_price),
            ('week', week_price),
            ('month', month_price)
        ]

        for duration, price in prices:
            hack_price = HackPrice(
                id=str(uuid.uuid4()),
                hack_id=hack.id,
                duration=duration,
                price=price
            )
            db.session.add(hack_price)

        db.session.commit()
        flash('Hack added successfully', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Error adding hack: ' + str(e), 'danger')

    return redirect(url_for('admin.hacks'))

@admin_bp.route('/admin/edit_hack', methods=['POST'])
@admin_required
def edit_hack():
    hack_id = request.form.get('hack_id')
    name = request.form.get('name')
    description = request.form.get('description')

    if not hack_id or not name:
        flash('Name is required', 'danger')
        return redirect(url_for('admin.hacks'))

    try:
        hack = Hack.query.get(hack_id)
        if hack:
            hack.name = name
            hack.description = description
            db.session.commit()
            flash('Hack updated successfully', 'success')
        else:
            flash('Hack not found', 'danger')

    except Exception as e:
        db.session.rollback()
        flash('Error updating hack: ' + str(e), 'danger')

    return redirect(url_for('admin.hacks'))

@admin_bp.route('/admin/update_prices', methods=['POST'])
@admin_required
def update_prices():
    hack_id = request.form.get('hack_id')
    day_price = float(request.form.get('day_price', 0))
    week_price = float(request.form.get('week_price', 0))
    month_price = float(request.form.get('month_price', 0))

    if not hack_id or not all([day_price, week_price, month_price]):
        flash('All prices are required', 'danger')
        return redirect(url_for('admin.hacks'))

    try:
        prices = HackPrice.query.filter_by(hack_id=hack_id).all()
        price_map = {'day': day_price, 'week': week_price, 'month': month_price}

        for price in prices:
            price.price = price_map[price.duration]

        db.session.commit()
        flash('Prices updated successfully', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Error updating prices: ' + str(e), 'danger')

    return redirect(url_for('admin.hacks'))

@admin_bp.route('/admin/resellers')
@admin_required
def resellers():
    resellers = User.query.filter_by(role='reseller').all()
    return render_template('admin/resellers.html', resellers=resellers)

@admin_bp.route('/admin/keys')
@admin_required
def keys():
    status = request.args.get('status')
    duration = request.args.get('duration')

    query = LicenseKey.query
    if status:
        query = query.filter_by(status=status)
    if duration:
        query = query.filter_by(duration=duration)

    keys = query.all()
    hacks = Hack.query.filter_by(active=True).all()
    return render_template('admin/keys.html', keys=keys, hacks=hacks)

@admin_bp.route('/admin/add_reseller', methods=['POST'])
@admin_required
def add_reseller():
    try:
        username = request.form.get('username')
        password = request.form.get('password')
        initial_balance = float(request.form.get('initial_balance', 0))

        if not username or not password:
            flash('Username and password are required', 'danger')
            return redirect(url_for('admin.resellers'))

        if initial_balance < 0:
            flash('Initial balance cannot be negative', 'danger')
            return redirect(url_for('admin.resellers'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('admin.resellers'))

        # Create reseller with initial balance
        new_reseller = User(
            id=str(uuid.uuid4()),
            username=username,
            password_hash=generate_password_hash(password),
            role='reseller',
            balance=initial_balance
        )
        db.session.add(new_reseller)
        db.session.flush()  # Ensure we have the ID before creating transaction

        # Record initial balance transaction if needed
        if initial_balance > 0:
            transaction = Transaction(
                id=str(uuid.uuid4()),
                reseller_id=new_reseller.id,
                type='balance_add',
                amount=initial_balance,
                created_at=datetime.utcnow()
            )
            db.session.add(transaction)

        db.session.commit()
        flash('Reseller added successfully', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error creating reseller: {str(e)}', 'danger')
        print(f"Error in add_reseller: {str(e)}")

    return redirect(url_for('admin.resellers'))

@admin_bp.route('/admin/generate_keys', methods=['POST'])
@admin_required
def generate_keys():
    try:
        count = int(request.form.get('count', 0))
        duration = request.form.get('duration')
        hack_id = request.form.get('hack_id')

        if not count or not duration or not hack_id or count > 100:
            flash('Invalid request', 'danger')
            return redirect(url_for('admin.keys'))

        hack = Hack.query.get(hack_id)
        if not hack:
            flash('Invalid hack selected', 'danger')
            return redirect(url_for('admin.keys'))

        import random
        import string

        for _ in range(count):
            key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
            key = '-'.join([key[i:i+4] for i in range(0, 16, 4)])

            license_key = LicenseKey(
                id=str(uuid.uuid4()),
                hack_id=hack_id,
                key=key,
                duration=duration,
                status='available',
                created_at=datetime.utcnow()
            )
            db.session.add(license_key)

        db.session.commit()
        flash(f'Successfully generated {count} keys', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Error generating keys: {str(e)}', 'danger')

    return redirect(url_for('admin.keys'))

@admin_bp.route('/admin/lock_reseller/<reseller_id>', methods=['POST'])
@admin_required
def lock_reseller(reseller_id):
    try:
        reseller = User.query.get(reseller_id)
        if reseller:
            reseller.active = not reseller.active
            db.session.commit()
            status = 'unlocked' if reseller.active else 'locked'
            flash(f'Reseller {status} successfully', 'success')
        else:
            flash('Reseller not found', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating reseller status: {str(e)}', 'danger')
    return redirect(url_for('admin.resellers'))

@admin_bp.route('/admin/add_balance', methods=['POST'])
@admin_required
def add_balance():
    reseller_id = request.form.get('reseller_id')
    new_balance = float(request.form.get('amount', 0))

    if not reseller_id or new_balance < 0:
        flash('Invalid request', 'danger')
        return redirect(url_for('admin.resellers'))

    try:
        reseller = User.query.get(reseller_id)
        if reseller:
            balance_difference = new_balance - reseller.balance
            reseller.balance = new_balance

            if balance_difference != 0:
                transaction = Transaction(
                    id=str(uuid.uuid4()),
                    reseller_id=reseller_id,
                    type='balance_update',
                    amount=balance_difference,
                    created_at=datetime.utcnow()
                )
                db.session.add(transaction)

            db.session.commit()
            flash(f'Updated balance to ${new_balance}', 'success')
        else:
            flash('Reseller not found', 'danger')

    except Exception as e:
        db.session.rollback()
        flash('Error updating balance: ' + str(e), 'danger')

    return redirect(url_for('admin.resellers'))

@admin_bp.route('/admin/import_keys', methods=['POST'])
@admin_required
def import_keys():
    try:
        keys_text = request.form.get('keys')
        duration = request.form.get('duration')
        hack_id = request.form.get('hack_id')

        if not all([keys_text, duration, hack_id]):
            flash('Keys, duration and hack are required', 'danger')
            return redirect(url_for('admin.keys'))

        # Verify hack exists
        hack = Hack.query.get(hack_id)
        if not hack:
            flash('Selected hack does not exist', 'danger')
            return redirect(url_for('admin.keys'))

        keys_list = [k.strip() for k in keys_text.split('\n') if k.strip()]
        imported = 0
        skipped = 0
        
        for key_value in keys_list:
            existing_key = LicenseKey.query.filter_by(key=key_value).first()
            if existing_key:
                skipped += 1
                continue
                
            key = LicenseKey(
                id=str(uuid.uuid4()),
                hack_id=hack_id,
                key=key_value,
                duration=duration,
                status='available',
                created_at=datetime.utcnow()
            )
            db.session.add(key)
            imported += 1

        db.session.commit()
        if skipped > 0:
            flash(f'Imported {imported} keys. Skipped {skipped} duplicate keys.', 'warning')
        else:
            flash(f'Successfully imported {imported} keys', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Error importing keys: ' + str(e), 'danger')

    return redirect(url_for('admin.keys'))

@admin_bp.route('/admin/delete_key/<key_id>', methods=['POST'])
@admin_required
def delete_key(key_id):
    try:
        key = LicenseKey.query.get(key_id)
        if key and key.status == 'available':
            db.session.delete(key)
            db.session.commit()
            flash('Key deleted successfully', 'success')
        else:
            flash('Key not found or already sold', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting key: {str(e)}', 'danger')
    return redirect(url_for('admin.keys'))
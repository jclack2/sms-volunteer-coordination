from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User
import phonenumbers

bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')

        # Normalize phone number
        try:
            parsed = phonenumbers.parse(phone_number, 'US')
            normalized_phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            normalized_phone = phone_number

        user = User.query.filter_by(phone_number=normalized_phone).first()

        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid phone number or password', 'error')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
@login_required
def register_user():
    """Register a new user (admin only)"""
    if not current_user.is_admin:
        flash('Admin access required', 'error')
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        name = request.form.get('name')
        phone_number = request.form.get('phone_number')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'
        is_sender = request.form.get('is_sender') == 'on'
        is_receiver = request.form.get('is_receiver', 'on') == 'on'

        # Normalize phone number
        try:
            parsed = phonenumbers.parse(phone_number, 'US')
            normalized_phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except:
            flash('Invalid phone number format', 'error')
            return render_template('auth/register.html')

        # Check if user exists
        if User.query.filter_by(phone_number=normalized_phone).first():
            flash('User with this phone number already exists', 'error')
            return render_template('auth/register.html')

        # Create user
        user = User(
            name=name,
            phone_number=normalized_phone,
            is_admin=is_admin,
            is_sender=is_sender,
            is_receiver=is_receiver
        )

        if password:
            user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash(f'User {name} created successfully', 'success')
        return redirect(url_for('dashboard.users'))

    return render_template('auth/register.html')

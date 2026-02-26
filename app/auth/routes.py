from flask import render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, current_user, login_required
from app.auth import bp
from app.models import User
from app.database import get_user_by_username, verify_password, update_user_login, create_user, check_user_exists, validate_password
from datetime import datetime

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        username = data.get('username')
        password = data.get('password')
        remember_me = data.get('remember_me', False)
        
        if not username or not password:
            flash('Please provide both username and password')
            return render_template('auth/login.html')
        
        user_data = get_user_by_username(username)
        
        if user_data is None or not verify_password(password, user_data['password_hash']):
            flash('Invalid username or password')
            return render_template('auth/login.html')
        
        user = User(user_data)
        login_user(user, remember=remember_me)
        update_user_login(user.id)
        
        next_page = request.args.get('next')
        if not next_page or next_page.startswith('/auth/'):
            next_page = url_for('main.dashboard')
        
        return redirect(next_page)
    
    return render_template('auth/login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        # Extract form data
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone = data.get('phone')
        voice_enabled = data.get('voice_enabled') == 'on' or data.get('voice_enabled') == True
        
        # Basic validation
        if not all([username, email, password, confirm_password, first_name, last_name, phone]):
            flash('All fields are required')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('auth/register.html')
        
        # Validate password complexity
        is_valid, message = validate_password(password)
        if not is_valid:
            flash(message)
            return render_template('auth/register.html')
        
        # Check for existing users
        if check_user_exists(username=username):
            flash('Username already exists')
            return render_template('auth/register.html')
        
        if check_user_exists(email=email):
            flash('Email already registered')
            return render_template('auth/register.html')
        
        # Create new user
        user_id, message = create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            voice_enabled=voice_enabled
        )
        
        if user_id:
            flash('Registration successful! You can now log in.')
            return redirect(url_for('auth.login'))
        else:
            flash(f'Registration failed: {message}')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@bp.route('/logout')
@login_required 
def logout():
    logout_user()
    flash('You have been logged out successfully.')
    return redirect(url_for('main.index'))

@bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')

@bp.route('/voice-preferences', methods=['GET', 'POST'])
@login_required
def voice_preferences():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        
        current_user.voice_enabled = data.get('voice_enabled', False)
        current_user.preferred_language = data.get('preferred_language', 'en-IN')
        current_user.voice_speed = float(data.get('voice_speed', 1.0))
        
        db.session.commit()
        flash('Voice preferences updated successfully.')
        
        if request.is_json:
            return {'status': 'success', 'message': 'Preferences updated'}
    
    return render_template('auth/voice_preferences.html')
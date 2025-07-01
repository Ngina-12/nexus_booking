from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta, timezone
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-very-secure-secret-key'

db = SQLAlchemy(app)

# ===== MODELS =====
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Hotel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    description = db.Column(db.Text)
    image_url = db.Column(db.String(200))
    rooms = db.relationship('Room', backref='hotel', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey('hotel.id'), nullable=False)
    room_number = db.Column(db.String(10), nullable=False)
    room_type = db.Column(db.String(50))
    price_per_night = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, default=2)
    is_available = db.Column(db.Boolean, default=True)
    bookings = db.relationship('Booking', backref='room', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in = db.Column(db.DateTime, nullable=False)
    check_out = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='confirmed')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# === DATETIME UTILITY ===
def ensure_aware_utc(dt):
    """Ensure datetime is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def patch_booking_datetimes(bookings):
    """Patch all datetime fields in Booking objects to be timezone-aware UTC."""
    for b in bookings:
        if hasattr(b, "check_in"):
            b.check_in = ensure_aware_utc(b.check_in)
        if hasattr(b, "check_out"):
            b.check_out = ensure_aware_utc(b.check_out)
        if hasattr(b, "created_at"):
            b.created_at = ensure_aware_utc(b.created_at)
    return bookings

def patch_user_datetimes(users):
    for u in users:
        if hasattr(u, "created_at"):
            u.created_at = ensure_aware_utc(u.created_at)
    return users

# ===== HELPER FUNCTIONS =====
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_role' not in session or session['user_role'] != 'admin':
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ===== ROUTES =====
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_role'] = user.role
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = db.session.get(User, session['user_id'])
    now = datetime.now(timezone.utc)
    if user.role == 'admin':
        bookings = db.session.execute(db.select(Booking)).scalars().all()
        patch_booking_datetimes(bookings)
        return render_template(
            'dashboard.html',
            user=user,
            bookings=bookings,
            User=User,
            Room=Room,
            Booking=Booking,
            now=now
        )
    else:
        rooms = db.session.execute(db.select(Room).filter_by(is_available=True)).scalars().all()
        bookings = db.session.execute(
            db.select(Booking).filter_by(user_id=user.id).order_by(Booking.check_in)
        ).scalars().all()
        patch_booking_datetimes(bookings)
        return render_template('dashboard.html', user=user, rooms=rooms, bookings=bookings, now=now)

@app.route('/my-bookings')
@login_required
def my_bookings():
    user = db.session.get(User, session['user_id'])
    bookings = db.session.execute(
        db.select(Booking).filter_by(user_id=user.id).order_by(Booking.check_in)
    ).scalars().all()
    patch_booking_datetimes(bookings)
    now = datetime.now(timezone.utc)
    return render_template('bookings.html', bookings=bookings, user=user, now=now)

@app.route('/book-room', methods=['POST'])
@login_required
def book_room():
    data = request.get_json()
    room_id = data.get('room_id')
    check_in = data.get('check_in')
    check_out = data.get('check_out')

    try:
        room = db.session.get(Room, room_id)
        if not room or not room.is_available:
            return jsonify({'success': False, 'message': 'Room not available.'}), 400

        booking = Booking(
            user_id=session['user_id'],
            room_id=room.id,
            check_in=datetime.strptime(check_in, '%Y-%m-%d').replace(tzinfo=timezone.utc),
            check_out=datetime.strptime(check_out, '%Y-%m-%d').replace(tzinfo=timezone.utc),
            status='confirmed'
        )
        room.is_available = False
        db.session.add(booking)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Room booked successfully!', 'room_id': room.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Booking failed.'}), 500

@app.route('/cancel-booking', methods=['POST'])
@login_required
def cancel_booking():
    data = request.get_json()
    booking_id = data.get('booking_id')
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    try:
        booking.status = 'cancelled'
        room = db.session.get(Room, booking.room_id)
        if room:
            room.is_available = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Booking cancelled', 'room_id': room.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Cancellation failed.'}), 500

@app.route('/get-bookings')
@login_required
def get_bookings():
    user = db.session.get(User, session['user_id'])
    if user.role == 'admin':
        bookings = db.session.execute(db.select(Booking)).scalars().all()
    else:
        bookings = db.session.execute(db.select(Booking).filter_by(user_id=user.id)).scalars().all()
    patch_booking_datetimes(bookings)

    result = []
    for b in bookings:
        room = db.session.get(Room, b.room_id)
        hotel = db.session.get(Hotel, room.hotel_id) if room else None
        booking_user = db.session.get(User, b.user_id)
        result.append({
            'id': b.id,
            'hotel': hotel.name if hotel else '',
            'room_number': room.room_number if room else '',
            'user': booking_user.username if booking_user else '',
            'check_in': b.check_in.strftime('%Y-%m-%d'),
            'check_out': b.check_out.strftime('%Y-%m-%d'),
            'status': b.status,
            'can_cancel': (b.status == 'confirmed' and (user.role == 'admin' or b.user_id == user.id))
        })
    return jsonify(result)

# ===== ADMIN USER MANAGEMENT =====
@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = db.session.execute(db.select(User).order_by(User.created_at.desc())).scalars().all()
    patch_user_datetimes(users)
    return render_template('user_management.html', users=users, user=db.session.get(User, session['user_id']))

@app.route('/admin/user/<int:user_id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    username = request.form.get('username')
    email = request.form.get('email')
    role = request.form.get('role')
    if username:
        user.username = username
    if email:
        user.email = email
    if role in ['admin', 'user']:
        user.role = role
    db.session.commit()
    flash('User updated successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.id == session['user_id']:
        flash('You cannot delete yourself.', 'error')
        return redirect(url_for('admin_users'))
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))

# ===== USER SETTINGS =====
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    user = db.session.get(User, session['user_id'])
    if hasattr(user, "created_at"):
        user.created_at = ensure_aware_utc(user.created_at)
    if request.method == 'POST':
        user.username = request.form.get('fullname', user.username)
        user.email = request.form.get('email', user.email)
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('settings'))
    return render_template('settings.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps
import random
import pyscrypt
import os
import binascii

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexus.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-very-secure-secret-key'

db = SQLAlchemy(app)

# ===== MODELS WITH PYSCRYPT HASHING =====
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))  # Stores salt + hash
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bookings = db.relationship('Booking', backref='user', lazy=True)

    def set_password(self, password):
        salt = os.urandom(16)
        hash = pyscrypt.hash(
            password=password.encode('utf-8'),
            salt=salt,
            N=16384,  # CPU/memory cost
            r=8,      # Block size
            p=1,      # Parallelization
            dkLen=32  # Output length
        )
        # Store as "salt:hash" hex strings
        self.password_hash = f"{binascii.hexlify(salt).decode()}:{binascii.hexlify(hash).decode()}"
    
    def check_password(self, password):
        try:
            salt_hex, stored_hash = self.password_hash.split(':')
            salt = binascii.unhexlify(salt_hex)
            
            test_hash = pyscrypt.hash(
                password=password.encode('utf-8'),
                salt=salt,
                N=16384,
                r=8,
                p=1,
                dkLen=32
            )
            return binascii.hexlify(test_hash).decode() == stored_hash
        except:
            return False

# ===== OTHER MODELS (UNCHANGED) =====
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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

def seed_database():
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        if not User.query.filter_by(role='admin').first():
            admin = User(
                username='admin',
                email='admin@nexus.com',
                role='admin'
            )
            admin.set_password('Admin123!')
            db.session.add(admin)
        
        # Create hotels if none exist
        if Hotel.query.count() == 0:
            hotels = [
                {'name': 'Grand Plaza', 'location': 'New York'},
                {'name': 'Ocean View', 'location': 'Miami'},
                {'name': 'Mountain Retreat', 'location': 'Denver'},
                {'name': 'Royal Orchid', 'location': 'Las Vegas'},
                {'name': 'Urban Haven', 'location': 'Chicago'}
            ]
            
            for hotel_data in hotels:
                hotel = Hotel(
                    name=hotel_data['name'],
                    location=hotel_data['location'],
                    description=f"Luxurious {hotel_data['name']} in {hotel_data['location']}",
                    image_url=f"/static/images/{hotel_data['name'].lower().replace(' ', '-')}.jpg"
                )
                db.session.add(hotel)
                db.session.commit()
                
                # Create rooms
                for i in range(1, 11):
                    room = Room(
                        hotel_id=hotel.id,
                        room_number=f"{hotel.id}{i:02d}",
                        room_type=random.choice(['Standard', 'Deluxe', 'Suite']),
                        price_per_night=random.randint(100, 500),
                        capacity=random.choice([1, 2, 4]),
                        is_available=True
                    )
                    db.session.add(room)
        
        # Create regular users
        if User.query.filter_by(role='user').count() < 24:
            for i in range(1, 25):
                user = User(
                    username=f'user{i}',
                    email=f'user{i}@nexus.com',
                    role='user'
                )
                user.set_password(f'User{i}@123')
                db.session.add(user)
        
        db.session.commit()

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
        user = User.query.filter_by(email=email).first()
        
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
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    available_rooms = Room.query.filter_by(is_available=True).all()
    
    if user.role == 'admin':
        bookings = Booking.query.order_by(Booking.check_in.desc()).limit(10).all()
    else:
        bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.check_in.desc()).all()
    
    return render_template('dashboard.html', 
                         user=user,
                         rooms=available_rooms,
                         bookings=bookings,
                         hotels=Hotel.query.all(),
                         now=datetime.utcnow())

# ===== BOOKING ROUTES (UNCHANGED) =====
# ... [Include all your existing booking routes unchanged] ...

if __name__ == '__main__':
    seed_database()
    app.run(debug=True)
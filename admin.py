from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User, Booking, Room
from datetime import datetime, timedelta
from sqlalchemy import func

admin = Blueprint('admin', __name__)

# Admin access decorator
def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        current_user = User.query.get(get_jwt_identity())
        if not current_user or current_user.role != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

@admin.route('/dashboard-metrics', methods=['GET'])
@admin_required
def get_dashboard_metrics():
    # Key performance indicators
    total_revenue = db.session.query(
        func.sum(Booking.total_price)
    ).filter(
        Booking.status == 'confirmed',
        Booking.check_in >= datetime.utcnow() - timedelta(days=30)
    ).scalar() or 0
    
    occupancy_rate = db.session.query(
        func.avg(
            func.cast(Booking.rooms_booked, Float) / 
            func.cast(Room.total_inventory, Float)
        )
    ).filter(
        Booking.check_in >= datetime.utcnow() - timedelta(days=30)
    ).scalar() or 0
    
    # Recent bookings
    recent_bookings = Booking.query.join(User).join(Room)\
        .order_by(Booking.created_at.desc())\
        .limit(10)\
        .with_entities(
            Booking.id,
            User.username,
            Room.room_number,
            Booking.check_in,
            Booking.check_out,
            Booking.total_price
        ).all()
    
    return jsonify({
        "metrics": {
            "revenue": float(total_revenue),
            "occupancy": float(occupancy_rate * 100),  # as percentage
            "active_users": User.query.count()
        },
        "recent_bookings": [
            {
                "id": b.id,
                "guest": b.username,
                "room": b.room_number,
                "dates": f"{b.check_in.strftime('%Y-%m-%d')} to {b.check_out.strftime('%Y-%m-%d')}",
                "total": float(b.total_price)
            } for b in recent_bookings
        ]
    }), 200
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import Booking, Room, db
from datetime import datetime
from app import stripe
import math

bookings = Blueprint('bookings', __name__)

@bookings.route('/cancel-booking/<int:booking_id>', methods=['POST'])
@jwt_required()
def cancel_booking(booking_id):
    current_user_id = get_jwt_identity()
    booking = Booking.query.get_or_404(booking_id)
    
    # Authorization check
    if booking.user_id != current_user_id and not User.query.get(current_user_id).is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Refund calculation logic
    days_until_checkin = (booking.check_in - datetime.utcnow()).days
    refund_percentage = max(
        0,
        min(
            100,  # Full refund if >14 days
            100 - (max(0, 14 - days_until_checkin) * 10  # 10% penalty per day
        )
    )
    refund_amount = math.floor(booking.total_price * (refund_percentage / 100))
    
    # Process refund if paid
    if booking.payment_id:
        try:
            stripe.Refund.create(
                payment_intent=booking.payment_id,
                amount=refund_amount * 100  # Convert to cents
            )
            refund_processed = True
        except Exception as e:
            refund_processed = False
    else:
        refund_processed = False
    
    # Update records
    booking.status = 'cancelled'
    booking.refund_amount = refund_amount
    booking.refund_processed = refund_processed
    booking.cancelled_at = datetime.utcnow()
    
    # Mark room as available
    Room.query.filter_by(id=booking.room_id).update({'is_available': True})
    
    db.session.commit()
    
    return jsonify({
        "message": "Booking cancelled",
        "refund_amount": refund_amount,
        "refund_processed": refund_processed
    }), 200
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from itsdangerous import URLSafeTimedSerializer
from app import db, mail
from flask_mail import Message
from models import User
from functools import wraps
import os

auth = Blueprint('auth', __name__)
serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY'))

# Helper decorator for token verification
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({"error": "Token is missing"}), 401
        try:
            email = serializer.loads(
                token,
                max_age=3600  # 1 hour expiration
            )
        except:
            return jsonify({"error": "Invalid or expired token"}), 401
        return f(email, *args, **kwargs)
    return decorated

@auth.route('/request-password-reset', methods=['POST'])
def request_reset():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"message": "If this email exists, a reset link was sent"}), 200
    
    token = serializer.dumps(email)
    reset_url = f"{request.host_url}reset-password?token={token}"
    
    msg = Message(
        "Nexus Password Reset",
        sender="no-reply@nexus.com",
        recipients=[email]
    )
    msg.body = f"""To reset your password, visit:
{reset_url}

This link expires in 1 hour."""
    
    mail.send(msg)
    return jsonify({"message": "Reset link sent"}), 200

@auth.route('/reset-password', methods=['POST'])
@token_required
def reset_password(email):
    new_password = request.json.get('password')
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    user.password_hash = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({"message": "Password updated successfully"}), 200
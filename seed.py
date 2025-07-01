from app import db, User, Hotel, Room
from werkzeug.security import generate_password_hash

def reset_db():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        # Create admin
        admin = User(
            username='admin',
            email='admin@nexus.com',
            role='admin'
        )
        admin.set_password('Admin123!')  # Proper hashing
        db.session.add(admin)
        
        # Add sample hotels/rooms (from your existing seed logic)
        # ...
        
        db.session.commit()
        print("Database reset complete")

if __name__ == '__main__':
    reset_db()
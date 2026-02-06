from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    student_number = db.Column(db.String(8), unique=True, nullable=False)
    id_number = db.Column(db.String(13), unique=True, nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    password_hash = db.Column(db.String(255))  # Increased for PostgreSQL
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    bookings = db.relationship('Booking', backref='user', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='user', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.email}>'

class Accommodation(db.Model):
    __tablename__ = 'accommodation'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200), nullable=False)
    room_type = db.Column(db.String(50), nullable=False)
    price_per_month = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    current_occupancy = db.Column(db.Integer, default=0, nullable=False)
    image_filename = db.Column(db.String(500))  # Increased to 500 for Cloudinary URLs
    amenities = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    bookings = db.relationship('Booking', backref='accommodation', lazy=True, cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='accommodation', lazy=True, cascade='all, delete-orphan')
    favorites = db.relationship('Favorite', backref='accommodation', lazy=True, cascade='all, delete-orphan')
    
    def get_amenities_list(self):
        if self.amenities:
            try:
                return json.loads(self.amenities)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_amenities_list(self, amenities_list):
        self.amenities = json.dumps(amenities_list)
    
    def available_spots(self):
        return max(0, self.capacity - self.current_occupancy)
    
    def average_rating(self):
        if not self.reviews:
            return 0
        return round(sum(r.rating for r in self.reviews) / len(self.reviews), 1)
    
    def is_full(self):
        return self.current_occupancy >= self.capacity
    
    def __repr__(self):
        return f'<Accommodation {self.title}>'

class Booking(db.Model):
    __tablename__ = 'booking'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accommodation_id = db.Column(db.Integer, db.ForeignKey('accommodation.id'), nullable=False)
    duration = db.Column(db.String(20), nullable=False)
    months = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='approved', nullable=False)
    stripe_session_id = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Booking {self.id}>'

class Review(db.Model):
    __tablename__ = 'review'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accommodation_id = db.Column(db.Integer, db.ForeignKey('accommodation.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'accommodation_id', name='unique_review'),)
    
    def __repr__(self):
        return f'<Review {self.id}>'

class Favorite(db.Model):
    __tablename__ = 'favorite'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    accommodation_id = db.Column(db.Integer, db.ForeignKey('accommodation.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('user_id', 'accommodation_id', name='unique_favorite'),)
    
    def __repr__(self):
        return f'<Favorite {self.id}>'
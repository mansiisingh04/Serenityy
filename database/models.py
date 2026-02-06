from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    """User model for authentication and user information"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    profile_picture = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    medications = db.relationship('Medication', backref='user', lazy=True, cascade='all, delete-orphan')
    health_logs = db.relationship('HealthLog', backref='user', lazy=True, cascade='all, delete-orphan')
    emergency_contacts = db.relationship('EmergencyContact', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.email}>'


class Medication(db.Model):
    """Medication model for tracking user medications"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(50), nullable=False) # daily, twice_daily, weekly, etc.
    time = db.Column(db.String(20), nullable=False) # Time of day to take medication
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    logs = db.relationship('MedicationLog', backref='medication', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Medication {self.name}>'


class MedicationLog(db.Model):
    """Log of medication doses scheduled and taken"""
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medication.id'), nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    taken = db.Column(db.Boolean, default=False)
    taken_time = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    def __repr__(self):
        status = "Taken" if self.taken else "Not Taken"
        return f'<MedicationLog {self.medication.name} - {status}>'


class HealthLog(db.Model):
    """User health logs for tracking mood, pain, and other health metrics"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    mood = db.Column(db.String(20)) # great, good, okay, bad, terrible
    pain_level = db.Column(db.Integer) # 0-10 scale
    notes = db.Column(db.Text)
    
    def __repr__(self):
        return f'<HealthLog {self.user.name} - {self.timestamp.strftime("%Y-%m-%d")}>'


class EmergencyContact(db.Model):
    """Emergency contacts for the user"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    is_primary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<EmergencyContact {self.name}>'


class DailyTip(db.Model):
    """Daily health tips for users"""
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50)) # general, medication, exercise, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DailyTip {self.id}>'
import os
import json
import uuid
from datetime import datetime
from flask_login import UserMixin

# Storage paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'storage', 'data')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
MEDICATIONS_FILE = os.path.join(DATA_DIR, 'medications.json')
MED_LOGS_FILE = os.path.join(DATA_DIR, 'medication_logs.json')
HEALTH_LOGS_FILE = os.path.join(DATA_DIR, 'health_logs.json')
EMERGENCY_CONTACTS_FILE = os.path.join(DATA_DIR, 'emergency_contacts.json')

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize data files if they don't exist
def init_data_files():
    for file_path in [USERS_FILE, MEDICATIONS_FILE, MED_LOGS_FILE, HEALTH_LOGS_FILE, EMERGENCY_CONTACTS_FILE]:
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump([], f)

init_data_files()

# Health tips for the application
HEALTH_TIPS = [
    "Try to walk for at least 30 minutes each day.",
    "Stay hydrated! Drink at least 8 glasses of water daily.",
    "Eating colorful fruits and vegetables helps maintain good health.",
    "Don't forget to take your medications as prescribed.",
    "Regular social interaction is important for mental health.",
    "Stretching in the morning can help reduce stiffness.",
    "Regular blood pressure monitoring helps prevent health complications.",
    "Schedule regular check-ups with your doctor.",
    "Meditation and deep breathing can help reduce stress.",
    "Getting 7-8 hours of sleep is essential for good health.",
    "Limit salt and sugar intake for better heart health.",
    "Maintain a healthy weight through diet and exercise.",
    "Puzzles and brain games help keep your mind sharp.",
    "Stay up to date with vaccinations, including annual flu shots.",
    "Regular eye exams are important, especially as you age."
]

# User model compatible with Flask-Login
class User(UserMixin):
    def __init__(self, id, email, name, profile_picture=None, created_at=None):
        self.id = id
        self.email = email
        self.name = name
        self.profile_picture = profile_picture
        self.created_at = created_at or datetime.now().isoformat()
    
    def get_id(self):
        return self.id
    
    @classmethod
    def get(cls, user_id):
        """Get user by ID"""
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
            for user in users:
                if user['id'] == user_id:
                    return cls(**user)
        return None
    
    @classmethod
    def find_by_email(cls, email):
        """Find user by email"""
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
            for user in users:
                if user['email'] == email:
                    return cls(**user)
        return None
    
    @classmethod
    def create(cls, email, name, profile_picture=None):
        """Create a new user"""
        user_id = str(uuid.uuid4())
        new_user = {
            'id': user_id,
            'email': email,
            'name': name,
            'profile_picture': profile_picture,
            'created_at': datetime.now().isoformat()
        }
        
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
        
        users.append(new_user)
        
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        
        return cls(**new_user)
    
    def get_medications(self):
        """Get all medications for this user"""
        with open(MEDICATIONS_FILE, 'r') as f:
            medications = json.load(f)
            return [med for med in medications if med['user_id'] == self.id]
    
    def get_emergency_contacts(self):
        """Get all emergency contacts for this user"""
        with open(EMERGENCY_CONTACTS_FILE, 'r') as f:
            contacts = json.load(f)
            return [contact for contact in contacts if contact['user_id'] == self.id]

# Medication functions
def add_medication(user_id, name, dosage, frequency, time, start_date, end_date=None, notes=None):
    """Add a medication for a user"""
    medication_id = str(uuid.uuid4())
    
    # Convert datetime objects to ISO format strings for JSON serialization
    if isinstance(start_date, datetime):
        start_date = start_date.isoformat()
    
    if end_date and isinstance(end_date, datetime):
        end_date = end_date.isoformat()
    
    new_medication = {
        'id': medication_id,
        'user_id': user_id,
        'name': name,
        'dosage': dosage,
        'frequency': frequency,
        'time': time,
        'start_date': start_date,
        'end_date': end_date,
        'notes': notes,
        'created_at': datetime.now().isoformat()
    }
    
    with open(MEDICATIONS_FILE, 'r') as f:
        medications = json.load(f)
    
    medications.append(new_medication)
    
    with open(MEDICATIONS_FILE, 'w') as f:
        json.dump(medications, f, indent=2)
    
    return new_medication

def get_medication(medication_id):
    """Get medication by ID"""
    with open(MEDICATIONS_FILE, 'r') as f:
        medications = json.load(f)
        for med in medications:
            if med['id'] == medication_id:
                return med
    return None

def delete_medication(medication_id):
    """Delete a medication and its associated logs"""
    # Delete the medication
    with open(MEDICATIONS_FILE, 'r') as f:
        medications = json.load(f)
    
    # Find the medication index
    medication_index = None
    for i, med in enumerate(medications):
        if med['id'] == medication_id:
            medication_index = i
            break
    
    # If medication found, remove it
    if medication_index is not None:
        deleted_medication = medications.pop(medication_index)
        
        # Save updated medications list
        with open(MEDICATIONS_FILE, 'w') as f:
            json.dump(medications, f, indent=2)
        
        # Also delete associated medication logs
        with open(MED_LOGS_FILE, 'r') as f:
            logs = json.load(f)
        
        # Filter out logs for this medication
        updated_logs = [log for log in logs if log['medication_id'] != medication_id]
        
        # Save updated logs
        with open(MED_LOGS_FILE, 'w') as f:
            json.dump(updated_logs, f, indent=2)
        
        return deleted_medication
    
    return None

# Medication log functions
def add_medication_log(medication_id=None, scheduled_time=None, taken=False, taken_time=None, notes=None, user_id=None, medication_name=None, timestamp=None):
    """Add a medication log"""
    log_id = str(uuid.uuid4())
    new_log = {
        'id': log_id,
        'medication_id': medication_id,
        'scheduled_time': scheduled_time,
        'taken': taken,
        'taken_time': taken_time or (timestamp if taken else None),
        'notes': notes,
        'user_id': user_id,
        'medication_name': medication_name,
        'timestamp': timestamp or datetime.now().isoformat()
    }
    
    with open(MED_LOGS_FILE, 'r') as f:
        logs = json.load(f)
    
    logs.append(new_log)
    
    with open(MED_LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=2)
    
    return new_log

def get_medication_logs(medication_id, limit=None):
    """Get medication logs for a medication"""
    with open(MED_LOGS_FILE, 'r') as f:
        logs = json.load(f)
        filtered_logs = [log for log in logs if log['medication_id'] == medication_id]
        
    # Sort by scheduled time (newest first)
    filtered_logs.sort(key=lambda x: x['scheduled_time'], reverse=True)
    
    if limit:
        filtered_logs = filtered_logs[:limit]
    
    return filtered_logs

# Health log functions
def add_health_log(user_id, mood, pain_level=None, notes=None, energy_level=None, sleep_quality=None, 
                   appetite=None, mobility=None, heart_rate=None, breathing_difficulty=None, 
                   hydration_level=None, medication_taken=None, bowel_movement=None):
    """Add a health log for a user"""
    log_id = str(uuid.uuid4())
    new_log = {
        'id': log_id,
        'user_id': user_id,
        'mood': mood,
        'pain_level': pain_level,
        'notes': notes,
        'timestamp': datetime.now().isoformat(),
        'energy_level': energy_level,
        'sleep_quality': sleep_quality,
        'appetite': appetite,
        'mobility': mobility,
        'heart_rate': heart_rate,
        'breathing_difficulty': breathing_difficulty,
        'hydration_level': hydration_level,
        'medication_taken': medication_taken,
        'bowel_movement': bowel_movement
    }
    
    with open(HEALTH_LOGS_FILE, 'r') as f:
        logs = json.load(f)
    
    logs.append(new_log)
    
    with open(HEALTH_LOGS_FILE, 'w') as f:
        json.dump(logs, f, indent=2)
    
    return new_log

def get_recent_health_logs(user_id, limit=10):
    """Get recent health logs for a user"""
    with open(HEALTH_LOGS_FILE, 'r') as f:
        logs = json.load(f)
        filtered_logs = [log for log in logs if log['user_id'] == user_id]
    
    # Sort by timestamp (newest first)
    filtered_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    if limit:
        filtered_logs = filtered_logs[:limit]
    
    return filtered_logs

# Emergency contact functions
def add_emergency_contact(user_id, name, relationship, phone, email=None, is_primary=False):
    """Add an emergency contact for a user"""
    contact_id = str(uuid.uuid4())
    new_contact = {
        'id': contact_id,
        'user_id': user_id,
        'name': name,
        'relationship': relationship,
        'phone': phone,
        'email': email,
        'is_primary': is_primary,
        'created_at': datetime.now().isoformat()
    }
    
    with open(EMERGENCY_CONTACTS_FILE, 'r') as f:
        contacts = json.load(f)
    
    # If this is a primary contact, set existing primary contacts to non-primary
    if is_primary:
        for contact in contacts:
            if contact['user_id'] == user_id and contact['is_primary']:
                contact['is_primary'] = False
    
    contacts.append(new_contact)
    
    with open(EMERGENCY_CONTACTS_FILE, 'w') as f:
        json.dump(contacts, f, indent=2)
    
    return new_contact

def delete_emergency_contact(contact_id):
    """Delete an emergency contact by ID"""
    with open(EMERGENCY_CONTACTS_FILE, 'r') as f:
        contacts = json.load(f)
    
    # Find the contact index
    contact_index = None
    for i, contact in enumerate(contacts):
        if contact['id'] == contact_id:
            contact_index = i
            break
    
    # If contact found, remove it
    if contact_index is not None:
        deleted_contact = contacts.pop(contact_index)
        
        # Save updated contacts list
        with open(EMERGENCY_CONTACTS_FILE, 'w') as f:
            json.dump(contacts, f, indent=2)
        
        return deleted_contact
    
    return None
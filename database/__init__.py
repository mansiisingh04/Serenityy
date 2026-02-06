# Database initialization
from .models import db

# Import models to make them available when importing the package
from .models import User, Medication, MedicationLog, HealthLog, EmergencyContact, DailyTip
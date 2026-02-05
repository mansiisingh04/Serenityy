import os
import json
from datetime import datetime, timedelta
import random
import time
import hashlib
import threading
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_session import Session as FlaskSession
from authlib.integrations.flask_client import OAuth
import google.generativeai as genai
from dotenv import load_dotenv
from utils.storage import User, add_medication, get_medication, add_medication_log, get_medication_logs
from utils.storage import add_health_log, get_recent_health_logs, add_emergency_contact, delete_medication, HEALTH_TIPS
from utils.storage import delete_emergency_contact

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

FlaskSession(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

oauth = OAuth(app)

print(f"GOOGLE_CLIENT_ID: {os.getenv('GOOGLE_CLIENT_ID')}")
print(f"GOOGLE_CLIENT_SECRET: {os.getenv('GOOGLE_CLIENT_SECRET', 'Not loaded')[:5]}...")

google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile',
        'redirect_uri': 'http://127.0.0.1:5000/callback'
    },
)

genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

response_cache = {}
QUICK_RESPONSES = {
    "hello": "Hello! How are you feeling today?",
    "hi": "Hi there! How can I assist you today?",
    "good morning": "Good morning! I hope you're having a wonderful day.",
    "good afternoon": "Good afternoon! How are you doing today?",
    "good evening": "Good evening! How has your day been?",
    "how are you": "I'm doing well, thank you for asking! How are you feeling today?",
    "thank you": "You're welcome! Is there anything else I can help you with?",
    "goodbye": "Goodbye! Take care and have a wonderful day.",
    "bye": "Bye for now! Don't hesitate to chat again if you need anything.",
    "help": "I'm here to help! I can assist with medication reminders, health tracking, emergency contacts, and answer health-related questions. What would you like help with?",
}

HEALTH_KNOWLEDGE = {
    "headache": {
        "advice": "For headaches, it's important to stay hydrated and rest in a quiet, dark room if possible.",
        "medications": ["acetaminophen (Tylenol)", "ibuprofen (Advil, Motrin)", "aspirin"]
    },
    "cold": {
        "advice": "Rest, stay hydrated, and consider over-the-counter medications for symptom relief.",
        "medications": ["acetaminophen", "decongestants", "cough suppressants"]
    },
    "fever": {
        "advice": "Stay hydrated and rest. If fever persists over 101°F (38.3°C) for more than two days, consult a doctor.",
        "medications": ["acetaminophen (Tylenol)", "ibuprofen (Advil, Motrin)"]
    },
    "allergies": {
        "advice": "Avoid triggers if known. Consider over-the-counter antihistamines for relief.",
        "medications": ["loratadine (Claritin)", "cetirizine (Zyrtec)", "diphenhydramine (Benadryl)"]
    }
}

pending_responses = {}

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        daily_tip = get_daily_tip() if 'get_daily_tip' in globals() else random.choice(HEALTH_TIPS)
        return render_template('public_dashboard.html', daily_tip=daily_tip)

@app.route('/login')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('authorize'))

@app.route('/authorize')
def authorize():
    redirect_uri = google.client_kwargs.get('redirect_uri')
    return google.authorize_redirect(redirect_uri=redirect_uri)

@app.route('/callback')
def callback():
    try:
        redirect_uri = google.client_kwargs.get('redirect_uri')
        token = google.authorize_access_token()
        resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
        user_info = resp.json()
        
        user = User.find_by_email(user_info['email'])
        if not user:
            user = User.create(
                email=user_info['email'],
                name=user_info['name'],
                profile_picture=user_info.get('picture')
            )
        
        login_user(user)
        if 'oauth_redirect_uri' in session:
            session.pop('oauth_redirect_uri')
            
        return redirect(url_for('dashboard'))
    except Exception as e:
        app.logger.error(f"OAuth callback error: {e}")
        flash("Authentication failed. Please try again.", "error")
        return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now()
    medications = current_user.get_medications()
    today_meds = [med for med in medications if is_medication_due_today(med)]
    health_logs = get_recent_health_logs(current_user.id, limit=5)
    
    for log in health_logs:
        if isinstance(log['timestamp'], str):
            log['timestamp'] = datetime.fromisoformat(log['timestamp'])
    
    daily_tip = get_daily_tip()
    
    return render_template('dashboard.html',
                          now=today,
                          medications=today_meds,
                          health_logs=health_logs,
                          daily_tip=daily_tip)

@app.route('/medications')
@login_required
def medications():
    medications_list = current_user.get_medications()
    
    for medication in medications_list:
        if isinstance(medication['start_date'], datetime):
            medication['start_date'] = medication['start_date'].isoformat()
        if medication.get('end_date') and isinstance(medication['end_date'], datetime):
            medication['end_date'] = medication['end_date'].isoformat()
    
    return render_template('medications.html', medications=medications_list)

@app.route('/add_medication', methods=['POST'])
@login_required
def add_medication_route():
    data = request.json
    print(f"Received medication data: {data}")
    
    try:
        start_date = datetime.strptime(data.get('start_date'), '%Y-%m-%d')
        
        end_date = None
        if data.get('end_date'):
            end_date = datetime.strptime(data.get('end_date'), '%Y-%m-%d')
        
        new_medication = add_medication(
            user_id=current_user.id,
            name=data.get('name'),
            dosage=data.get('dosage'),
            frequency=data.get('frequency'),
            time=data.get('time'),
            start_date=start_date,
            end_date=end_date,
            notes=data.get('notes')
        )
        
        if new_medication:
            if isinstance(new_medication['start_date'], datetime):
                new_medication['start_date'] = new_medication['start_date'].isoformat()
            if new_medication.get('end_date') and isinstance(new_medication['end_date'], datetime):
                new_medication['end_date'] = new_medication['end_date'].isoformat()
                
            create_medication_logs(new_medication)
            return jsonify({'success': True, 'medication': new_medication})
        else:
            return jsonify({'success': False, 'error': 'Failed to add medication'}), 500
            
    except Exception as e:
        print(f"Error adding medication: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_medication/<medication_id>', methods=['POST'])
@login_required
def delete_medication_route(medication_id):
    try:
        medication = get_medication(medication_id)
        
        if not medication:
            return jsonify({'success': False, 'error': 'Medication not found'}), 404
            
        if medication['user_id'] != current_user.id:
            return jsonify({'success': False, 'error': 'Not authorized to delete this medication'}), 403
        
        deleted_medication = delete_medication(medication_id)
        
        if deleted_medication:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete medication'}), 500
            
    except Exception as e:
        print(f"Error deleting medication: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/mark_medication_taken/<medication_id>', methods=['POST'])
@login_required
def mark_medication_taken(medication_id):
    try:
        medication = get_medication(medication_id)
        
        if not medication:
            return jsonify({'success': False, 'error': 'Medication not found'}), 404
            
        now = datetime.now()
        add_medication_log(
            user_id=current_user.id,
            medication_id=medication_id,
            medication_name=medication['name'],
            taken=True,
            timestamp=now.isoformat(),
            notes="Marked as taken via dashboard"
        )
        
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error marking medication as taken: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health_check')
@login_required
def health_check():
    health_logs = get_recent_health_logs(current_user.id, limit=10)
    
    for log in health_logs:
        if isinstance(log['timestamp'], str):
            log['timestamp'] = datetime.fromisoformat(log['timestamp'])
    
    return render_template('health_check.html', health_logs=health_logs)

@app.route('/submit_health_check', methods=['POST'])
@login_required
def submit_health_check():
    try:
        data = request.json
        
        health_log = {
            "timestamp": datetime.now(),
            "mood": data.get('mood'),
            "energy_level": data.get('energy_level'),
            "sleep_quality": data.get('sleep_quality'),
            "appetite": data.get('appetite'),
            "mobility": data.get('mobility'),
            "heart_rate": data.get('heart_rate'),
            "breathing": data.get('breathing', None),  # Use 'breathing' instead of 'breathing_difficulty'
            "hydration_level": data.get('hydration_level'),
            "medication_taken": data.get('medication_taken'),
            "notes": data.get('notes')
        }
        
        add_health_log(
            user_id=current_user.id,
            mood=data.get('mood'),
            energy_level=data.get('energy_level'),
            sleep_quality=data.get('sleep_quality'),
            appetite=data.get('appetite'),
            mobility=data.get('mobility'),
            heart_rate=data.get('heart_rate'),
            breathing_difficulty=data.get('breathing'),
            hydration_level=data.get('hydration_level'),
            medication_taken=data.get('medication_taken'),
            notes=data.get('notes')
        )
        
        return jsonify({"success": True})
    except Exception as e:
        app.logger.error(f"Error submitting health check: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/emergency_contacts')
@login_required
def emergency_contacts():
    contacts = current_user.get_emergency_contacts()
    return render_template('emergency_contacts.html', emergency_contacts=contacts)

@app.route('/add_emergency_contact', methods=['POST'])
@login_required
def add_emergency_contact_route():
    data = request.json
    
    add_emergency_contact(
        user_id=current_user.id,
        name=data.get('name'),
        relationship=data.get('relationship'),
        phone=data.get('phone'),
        email=data.get('email') if data.get('email') else None,
        is_primary=data.get('is_primary')
    )
    
    return jsonify({'success': True})

@app.route('/delete_emergency_contact/<contact_id>', methods=['POST'])
@login_required
def delete_emergency_contact_route(contact_id):
    try:
        # Get all contacts first to verify ownership
        contacts = current_user.get_emergency_contacts()
        
        # Check if the contact belongs to the current user
        if not any(contact['id'] == contact_id for contact in contacts):
            return jsonify({'success': False, 'error': 'Not authorized to delete this contact'}), 403
        
        deleted_contact = delete_emergency_contact(contact_id)
        
        if deleted_contact:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete contact'}), 500
            
    except Exception as e:
        app.logger.error(f"Error deleting emergency contact: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    print("==== API CHAT ENDPOINT HIT ====")
    print(f"Request: Method={request.method}, ContentType={request.content_type}, JSON={request.is_json}")
    
    try:
        print(f"Raw request data: {request.data}")
        if request.is_json:
            print(f"JSON data: {request.get_json()}")
    except Exception as e:
        print(f"Error parsing request data: {e}")
    
    if '_id' not in session:
        print("No session ID found - creating a new session ID")
        session['_id'] = hashlib.md5(os.urandom(16)).hexdigest()
        
    session_id = session.get('_id')
    print(f"Session ID: {session_id}")
    
    data = request.get_json() if request.is_json else {}
    user_message = data.get('message', '').lower() if data else ''
    print(f"Received message: {user_message}")
    
    for keyword, response in QUICK_RESPONSES.items():
        if keyword in user_message:
            print(f"Quick response matched: {keyword}")
            return jsonify({'response': response, 'is_emergency': False})
    
    emergency_keywords = ['emergency', 'help me', 'severe pain', 'chest pain', 'can\'t breathe', 
                         'heart attack', 'stroke', 'bleeding', 'unconscious', 'fell and can\'t get up']
    
    for keyword in emergency_keywords:
        if keyword in user_message:
            print(f"Emergency keyword matched: {keyword}")
            emergency_response = (
                "⚠️ This sounds like an emergency! Please call 911 or your local emergency number immediately. "
                "Don't wait for a response here."
            )
            return jsonify({'response': emergency_response, 'is_emergency': True})
    
    for condition, info in HEALTH_KNOWLEDGE.items():
        if condition in user_message or (condition == "headache" and "medicine for headache" in user_message):
            print(f"Health knowledge matched: {condition}")
            response = f"{info['advice']} Common medications include: {', '.join(info['medications'])}."
            return jsonify({'response': response, 'is_emergency': False})
    
    print("No quick/emergency/health matches, proceeding to Gemini API")
    
    try:
        print("Initializing Gemini model...")
        api_key = os.getenv("GEMINI_API_KEY")
        print(f"API key available: {bool(api_key)} (Key starts with: {api_key[:4] if api_key else 'None'}...)")
        
        genai.configure(api_key=api_key)
        
        model = genai.GenerativeModel('models/gemini-2.0-flash')
        print(f"Using model: models/gemini-2.0-flash")
        
        prompt = f"""You are a helpful health assistant for seniors. 
        Please provide a clear, concise, and compassionate response to the following question.
        Focus on providing accurate health information, but always remind users to consult healthcare professionals for medical advice.
        
        User question: {user_message}
        """
        
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
        
        print("Sending request to Gemini API...")
        try:
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            print("Gemini API response received successfully")
            response_text = response.text
            print(f"Response first 50 chars: {response_text[:50]}...")
            
            return jsonify({'response': response_text, 'is_emergency': False})
            
        except Exception as api_error:
            print(f"Error during API call: {api_error}")
            return jsonify({
                'response': f"I'm sorry, I couldn't process your request due to an API error: {str(api_error)[:100]}...",
                'is_emergency': False,
                'error': True
            })
    
    except Exception as e:
        print(f"ERROR generating AI response: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'response': "I'm sorry, I couldn't process your request at this time. Please try again later.",
            'is_emergency': False,
            'error': True
        })

@app.route('/api/check_pending_response', methods=['GET'])
def check_pending_response():
    session_id = session.get('_id')
    if not session_id or session_id not in pending_responses:
        return jsonify({
            'status': 'error',
            'response': 'No pending response found'
        })
    
    response_data = pending_responses[session_id]
    
    if response_data.get('status') == 'ready':
        response_to_return = response_data.copy()
        cleanup_time = datetime.now() - timedelta(minutes=10)
        for sess_id in list(pending_responses.keys()):
            timestamp = datetime.fromisoformat(pending_responses[sess_id]['timestamp'])
            if timestamp < cleanup_time:
                del pending_responses[sess_id]
        return jsonify(response_to_return)
    
    return jsonify(response_data)

def is_medication_due_today(medication):
    today = datetime.now().date()
    start_date = datetime.fromisoformat(medication['start_date']).date() if isinstance(medication['start_date'], str) else medication['start_date']
    if start_date > today:
        return False
    
    if medication['end_date']:
        end_date = datetime.fromisoformat(medication['end_date']).date() if isinstance(medication['end_date'], str) else medication['end_date']
        if end_date < today:
            return False
    
    if medication['frequency'] in ['daily', 'twice_daily', 'three_times_daily', 'four_times_daily']:
        return True
    
    if medication['frequency'] == 'weekly':
        days_since_start = (today - start_date).days
        return days_since_start % 7 == 0
    
    if medication['frequency'] == 'biweekly':
        days_since_start = (today - start_date).days
        return days_since_start % 14 == 0
    
    if medication['frequency'] == 'monthly':
        return today.day == start_date.day
    
    return False

def create_medication_logs(medication):
    today = datetime.now().date()
    medication_id = medication['id']
    
    for i in range(7):
        check_date = today + timedelta(days=i)
        start_date = datetime.fromisoformat(medication['start_date']).date() if isinstance(medication['start_date'], str) else medication['start_date']
        if start_date > check_date:
            continue
        
        if medication['end_date']:
            end_date = datetime.fromisoformat(medication['end_date']).date() if isinstance(medication['end_date'], str) else medication['end_date']
            if end_date < check_date:
                continue
            
        if medication['frequency'] == 'daily':
            time_parts = medication['time'].split(':')
            log_time = datetime.combine(check_date, 
                                       datetime.min.time().replace(hour=int(time_parts[0]), 
                                                                 minute=int(time_parts[1]))).isoformat()
            
            add_medication_log(
                medication_id=medication_id,
                scheduled_time=log_time,
                taken=False
            )
            
        elif medication['frequency'] in ['twice_daily', 'three_times_daily', 'four_times_daily']:
            time_parts = medication['time'].split(':')
            log_time = datetime.combine(check_date, 
                                       datetime.min.time().replace(hour=int(time_parts[0]), 
                                                                 minute=int(time_parts[1]))).isoformat()
            
            add_medication_log(
                medication_id=medication_id,
                scheduled_time=log_time,
                taken=False
            )
            
        elif medication['frequency'] == 'weekly':
            days_since_start = (check_date - start_date).days
            if days_since_start % 7 == 0:
                time_parts = medication['time'].split(':')
                log_time = datetime.combine(check_date, 
                                           datetime.min.time().replace(hour=int(time_parts[0]), 
                                                                     minute=int(time_parts[1]))).isoformat()
                
                add_medication_log(
                    medication_id=medication_id,
                    scheduled_time=log_time,
                    taken=False
                )

def get_daily_tip():
    return random.choice(HEALTH_TIPS)

if __name__ == '__main__':
    app.run(debug=True)






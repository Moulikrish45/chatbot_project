from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
import re

app = Flask(__name__)

# Configuring the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Defining a simple Lead model
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_required = db.Column(db.String(100), nullable=False)

# Create the database
with app.app_context():
    db.create_all()

# Simple state management
conversation_state = {}

@app.route('/chatbot', methods=['POST'])
def chatbot():
    global conversation_state
    user_message = request.json.get('message').strip().lower()
    user_id = request.remote_addr  # Example: using IP address as a simple user identifier

    # Initialize state for new user session
    if user_id not in conversation_state:
        conversation_state[user_id] = {'step': None}

    # Handle the conversation state and respond accordingly
    if "service" in user_message or "need" in user_message:
        conversation_state[user_id]['step'] = 'service_selection'
        return jsonify({"message": "What type of service do you need?", 
                        "options": ["Plumbing", "Electrical", "HVAC"]})
    
    elif user_message in ["plumbing", "electrical", "hvac"]:
        conversation_state[user_id]['step'] = 'service_selected'
        conversation_state[user_id]['service_required'] = user_message.capitalize()
        return jsonify({"message": f"Great! We have contractors available for {user_message.capitalize()} services. How would you like to proceed?", 
                        "options": ["Fill in a Form", "Call a Contractor", "Set an Appointment"]})
    
    elif conversation_state[user_id]['step'] == 'service_selected' and "form" in user_message:
        conversation_state[user_id]['step'] = 'form_filling'
        return jsonify({"message": "Please provide your name, email, and phone number to proceed with the form submission."})
    
    elif conversation_state[user_id]['step'] == 'service_selected' and "call" in user_message:
        return jsonify({"message": "Please select a contractor from the list provided earlier and submit their name to receive the phone number."})
    
    elif conversation_state[user_id]['step'] == 'service_selected' and "appointment" in user_message:
        conversation_state[user_id]['step'] = 'appointment_scheduling'
        return jsonify({"message": "Please provide the appointment time and select contractors from the list provided earlier."})
    
    elif conversation_state[user_id]['step'] == 'form_filling':
        user_details = parse_user_details(user_message)
        if user_details:
            name, email, phone = user_details
            service_required = conversation_state[user_id].get('service_required')
            return capture_lead_data(name, email, phone, service_required)
        else:
            return jsonify({"message": "I couldn't parse your details. Please provide your name, email, and phone number in the format: Name, Email, Phone."})

    # Default fallback
    else:
        return jsonify({"message": "I didn't quite catch that. Can you please specify the service or action you'd like to take?"})

def parse_user_details(message):
    """Parse user details from a message using a regular expression."""
    match = re.match(r'^\s*(?P<name>[a-zA-Z\s]+)\s*,\s*(?P<email>[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*,\s*(?P<phone>\d{10,15})\s*$', message)
    if match:
        return match.group('name'), match.group('email'), match.group('phone')
    return None

def capture_lead_data(name, email, phone, service_required):
    """Capture the lead data and save it to the database."""
    new_lead = Lead(name=name, email=email, phone=phone, service_required=service_required)
    db.session.add(new_lead)
    db.session.commit()
    return jsonify({"message": f"Thank you, {name}! Your details have been captured for {service_required}."})

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

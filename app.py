from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

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

@app.route('/capture_lead', methods=['POST'])
def capture_lead():
    data = request.json
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    service_required = data.get('service_required')

    if not all([name, email, phone, service_required]):
        return jsonify({"error": "All fields are required!"}), 400

    new_lead = Lead(name=name, email=email, phone=phone, service_required=service_required)
    db.session.add(new_lead)
    db.session.commit()

    return jsonify({"message": "Thank you! Your details have been captured."}), 201

@app.route('/service_options', methods=['POST'])
def service_options():
    data = request.json
    service_required = data.get('service_required')

    if not service_required:
        return jsonify({"error": "Service required is missing!"}), 400

    # Dummy data for contractors
    contractors = [
        {"name": "Contractor A", "phone": "123-456-7890"},
        {"name": "Contractor B", "phone": "234-567-8901"},
        {"name": "Contractor C", "phone": "345-678-9012"},
        {"name": "Contractor D", "phone": "456-789-0123"}
    ]

    # Provide options to the user
    response = {
        "message": f"We have contractors available for {service_required}. How would you like to proceed?",
        "options": [
            {"option": "Fill in a Form", "description": "Select up to four contractors and submit your information."},
            {"option": "Call a Contractor", "description": "Here are the numbers of available contractors you can call directly."},
            {"option": "Set an Appointment", "description": "Schedule an appointment with one or more contractors."}
        ],
        "contractors": contractors
    }

    return jsonify(response)

@app.route('/submit_form', methods=['POST'])
def submit_form():
    data = request.json
    selected_contractors = data.get('selected_contractors')
    user_details = data.get('user_details')

    if not selected_contractors or not user_details:
        return jsonify({"error": "Contractors and user details are required!"}), 400

    # Process form submission (Store in DB or send email, etc.)
    return jsonify({"message": "Your information has been submitted to the selected contractors."})

@app.route('/call_contractor', methods=['POST'])
def call_contractor():
    data = request.json
    selected_contractor = data.get('selected_contractor')

    if not selected_contractor:
        return jsonify({"error": "Please select a contractor to call!"}), 400

    # In a real application, here we could integrate with a VoIP service
    return jsonify({"message": f"Please call {selected_contractor['phone']} to speak with {selected_contractor['name']}."})

@app.route('/set_appointment', methods=['POST'])
def set_appointment():
    data = request.json
    selected_contractors = data.get('selected_contractors')
    appointment_time = data.get('appointment_time')

    if not selected_contractors or not appointment_time:
        return jsonify({"error": "Contractors and appointment time are required!"}), 400

    # Process appointment scheduling (Store in DB, send notifications, etc.)
    return jsonify({"message": "Your appointment has been scheduled with the selected contractors."})


@app.route('/welcome', methods=['GET'])
def welcome():
    return jsonify(message="Hi there! I'm here to help you connect with top-rated contractors. How can I assist you today?")

if __name__ == '__main__':
    app.run(debug=True)

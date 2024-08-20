from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import re
import openai
from chromadb import Client
from chromadb.config import Settings
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

# Initialize Flask and Database
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# GPT-4 API Initialization
openai.api_key = "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"

# ChromaDB Initialization for FAQ handling
chroma_client = Client(Settings(embedding_function=OpenAIEmbeddingFunction(api_key="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")))

class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_required = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

conversation_state = {}

# Load FAQ data and store in ChromaDB
def load_faq_data(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

faq_data = load_faq_data("faq_data.json")

for faq in faq_data:
    chroma_client.add_document(faq['question'], faq['answer'])

# Route to handle chatbot interactions
@app.route('/chatbot', methods=['POST'])
def chatbot():
    global conversation_state
    user_message = request.json.get('message').strip().lower()
    user_id = request.remote_addr

    if user_id not in conversation_state:
        conversation_state[user_id] = {'step': None}

    # FAQ Handling
    if 'faq' in user_message or 'question' in user_message:
        return faq()

    # Handle different steps of conversation
    if conversation_state[user_id]['step'] is None:
        conversation_state[user_id]['step'] = 'introduction'
        return jsonify({
            "message": "Hello! I am your service assistant. How can I help you today? You can upload an image or tell me what service you need.",
            "options": ["Upload Image", "Specify Service"]
        })

    elif conversation_state[user_id]['step'] == 'introduction':
        if "upload image" in user_message:
            conversation_state[user_id]['step'] = 'awaiting_image'
            return jsonify({"message": "Please click the 'Upload Image' button near the send button to upload an image of the problem you are facing."})
        elif "specify service" in user_message:
            conversation_state[user_id]['step'] = 'service_selection'
            return jsonify({"message": "What type of service do you need?", "options": ["Plumbing", "Electrical", "HVAC"]})
        else:
            return jsonify({"message": "I didn't quite catch that. Would you like to upload an image or specify the service?", 
                            "options": ["Upload Image", "Specify Service"]})

    elif conversation_state[user_id]['step'] == 'awaiting_image':
        return jsonify({"message": "Please click the 'Upload Image' button near the send button to upload an image."})

    elif conversation_state[user_id]['step'] == 'service_selection':
        if user_message in ["plumbing", "electrical", "hvac"]:
            conversation_state[user_id]['step'] = 'service_selected'
            conversation_state[user_id]['service_required'] = user_message.capitalize()
            return jsonify({
                "message": f"Great! We have contractors available for {user_message.capitalize()} services. How would you like to proceed?",
                "options": ["Fill in a Form", "Call a Contractor", "Set an Appointment"]
            })
        else:
            return jsonify({"message": "Please select a valid service option.", "options": ["Plumbing", "Electrical", "HVAC"]})

    elif conversation_state[user_id]['step'] == 'service_selected':
        if "form" in user_message:
            conversation_state[user_id]['step'] = 'form_filling'
            return jsonify({"message": "Please provide your name, email, and phone number to proceed with the form submission."})
        elif "call" in user_message:
            return jsonify({
                "message": "Here are the available contractors you can call:",
                "options": ["Contractor A: 123-456-7890", "Contractor B: 234-567-8901", "Contractor C: 345-678-9012", "Contractor D: 456-789-0123"]
            })
        elif "appointment" in user_message:
            conversation_state[user_id]['step'] = 'appointment_scheduling'
            return jsonify({
                "message": "Please provide the appointment time and select contractors from the list below:",
                "contractors": ["Contractor A", "Contractor B", "Contractor C", "Contractor D"],
                "example": "Example: 10 pm Contractor A"
            })
        else:
            return jsonify({"message": "Please select how you'd like to proceed.", "options": ["Fill in a Form", "Call a Contractor", "Set an Appointment"]})

    elif conversation_state[user_id]['step'] == 'appointment_scheduling':
        if any(contractor.lower() in user_message for contractor in ["contractor a", "contractor b", "contractor c", "contractor d"]):
            conversation_state[user_id]['step'] = 'completed'
            return jsonify({
                "message": "Your appointment has been scheduled successfully. Is there anything else I can assist you with?",
                "options": ["Yes, I have another issue", "No, that's all"]
            })
        else:
            return jsonify({"message": "Please provide the appointment time and select a contractor from the list provided earlier."})

    elif conversation_state[user_id]['step'] == 'form_filling':
        user_details = parse_user_details(user_message)
        if user_details:
            name, email, phone = user_details
            service_required = conversation_state[user_id].get('service_required')
            conversation_state[user_id]['step'] = 'completed'
            return capture_lead_data(name, email, phone, service_required)
        else:
            return jsonify({"message": "I couldn't parse your details. Please provide your name, email, and phone number in the format: Name, Email, Phone."})

    elif conversation_state[user_id]['step'] == 'completed':
        if "yes" in user_message:
            conversation_state[user_id]['step'] = 'introduction'
            return jsonify({
                "message": "How can I help you today? You can upload an image or tell me what service you need.",
                "options": ["Upload Image", "Specify Service"]
            })
        elif "no" in user_message or "thanks" in user_message:
            return jsonify({"message": "You're welcome! If you need any further assistance, feel free to reach out. Have a great day!"})
        else:
            return jsonify({
                "message": "Is there anything else I can assist you with?",
                "options": ["Yes, I have another issue", "No, that's all"]
            })

    else:
        return jsonify({"message": "I didn't quite catch that. Can you please specify the service or action you'd like to take?"})

# Helper function to parse user details
def parse_user_details(message):
    match = re.match(r'^\s*(?P<name>[a-zA-Z\s]+)\s*,\s*(?P<email>[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*,\s*(?P<phone>\d{10,15})\s*$', message)
    if match:
        return match.group('name'), match.group('email'), match.group('phone')
    return None

# Helper function to capture lead data
def capture_lead_data(name, email, phone, service_required):
    new_lead = Lead(name=name, email=email, phone=phone, service_required=service_required)
    db.session.add(new_lead)
    db.session.commit()
    return jsonify({
        "message": f"Thank you, {name}! Your details have been captured for {service_required}. Is there anything else I can assist you with?",
        "options": ["Yes, I have another issue", "No, that's all"]
    })

# Route to handle image upload
@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file"})
    if file:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process the image using GPT's API to understand the problem
        image_response = openai.Image.create(file=open(file_path, "rb"), purpose="image-analysis")
        identified_service = image_response['data']['service']  # Example, adjust based on API response
        
        conversation_state[request.remote_addr]['step'] = 'service_selection'
        conversation_state[request.remote_addr]['service_suggested'] = identified_service.capitalize()
        
        return jsonify({
            "message": f"Image received. Based on the image, it looks like you might need {identified_service} services. Is that correct?",
            "options": ["Yes", "No"]
        })

# Route to handle FAQ queries using GPT-4 and ChromaDB
@app.route('/faq', methods=['POST'])
def faq():
    user_question = request.json.get('question')
    
    # Retrieve relevant data from ChromaDB
    relevant_faqs = chroma_client.query(user_question, top_k=3)
    
    # Generate a response using GPT-4
    gpt_response = openai.Completion.create(
        engine="gpt-4",
        prompt=create_prompt(user_question, relevant_faqs),
        max_tokens=150
    )
    
    return jsonify({"response": gpt_response.choices[0].text.strip()})

def create_prompt(user_question, relevant_faqs):
    faq_texts = "\n".join([f"Q: {faq['question']}\nA: {faq['answer']}" for faq in relevant_faqs])
    return f"User asked: {user_question}\nRelevant FAQs:\n{faq_texts}\nAnswer:"

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

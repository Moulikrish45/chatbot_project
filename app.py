import os
import fitz  # PyMuPDF
import uuid
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import openai
import chromadb
from chromadb.utils import embedding_functions
from chromadb.config import Settings

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///leads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Set up OpenAI API key
openai.api_key = 'YOUR_OPENAI_API_KEY'  # Replace with your actual API key

# Initialize ChromaDB client
chroma_client = chromadb.Client(Settings(
    chroma_db_impl="duckdb+parquet",
    persist_directory="chroma_db"  # Directory to store the database
))

# Create or get existing collection
collection_name = "faq_collection"
collection = chroma_client.get_or_create_collection(name=collection_name)

# Define the Lead model for SQLite
class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    service_required = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

# Function to parse the PDF and store FAQs in a dictionary
def parse_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    faq_data = {}
    for page in doc:
        text = page.get_text()
        lines = text.splitlines()
        for i in range(len(lines)):
            if "Q:" in lines[i]:
                question = lines[i].replace("Q:", "").strip()
                if i + 1 < len(lines) and "A:" in lines[i + 1]:
                    answer = lines[i + 1].replace("A:", "").strip()
                    faq_data[question.lower()] = answer
                    # Store in ChromaDB
                    unique_id = str(uuid.uuid4())
                    embedding = create_embedding(question)
                    collection.add(
                        ids=[unique_id],
                        documents=[question],
                        metadatas=[{"answer": answer}],
                        embeddings=[embedding]
                    )
    return faq_data

# Function to create embeddings using OpenAI's API
def create_embedding(text):
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response['data'][0]['embedding']

# Load the FAQ data from the parsed PDF
faq_data = parse_pdf("path_to_your_pdf_file.pdf")  # Update with your actual path

# Initialize conversation state
conversation_state = {}

# Route for chatbot interaction
@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_input = request.json.get('message').strip().lower()
    user_id = request.remote_addr  # Using user's IP as a simple identifier

    if user_id not in conversation_state:
        conversation_state[user_id] = {'step': 'introduction'}

    current_step = conversation_state[user_id]['step']

    if current_step == 'introduction':
        response = {
            "message": "Hello! I’m here to help you connect with top-rated contractors. How can I assist you today?",
            "options": ["Ask a Question", "Upload an Image", "Specify Service Needed"]
        }
        conversation_state[user_id]['step'] = 'awaiting_choice'
        return jsonify(response)

    elif current_step == 'awaiting_choice':
        if user_input == 'ask a question':
            response = {"message": "Sure, what’s your question?"}
            conversation_state[user_id]['step'] = 'awaiting_question'
            return jsonify(response)
        elif user_input == 'upload an image':
            response = {"message": "Please upload an image related to your issue."}
            conversation_state[user_id]['step'] = 'awaiting_image'
            return jsonify(response)
        elif user_input == 'specify service needed':
            response = {
                "message": "Please specify the service you need.",
                "options": ["Plumbing", "Electrical", "HVAC", "Painting", "Roofing"]
            }
            conversation_state[user_id]['step'] = 'awaiting_service_selection'
            return jsonify(response)
        else:
            response = {
                "message": "I didn’t understand that. Please choose one of the options.",
                "options": ["Ask a Question", "Upload an Image", "Specify Service Needed"]
            }
            return jsonify(response)

    elif current_step == 'awaiting_question':
        user_question = user_input
        # First check for exact matches in parsed FAQ data
        for question, answer in faq_data.items():
            if question in user_question:
                conversation_state[user_id]['step'] = 'introduction'
                return jsonify({"response": answer})

        # If no exact match is found, use ChromaDB for RAG
        user_embedding = create_embedding(user_question)
        results = collection.query(
            query_embeddings=[user_embedding],
            n_results=3
        )
        if results['documents']:
            relevant_question = results['documents'][0][0]
            relevant_answer = results['metadatas'][0][0]['answer']
            return jsonify({"response": f"Based on your query, here's a related answer:\n\n{relevant_answer}"})

        # If no relevant FAQ is found, fall back to GPT-4
        gpt_response = openai.Completion.create(
            engine="gpt-4",
            prompt=f"User asked: {user_question}\n\nProvide a concise and helpful answer.",
            max_tokens=150,
            temperature=0.7,
            n=1,
            stop=None
        )
        answer = gpt_response.choices[0].text.strip()
        conversation_state[user_id]['step'] = 'introduction'
        return jsonify({"response": answer})

    elif current_step == 'awaiting_service_selection':
        service = user_input.capitalize()
        if service in ["Plumbing", "Electrical", "HVAC", "Painting", "Roofing"]:
            response = {
                "message": f"Great! You have selected {service}. What would you like to do next?",
                "options": ["Schedule an Appointment", "Get a Quote", "Talk to a Representative"]
            }
            conversation_state[user_id]['selected_service'] = service
            conversation_state[user_id]['step'] = 'service_options'
            return jsonify(response)
        else:
            response = {
                "message": "Please select a valid service from the options.",
                "options": ["Plumbing", "Electrical", "HVAC", "Painting", "Roofing"]
            }
            return jsonify(response)

    elif current_step == 'service_options':
        service = conversation_state[user_id]['selected_service']
        if user_input == 'schedule an appointment':
            response = {"message": f"Please provide your preferred date and time for the {service} appointment."}
            conversation_state[user_id]['step'] = 'scheduling_appointment'
            return jsonify(response)
        elif user_input == 'get a quote':
            response = {"message": f"Please provide details about the {service} work you need done."}
            conversation_state[user_id]['step'] = 'getting_quote'
            return jsonify(response)
        elif user_input == 'talk to a representative':
            response = {"message": "Connecting you to a representative..."}
            conversation_state[user_id]['step'] = 'introduction'
            return jsonify(response)
        else:
            response = {
                "message": "Please select a valid option.",
                "options": ["Schedule an Appointment", "Get a Quote", "Talk to a Representative"]
            }
            return jsonify(response)

    elif current_step == 'scheduling_appointment':
        appointment_details = user_input
        service = conversation_state[user_id]['selected_service']
        # Here, you’d typically process and store the appointment details
        response = {
            "message": f"Your {service} appointment has been scheduled for {appointment_details}. Is there anything else I can assist you with?",
            "options": ["Yes", "No"]
        }
        conversation_state[user_id]['step'] = 'confirmation'
        return jsonify(response)

    elif current_step == 'getting_quote':
        quote_details = user_input
        service = conversation_state[user_id]['selected_service']
        # Here, you’d typically process the quote details and generate a quote
        response = {
            "message": f"Thank you for the details. We will send you a quote for the {service} service shortly. Is there anything else I can assist you with?",
            "options": ["Yes", "No"]
        }
        conversation_state[user_id]['step'] = 'confirmation'
        return jsonify(response)

    elif current_step == 'confirmation':
        if user_input == 'yes':
            response = {
                "message": "How else can I assist you today?",
                "options": ["Ask a Question", "Upload an Image", "Specify Service Needed"]
            }
            conversation_state[user_id]['step'] = 'awaiting_choice'
            return jsonify(response)
        elif user_input == 'no':
            response = {"message": "Thank you for using our services. Have a great day!"}
            conversation_state[user_id]['step'] = 'end'
            return jsonify(response)
        else:
            response = {
                "message": "Please select a valid option.",
                "options": ["Yes", "No"]
            }
            return jsonify(response)

    else:
        response = {"message": "I'm sorry, something went wrong. Let's start over. How can I assist you today?"}
        conversation_state[user_id]['step'] = 'introduction'
        return jsonify(response)

# Route to handle image upload
@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({"message": "No file part in the request."}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"message": "No selected file."}), 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        # Here you can process the image as needed
        response = {"message": "Image uploaded successfully. How can I assist you further?"}
        return jsonify(response)

# Home route
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

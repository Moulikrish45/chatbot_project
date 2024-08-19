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


@app.route('/welcome', methods=['GET'])
def welcome():
    return jsonify(message="Hi there! I'm here to help you connect with top-rated contractors. How can I assist you today?")

if __name__ == '__main__':
    app.run(debug=True)

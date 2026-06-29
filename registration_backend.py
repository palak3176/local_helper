import os
import random
import json
from flask import Flask, request, jsonify, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, timezone, timedelta

# --- 1. INITIALIZATION ---
app = Flask(__name__)
app.secret_key = "neary_onboarding_dev_secret_2024"
CORS(app)

# --- 2. CONFIGURATION ---

# Gmail SMTP Setup (Sync with your credentials)
app.config['MAIL_SERVER'] = ''
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''
mail = Mail(app)

# Database Setup (local_helper_db)
app.config['SQLALCHEMY_DATABASE_URI'] = ''
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024  # Buffer for PDFs and high-res photos

db = SQLAlchemy(app)

# Neural Storage for OTPs with dynamic expiry
TEMP_OTP_STORE = {}


# --- 3. DATABASE MODEL ---
# FIXED: Removed 'created_at' to resolve SQL 1054 Error.
# All fields set to nullable=True for dev testing.
class Provider(db.Model):
    __tablename__ = 'service_providers'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=True)
    middle_name = db.Column(db.String(100), nullable=True)
    last_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    gmail = db.Column(db.String(100), unique=True, nullable=True)
    password = db.Column(db.String(100), nullable=True, default='pass123')
    address = db.Column(db.Text, nullable=True)
    interests = db.Column(db.Text, nullable=True)  # Stored as JSON string
    photo_path = db.Column(db.String(255), nullable=True)
    aadhaar_path = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending')
    type = db.Column(db.String(50), default='guide')
    lat = db.Column(db.Float, default=19.0760)
    lng = db.Column(db.Float, default=72.8777)


# --- 4. WEB ROUTES ---

@app.route('/')
def registration_home():
    """Serves the onboarding interface from the templates folder."""
    return render_template('register_provider.html')


# --- 5. VERIFICATION LOGIC ---

@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    """Triggers transmission via Gmail or WhatsApp based on frontend 'type'."""
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Neural payload missing"}), 400

    target = str(data.get('target', 'dev_test')).strip()
    method = str(data.get('type', 'gmail')).lower().strip()

    # Generate 6-digit code for testing
    otp = str(random.randint(100000, 999999))
    TEMP_OTP_STORE[target] = {
        "otp": otp,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=10)
    }

    try:
        if method in ['gmail', 'email']:
            msg = Message('NEARY.OS // Registry Code',
                          sender=app.config['MAIL_USERNAME'], recipients=[target])
            msg.body = f"Your Authorization Code: {otp}"
            mail.send(msg)
            return jsonify({"status": "success", "message": "OTP Dispatched to Gmail"})

        elif method == 'whatsapp':
            # Lazy loading pywhatkit inside route to prevent startup hangs on Windows
            import pywhatkit
            formatted_phone = f"+91{target}" if not target.startswith('+') else target
            pywhatkit.sendwhatmsg_instantly(formatted_phone, f"NEARY.OS Code: {otp}", 15, True, 2)
            return jsonify({"status": "success", "message": "OTP Dispatched to WhatsApp"})

        return jsonify({"status": "error", "message": f"Method '{method}' invalid"}), 400

    except Exception as e:
        return jsonify({"status": "error", "message": f"Dev Warning: {str(e)}"}), 500


@app.route('/api/verify_otp', methods=['POST'])
def verify_otp():
    """Validates code. Searches registry to allow stateless frontend verification."""
    data = request.json
    if not data: return jsonify({"status": "error"}), 400

    code = str(data.get('otp', '')).strip()

    for target, record in list(TEMP_OTP_STORE.items()):
        if record["otp"] == code:
            return jsonify({"status": "success", "message": "Neural Link Established"})

    return jsonify({"status": "error", "message": "Invalid Authorization Code"}), 401


# --- 6. REGISTRY SUBMISSION ---

@app.route('/api/auth/register-provider', methods=['POST'])
def register_provider():
    """FIXED: Robust registry matching SS columns with zero compulsory fields for dev phase."""
    try:
        phone = request.form.get('phone', f"test_{random.randint(100, 999)}")

        # 1. Document Capture (Supports PDF and JPEG)
        photo = request.files.get('photo')
        aadhaar = request.files.get('aadhaar')
        photo_fn, aadhaar_fn = None, None

        if photo:
            photo_fn = secure_filename(f"p_{phone}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_fn))
        if aadhaar:
            aadhaar_fn = secure_filename(f"a_{phone}_{aadhaar.filename}")
            aadhaar.save(os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_fn))

        # 2. Database Commitment (Synced with your MySQL grid)
        new_provider = Provider(
            first_name=request.form.get('firstName', ''),
            middle_name=request.form.get('middleName', ''),
            last_name=request.form.get('lastName', ''),
            phone=phone,
            gmail=request.form.get('gmail', ''),
            address=request.form.get('address', ''),
            interests=request.form.get('interests', '[]'),
            photo_path=photo_fn,
            aadhaar_path=aadhaar_fn,
            status='pending',
            type=request.form.get('type', 'guide'),
            lat=float(request.form.get('lat', 19.0760) or 19.0760),
            lng=float(request.form.get('lng', 72.8777) or 72.8777)
        )

        db.session.add(new_provider)
        db.session.commit()

        return jsonify({"status": "success", "message": "Registry Packet Processed."})

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"SQL Debug: {str(e)}"}), 500


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    print("NEARY.OS Registry Backend starting on Port 5001")
    app.run(debug=True, port=5001)

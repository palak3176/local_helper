
import os
import random
import json
import smtplib
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_mail import Mail, Message
from datetime import datetime, timezone, timedelta
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "neary_mumbai_2024_secure")
CORS(app)

# --- MySQL Configuration ---
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'mysql+mysqlconnector://root:31072006Palak@localhost/local_helper_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '').strip()
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '').replace(' ', '').strip()

db = SQLAlchemy(app)
mail = Mail(app)
TEMP_OTP_STORE = {}

# --- Regional Coordinate Mapping ---
REGION_COORDS = {
    "thane": (19.2183, 72.9781), "bandra": (19.0596, 72.8295),
    "andheri": (19.1136, 72.8697), "dadar": (19.0178, 72.8478),
    "powai": (19.1176, 72.9060), "colaba": (18.9067, 72.8147),
    "juhu": (19.1000, 72.8267), "worli": (19.0100, 72.8150),
    "borivali": (19.2307, 72.8567), "vashi": (19.0330, 73.0297),
    "mumbai": (19.0760, 72.8777)
}

SERVICE_ALIASES = {
    "guide": "guide",
    "errand": "errand",
    "errands": "errand",
    "queue": "queue",
    "waiting in queue": "queue",
    "labour": "labour",
    "labor": "labour",
    "manual labour": "labour"
}


def normalize_service(value):
    return SERVICE_ALIASES.get(str(value or "").strip().lower(), str(value or "").strip().lower())


def parse_provider_services(provider):
    services = []
    if provider and provider.interests:
        try:
            raw_services = json.loads(provider.interests)
            if isinstance(raw_services, str):
                raw_services = [raw_services]
        except Exception:
            raw_services = [provider.interests]
        services = [normalize_service(service) for service in raw_services if normalize_service(service)]

    if provider and not services and provider.type:
        services = [normalize_service(provider.type)]

    return list(dict.fromkeys(services))


def ensure_user_session():
    if session.get('role') == 'user' and session.get('user_id'):
        return User.query.get(session.get('user_id'))

    email = session.get('email')
    if email:
        user = User.query.filter_by(email=email).first()
        if user:
            session.update({
                'user_id': user.id,
                'role': 'user',
                'user_name': user.name,
                'email': user.email
            })
            return user
    return None


# --- Database Models ---

class Admin(db.Model):
    __tablename__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    access_level = db.Column(db.String(20), default='super_admin')


class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('service_providers.id'), nullable=True)
    service_type = db.Column(db.String(50), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    booking_time = db.Column(db.Time, nullable=False)
    address = db.Column(db.Text)
    lat = db.Column(db.Float, default=19.0760)
    lng = db.Column(db.Float, default=72.8777)
    hours = db.Column(db.Integer, nullable=False)
    people = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), default='COD')
    status = db.Column(db.String(20), default='pending')
    otp_start = db.Column(db.String(4))
    otp_end = db.Column(db.String(4))
    start_time = db.Column(db.DateTime)
    messages = db.Column(db.Text, default='[]')
    review_rating = db.Column(db.Integer)
    review_comment = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Provider(db.Model):
    __tablename__ = 'service_providers'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    gmail = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False, default='pass123')
    address = db.Column(db.Text)
    interests = db.Column(db.Text)
    photo_path = db.Column(db.String(255))
    aadhaar_path = db.Column(db.String(255))
    type = db.Column(db.String(50), default='guide')
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    status = db.Column(db.String(20), default='pending')


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    phone = db.Column(db.String(20), unique=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    location = db.Column(db.String(255))
    password = db.Column(db.String(100), nullable=False)


# --- Initialize DB ---
def ensure_booking_columns():
    """Keep older local MySQL databases compatible with the current model."""
    inspector = inspect(db.engine)
    existing = {column['name'] for column in inspector.get_columns('bookings')}
    column_sql = {
        'address': 'ALTER TABLE bookings ADD COLUMN address TEXT',
        'lat': 'ALTER TABLE bookings ADD COLUMN lat FLOAT DEFAULT 19.0760',
        'lng': 'ALTER TABLE bookings ADD COLUMN lng FLOAT DEFAULT 72.8777',
        'review_rating': 'ALTER TABLE bookings ADD COLUMN review_rating INT',
        'review_comment': 'ALTER TABLE bookings ADD COLUMN review_comment TEXT',
        'reviewed_at': 'ALTER TABLE bookings ADD COLUMN reviewed_at DATETIME'
    }
    for column_name, ddl in column_sql.items():
        if column_name not in existing:
            db.session.execute(text(ddl))
    db.session.commit()


with app.app_context():
    db.create_all()
    ensure_booking_columns()


# --- WEB ROUTES ---

@app.route('/')
def gateway():
    return render_template('neary_gateway.html')


@app.route('/register-sp')
def register_provider_page():
    return render_template('register_provider.html')


@app.route('/user_portal')
def user_portal():
    return render_template('index.html') if session.get('role') == 'user' else redirect(url_for('gateway'))


@app.route('/provider_portal')
def provider_portal():
    return render_template('provider.html') if session.get('role') == 'provider' else redirect(url_for('gateway'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('gateway'))


# --- AUTH API ---

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    admin = Admin.query.filter_by(email=email, password=password).first()
    if admin:
        session.update({'user_id': admin.id, 'role': 'admin', 'email': email})
        return jsonify({"status": "success", "redirect": "/admin_dashboard"})

    provider = Provider.query.filter_by(gmail=email, password=password).first()
    if provider:
        session.update({'user_id': provider.id, 'role': 'provider', 'user_name': provider.first_name, 'email': email})
        return jsonify({"status": "success", "redirect": "/provider_portal"})

    user = User.query.filter_by(email=email, password=password).first()
    if user:
        session.update({'user_id': user.id, 'role': 'user', 'user_name': user.name, 'email': email})
        return jsonify({"status": "success", "redirect": "/user_portal"})

    return jsonify({"status": "error", "message": "Invalid Credentials"}), 401


@app.route('/api/auth/register-user', methods=['POST'])
def register_user():
    data = request.json or {}
    try:
        user = User(
            name=str(data.get('name', '')).strip(),
            age=int(data.get('age', 0) or 0),
            phone=str(data.get('phone', '')).strip(),
            email=str(data.get('email', '')).strip(),
            location=str(data.get('location', '')).strip(),
            password=str(data.get('password', '')).strip()
        )
        if not user.name or not user.email or not user.password:
            return jsonify({"status": "error", "message": "Name, email, and password are required"}), 400
        db.session.add(user)
        db.session.commit()
        return jsonify({"status": "success", "message": "User registered"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/send_otp', methods=['POST'])
def send_otp():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "OTP payload missing"}), 400

    target = str(data.get('target', '')).strip()
    method = str(data.get('type', 'gmail')).lower().strip()
    if not target:
        return jsonify({"status": "error", "message": "Phone or email is required"}), 400

    otp = str(random.randint(100000, 999999))
    TEMP_OTP_STORE[target] = {
        "otp": otp,
        "expires": datetime.now(timezone.utc) + timedelta(minutes=10)
    }

    try:
        if method in ['gmail', 'email']:
            if not app.config['MAIL_USERNAME'] or not app.config['MAIL_PASSWORD']:
                return jsonify({"status": "error", "message": "Mail settings are missing"}), 500
            msg = Message(
                'NEARY.OS // Registry Code',
                sender=app.config['MAIL_USERNAME'],
                recipients=[target]
            )
            msg.body = f"Your Authorization Code: {otp}"
            mail.send(msg)
            return jsonify({"status": "success", "message": "OTP sent to Gmail"})

        if method == 'whatsapp':
            import pywhatkit
            formatted_phone = f"+91{target}" if not target.startswith('+') else target
            pywhatkit.sendwhatmsg_instantly(formatted_phone, f"NEARY.OS Code: {otp}", 15, True, 2)
            return jsonify({"status": "success", "message": "OTP sent on WhatsApp Web"})

        return jsonify({"status": "error", "message": f"Method '{method}' is invalid"}), 400
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            "status": "error",
            "message": "Email OTP failed. Update MAIL_USERNAME or MAIL_PASSWORD in .env and restart the server."
        }), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"OTP send failed: {str(e)}"}), 500


@app.route('/api/verify_otp', methods=['POST'])
def verify_otp():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "OTP payload missing"}), 400

    code = str(data.get('otp', '')).strip()
    now = datetime.now(timezone.utc)

    for target, record in list(TEMP_OTP_STORE.items()):
        if record["expires"] < now:
            TEMP_OTP_STORE.pop(target, None)
            continue
        if record["otp"] == code:
            return jsonify({"status": "success", "message": "Verified"})

    return jsonify({"status": "error", "message": "Invalid Authorization Code"}), 401


@app.route('/api/auth/register-provider', methods=['POST'])
def register_provider():
    try:
        phone = request.form.get('phone') or f"test_{random.randint(100, 999)}"
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        photo = request.files.get('photo')
        aadhaar = request.files.get('aadhaar')
        photo_fn, aadhaar_fn = None, None

        if photo:
            photo_fn = secure_filename(f"p_{phone}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_fn))
        if aadhaar:
            aadhaar_fn = secure_filename(f"a_{phone}_{aadhaar.filename}")
            aadhaar.save(os.path.join(app.config['UPLOAD_FOLDER'], aadhaar_fn))

        try:
            raw_interests = json.loads(request.form.get('interests', '[]'))
        except Exception:
            raw_interests = []
        interests = [normalize_service(service) for service in raw_interests if normalize_service(service)]

        provider = Provider(
            first_name=request.form.get('firstName', '').strip() or 'Local',
            middle_name=request.form.get('middleName', '').strip(),
            last_name=request.form.get('lastName', '').strip() or 'Provider',
            phone=phone,
            gmail=request.form.get('gmail', '').strip(),
            address=request.form.get('address', '').strip(),
            interests=json.dumps(interests),
            photo_path=photo_fn,
            aadhaar_path=aadhaar_fn,
            status='pending',
            type=interests[0] if interests else 'guide',
            lat=float(request.form.get('lat', 19.0760) or 19.0760),
            lng=float(request.form.get('lng', 72.8777) or 72.8777)
        )
        if not provider.gmail:
            return jsonify({"status": "error", "message": "Gmail is required"}), 400

        db.session.add(provider)
        db.session.commit()
        return jsonify({"status": "success", "message": "Provider registered"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500


# --- UNIFIED PROFILE LOGIC ---

@app.route('/api/provider/profile', methods=['GET'])
def get_profile_data_serviceprovider():
    email = session.get('email')
    if not email: return jsonify({"status": "error"}), 401

    # Search both tables as requested
    p = Provider.query.filter_by(gmail=email).first()
    u = User.query.filter_by(email=email).first()

    if p:
        interests = parse_provider_services(p)
        return jsonify({
            "status": "success",
            "provider": {
                "id": p.id, "name": f"{p.first_name} {p.last_name}",
                "email": p.gmail, "interests": interests, "status": p.status
            }
        })
    elif u:
        return jsonify({
            "status": "success",
            "provider": {"id": u.id, "name": u.name, "email": u.email, "status": "User Account"}
        })
    return jsonify({"status": "error"}), 404


@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    email = session.get('email')
    if not email: return jsonify({"status": "error"}), 401

    # Search both tables as requested
    u = User.query.filter_by(email=email).first()
    p = Provider.query.filter_by(gmail=email).first()

    if u:
        return jsonify({
            "status": "success",
            "user": {"name": u.name, "email": u.email, "location": u.location or "Mumbai Grid"}
        })
    elif p:
        return jsonify({
            "status": "success",
            "user": {"name": f"{p.first_name} {p.last_name}", "email": p.gmail,
                     "location": p.address or "Provider Grid"}
        })
    return jsonify({"status": "error"}), 404


# --- USER API ---

@app.route('/api/user/book', methods=['POST'])
def create_booking():
    active_user = ensure_user_session()
    if not active_user:
        return jsonify({"status": "error", "message": "Please log in with a user account to place a booking"}), 401
    data = request.json
    try:
        new_booking = Booking(
            user_id=active_user.id,
            service_type=normalize_service(data['service_type']),
            booking_date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
            booking_time=datetime.strptime(data['time'], '%H:%M').time(),
            address=data.get('address', ''),
            lat=float(data.get('lat', 19.0760) or 19.0760),
            lng=float(data.get('lng', 72.8777) or 72.8777),
            hours=int(data['hours']),
            people=int(data['people']),
            total_price=float(data['price']),
            payment_method=data.get('payment', 'COD'),
            status='pending'
        )
        db.session.add(new_booking)
        db.session.commit()
        return jsonify({"status": "success", "message": "Booked"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/user/history', methods=['GET'])
def get_user_history():
    active_user = ensure_user_session()
    if not active_user:
        return jsonify([]), 401
    u_id = active_user.id
    # Fetch all bookings for this user to show in "Past Bookings"
    history = Booking.query.filter_by(user_id=u_id).order_by(Booking.created_at.desc()).all()
    results = []
    for b in history:
        provider = Provider.query.get(b.provider_id) if b.provider_id else None
        results.append({
            "id": b.id, "service": b.service_type, "date": b.booking_date.strftime('%Y-%m-%d'),
            "total": b.total_price, "status": b.status,
            "provider_name": f"{provider.first_name} {provider.last_name}" if provider else "Unassigned",
            "review_rating": b.review_rating,
            "review_comment": b.review_comment or "",
            "can_review": b.status == 'completed' and b.review_rating is None
        })
    return jsonify(results)


@app.route('/api/user/review', methods=['POST'])
def submit_user_review():
    active_user = ensure_user_session()
    if not active_user:
        return jsonify({"status": "error", "message": "Please log in with a user account to submit feedback"}), 401

    data = request.json or {}
    booking = Booking.query.get(data.get('booking_id'))
    if not booking or booking.user_id != active_user.id:
        return jsonify({"status": "error", "message": "Booking not found"}), 404
    if booking.status != 'completed':
        return jsonify({"status": "error", "message": "Feedback opens after service completion"}), 400

    rating = int(data.get('rating', 0))
    comment = str(data.get('comment', '')).strip()
    if rating < 1 or rating > 5:
        return jsonify({"status": "error", "message": "Rating must be between 1 and 5"}), 400

    booking.review_rating = rating
    booking.review_comment = comment
    booking.reviewed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"status": "success", "message": "Feedback saved"})


@app.route('/api/user/active_bookings', methods=['GET'])
def get_user_active_bookings():
    active_user = ensure_user_session()
    if not active_user:
        return jsonify([]), 401
    u_id = active_user.id
    active_statuses = ['accepted', 'on_the_way', 'arrived', 'in_progress']
    active = Booking.query.filter(Booking.user_id == u_id, Booking.status.in_(active_statuses)).all()
    results = []
    for b in active:
        p = Provider.query.get(b.provider_id)
        current_otp = b.otp_end if b.status == 'in_progress' else b.otp_start
        results.append({
            "id": b.id, "status": b.status, "service": b.service_type,
            "otp": current_otp, "hours": b.hours,
            "date": b.booking_date.strftime('%Y-%m-%d'),
            "time": b.booking_time.strftime('%H:%M'),
            "start_time": b.start_time.isoformat() if b.start_time else None,
            "provider_name": f"{p.first_name} {p.last_name}" if p else "Assigned Node"
        })
    return jsonify(results)


# --- PROVIDER API ---

@app.route('/api/provider/upcoming', methods=['GET'])
def get_provider_bookings():
    p_id = session.get('user_id')
    p = Provider.query.get(p_id)
    if not p:
        return jsonify([]), 401

    interests = parse_provider_services(p)

    pending_filter = Booking.status == 'pending'
    if interests:
        pending_filter = db.and_(pending_filter, Booking.service_type.in_(interests))

    jobs = Booking.query.filter(
        db.or_(pending_filter, Booking.provider_id == p_id)
    ).order_by(Booking.created_at.desc()).all()

    return jsonify([{
        "id": b.id, "user_name": User.query.get(b.user_id).name if User.query.get(b.user_id) else "Anonymous",
        "service": b.service_type, "date": b.booking_date.strftime('%Y-%m-%d'),
        "time": b.booking_time.strftime('%H:%M'), "total": b.total_price,
        "status": b.status, "hours": b.hours,
        "people": b.people, "address": b.address or "Sector Location Locked",
        "lat": b.lat or 19.0760, "lng": b.lng or 72.8777,
        "review_rating": b.review_rating, "review_comment": b.review_comment or "",
        "start_time": b.start_time.isoformat() if b.start_time else None
    } for b in jobs])


@app.route('/api/provider/booking_action', methods=['POST'])
def provider_action():
    data = request.json
    booking = Booking.query.get(data.get('booking_id'))
    if data.get('action') == 'accept':
        booking.status = 'accepted'
        booking.provider_id = session.get('user_id')
        booking.otp_start = str(random.randint(1000, 9999))
        booking.otp_end = str(random.randint(1000, 9999))
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400


@app.route('/api/provider/update_interests', methods=['POST'])
def update_provider_interests():
    p_id = session.get('user_id')
    provider = Provider.query.get(p_id)
    if provider:
        provider.interests = json.dumps([
            normalize_service(service) for service in request.json.get('interests', [])
            if normalize_service(service)
        ])
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404


# --- MISSION TELEMETRY & CHAT ---

@app.route('/api/mission/update_status', methods=['POST'])
def update_mission_status():
    booking = Booking.query.get(request.json.get('booking_id'))
    if booking:
        booking.status = request.json.get('status')
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404


@app.route('/api/mission/verify_otp', methods=['POST'])
def verify_mission_otp():
    data = request.json
    booking = Booking.query.get(data.get('booking_id'))
    otp_type, otp = data.get('type'), data.get('otp')

    if otp_type == 'start' and booking.otp_start == otp:
        booking.status, booking.start_time = 'in_progress', datetime.now()
        db.session.commit()
        return jsonify({"status": "success"})
    elif otp_type == 'end' and booking.otp_end == otp:
        booking.status = 'completed'
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid OTP"}), 401


@app.route('/api/mission/chat', methods=['GET', 'POST'])
def handle_mission_chat():
    b_id = request.args.get('booking_id') if request.method == 'GET' else request.json.get('booking_id')
    booking = Booking.query.get(b_id)
    if not booking: return jsonify([]), 404
    if request.method == 'POST':
        history = json.loads(booking.messages or '[]')
        history.append({
            "sender": session.get('role'), "text": request.json.get('text'),
            "time": datetime.now().strftime('%H:%M')
        })
        booking.messages = json.dumps(history)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify(json.loads(booking.messages or '[]'))


# --- ADMIN COMMAND CENTER ROUTES ---

@app.route('/admin_dashboard')
def admin_dashboard():
    """Renders the Tactical Admin Dashboard for authorized personnel."""
    if session.get('role') == 'admin':
        return render_template('admin.html')
    return redirect(url_for('gateway'))


@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """Provides live telemetry counts for the dashboard tiles."""
    if session.get('role') != 'admin': return jsonify({"error": "Unauthorized"}), 401

    pending = Provider.query.filter_by(status='pending').count()
    approved = Provider.query.filter_by(status='approved').count()
    rejected = Provider.query.filter_by(status='rejected').count()
    total = Provider.query.count()

    return jsonify({
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "total": total
    })


@app.route('/api/admin/providers', methods=['GET'])
def get_admin_providers():
    """Returns a list of providers filtered by their verification status."""
    if session.get('role') != 'admin': return jsonify([]), 401

    status_filter = request.args.get('status', 'pending')
    nodes = Provider.query.filter_by(status=status_filter).all()

    results = []
    for n in nodes:
        # Safely handle interests JSON
        try:
            interests_list = json.loads(n.interests) if n.interests else []
        except:
            interests_list = [n.interests] if n.interests else []

        completed_jobs = Booking.query.filter_by(provider_id=n.id, status='completed').order_by(Booking.created_at.desc()).all()
        rated_jobs = [job for job in completed_jobs if job.review_rating]
        avg_rating = round(sum(job.review_rating for job in rated_jobs) / len(rated_jobs), 1) if rated_jobs else None
        feedback_history = [{
            "booking_id": job.id,
            "service": job.service_type,
            "date": job.booking_date.strftime('%Y-%m-%d'),
            "rating": job.review_rating,
            "comment": job.review_comment or "",
            "user_name": User.query.get(job.user_id).name if User.query.get(job.user_id) else "Anonymous"
        } for job in completed_jobs]

        results.append({
            "id": n.id,
            "name": f"{n.first_name} {n.last_name}",
            "phone": n.phone,
            "email": n.gmail,
            "status": n.status,
            "interests": interests_list,
            "photo": f"/static/uploads/{n.photo_path}" if n.photo_path else "",
            "aadhaar": f"/static/uploads/{n.aadhaar_path}" if n.aadhaar_path else "",
            "completed_jobs": len(completed_jobs),
            "avg_rating": avg_rating,
            "feedback_history": feedback_history[:5]
        })
    return jsonify(results)


@app.route('/api/admin/update_provider', methods=['POST'])
def admin_update_provider():
    """Enables Admin to authorize (approve) or void (reject) specialist nodes."""
    if session.get('role') != 'admin': return jsonify({"status": "error"}), 401

    data = request.json
    provider_id = data.get('id')
    new_status = data.get('status')  # 'approved' or 'rejected'

    provider = Provider.query.get(provider_id)
    if provider:
        provider.status = new_status
        db.session.commit()
        return jsonify({"status": "success"})

    return jsonify({"status": "error", "message": "Node not found"}), 404
if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)

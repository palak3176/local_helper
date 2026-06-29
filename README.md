

```markdown
# NEARY.OS // Central Core Network 🌌🛰️

NEARY.OS is a high-end, cyberpunk-inspired marketplace architecture engineered to connect localized specialist nodes (service providers) with user clients across regional coordinates throughout Mumbai (Thane, Bandra, Juhu, Colaba). Featuring a high-contrast neon-orange design, the platform handles real-time proximity telemetry, asynchronous OTP security validation, and dedicated mission management control bars.

---

## ⚡ Core Architecture Viewports

### 🛰️ Central Gateway Matrix (`neary_gateway.html`)
* **Role Routing:** Adaptive entry point providing secure structural splits into customer pipelines, service provider pipelines, or localized logging consoles.

### 👤 Customer Terminal (`index.html`)
* **Proximity Map Isolation:** Custom Leaflet.js interactive dark-mode grid map highlighting proximity arrays and active tracking routes.
* **Operational Comms Hub:** Asynchronous chat infrastructure allowing real-time bidirectional messaging between users and field workers.
* **Dual-Stage Token Auth:** Generates localized Start and Completion OTP combinations ensuring authenticated service verification.

### 🛠️ Provider Terminal (`provider.html` / `register_provider.html`)
* **Interest Configuration Selector:** Specialist node matrix toggling service specialization criteria (Guide, Errand, Line Waiting, Manual Labor).
* **Transit Geometry Calculation:** Integrated distance processing matrices computing live physical metrics to coordinates utilizing specialized geospatial mathematical formulas:
  $$d = 2R \cdot \arctan^2\left(\sqrt{a}, \sqrt{1-a}\right)$$
* **Digital Credential Ingestion:** Supports automated onboarding pipelines incorporating physical Aadhaar PDF validations and active media device inputs.

---

## 🛠️ Technology Core

* **Backend System Core:** Python, Flask Framework
* **Data Management Layer:** SQLAlchemy Engine, MySQL Grid Node Integration
* **Asynchronous Notifications:** Flask-Mail Sub-Protocols (SMTP TLS Integration), WhatsApp Automated Handshakes (`pywhatkit`)
* **Geospatial Processing Engine:** Leaflet.js Geospatial System Core

---

## 📂 System File Blueprint

```text
├── app.py                  # Multi-threaded core micro-services server
├── data.py                 # Core production environment runner configuration
├── templates/
│   ├── neary_gateway.html  # System Gateway Matrix interface
│   ├── index.html          # Reactive Customer Terminal UI
│   ├── provider.html       # Strategic Provider Mission Control UI
│   └── register_provider.html # Digital Credential Onboarding pipeline

```

---

## 🚀 Deployment Instructions

### 1. Initialize Network Dependencies

Clone your deployment package and run the setup script:

```bash
git clone [https://github.com/your-username/neary-os.git](https://github.com/your-username/neary-os.git)
cd neary-os

# Deploy environment variables
pip install -r requirements.txt

```

### 2. Configure Local Environment Variables

Create a secure `.env` file in the root directory to store sensitive platform keys securely:

```env
SECRET_KEY=your_runtime_production_secret_key_token
DATABASE_URI=mysql+mysqlconnector://<db_user>:<db_password>@localhost/local_helper_db
MAIL_USERNAME=palakjain31072006@gmail.com
MAIL_PASSWORD=your_secure_google_app_password

```

### 3. Bootstrap the Ecosystem

Execute the backend routing server to boot up active operational threads:

```bash
python app.py

```

* **Network Host Terminal:** `http://127.0.0.1:5000/`
* **Onboarding Workspace:** `http://127.0.0.1:5000/register-sp`

```

```

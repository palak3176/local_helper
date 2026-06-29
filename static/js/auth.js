let capturedPhotoBlob = null;
let stream = null;

/**
 * 1. Internal Profile Page Navigation
 * Switches between sub-pages in the Profile tab (Page 1: Identity, Page 2: Interests).
 * This eliminates the need for scroll bars.
 */
function nextProfilePage(num) {
    const page1 = document.getElementById('profilePage1');
    const page2 = document.getElementById('profilePage2');

    if (num === 2) {
        // Simple validation before moving to interests
        const firstName = document.getElementById('firstName').value;
        const phone = document.getElementById('phone').value;
        if (!firstName || !phone) {
            alert("Please enter your First Name and Phone Number to continue.");
            return;
        }
        page1.style.display = 'none';
        page2.style.display = 'block';
    } else {
        page1.style.display = 'block';
        page2.style.display = 'none';
    }
}

/**
 * 2. Main Tab Navigation
 * Switches between Profile, Docs Upload, and Verification.
 */
function showTab(num) {
    // Ensure address is provided before moving to Docs
    if (num === 2) {
        const addr = document.getElementById('addrField').value;
        if (!addr) {
            alert("Please provide your address before proceeding.");
            return;
        }
    }

    document.getElementById('profileSection').style.display = (num === 1) ? 'block' : 'none';
    document.getElementById('docsSection').style.display = (num === 2) ? 'block' : 'none';
    document.getElementById('verifySection').style.display = (num === 3) ? 'block' : 'none';

    // Update active state of progress pills
    document.querySelectorAll('.step-pill').forEach((pill, index) => {
        pill.classList.toggle('active', (index + 1) === num);
    });
}

/**
 * 3. Real OTP Logic (WhatsApp & Gmail)
 * Connects to the /api/send_otp route in app.py.
 */
async function getOTP(type) {
    const target = (type === 'whatsapp') ? document.getElementById('phone').value : document.getElementById('gmail').value;

    if (!target) {
        alert(`Please enter your ${type === 'whatsapp' ? 'Phone' : 'Gmail'} first.`);
        return;
    }

    // Capture button and start countdown
    const btn = event.target;
    startOTPCountdown(btn);

    try {
        const response = await fetch('/api/send_otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type, target: target })
        });
        const result = await response.json();
        alert(result.message);
    } catch (err) {
        alert("Server Error: Check if Flask and WhatsApp Web are active.");
    }
}

/**
 * Automatically triggers verification when 6 digits are typed.
 */
async function verifyOTPEntry(type, inputElement) {
    if (inputElement.value.length !== 6) return;

    try {
        const response = await fetch('/api/verify_otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: type, otp: inputElement.value })
        });
        const result = await response.json();

        if (result.status === "success") {
            inputElement.style.borderColor = "#4caf50"; // Success Green
            inputElement.disabled = true;
            inputElement.style.color = "#4caf50";
        } else {
            inputElement.style.borderColor = "#f44336"; // Error Red
            inputElement.value = "";
            alert("Invalid OTP code. Please try again.");
        }
    } catch (err) {
        console.error("Verification error:", err);
    }
}

function startOTPCountdown(btn) {
    let count = 30;
    btn.disabled = true;
    const timer = setInterval(() => {
        btn.innerText = `Wait ${count}s`;
        count--;
        if (count < 0) {
            clearInterval(timer);
            btn.innerText = "GET OTP";
            btn.disabled = false;
        }
    }, 1000);
}

/**
 * 4. Camera & Photo Logic
 */
document.getElementById('openCamBtn').addEventListener('click', async () => {
    try {
        const camPreview = document.getElementById('camPreview');
        camPreview.style.display = 'block';

        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        const video = document.getElementById('video');
        video.srcObject = stream;
        video.style.display = 'block';

        // Reset UI for retakes
        document.getElementById('photoResult').style.display = 'none';
        document.getElementById('confirmPhotoBtn').style.display = 'none';
        document.getElementById('confirmPhotoBtn').innerText = "OK, UPLOAD THIS";
        document.getElementById('confirmPhotoBtn').style.borderColor = "";
    } catch (err) {
        alert("Camera error: Ensure browser permissions are enabled.");
    }
});

document.getElementById('snapBtn').addEventListener('click', () => {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const photoResult = document.getElementById('photoResult');

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    canvas.toBlob((blob) => {
        capturedPhotoBlob = blob;
        photoResult.src = URL.createObjectURL(blob);
        photoResult.style.display = 'block';
        document.getElementById('confirmPhotoBtn').style.display = 'block';
        video.style.display = 'none';
    }, 'image/jpeg');
});

document.getElementById('confirmPhotoBtn').addEventListener('click', () => {
    // Stop camera stream to save 8GB RAM resources
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
    document.getElementById('confirmPhotoBtn').innerText = "PHOTO READY ✓";
    document.getElementById('confirmPhotoBtn').style.borderColor = "#4caf50";
});

/**
 * 5. Document Validation (50 KB Limit)
 */
function validateAadhaarSize(input) {
    const file = input.files[0];
    if (file && file.size > 50 * 1024) {
        alert("File too large! Aadhaar image must be smaller than 50 KB.");
        input.value = "";
        document.getElementById('aadhaarName').innerText = "";
        return false;
    }
    document.getElementById('aadhaarName').innerText = "Selected: " + (file ? file.name : "");
    return true;
}

/**
 * 6. Final Submission to MySQL
 * Sends text, interests JSON, and files to /register/submit.
 */
async function uploadFullData() {
    const formData = new FormData();

    // Map text fields
    formData.append('firstName', document.getElementById('firstName').value);
    formData.append('middleName', document.getElementById('middleName').value);
    formData.append('lastName', document.getElementById('lastName').value);
    formData.append('phone', document.getElementById('phone').value);
    formData.append('gmail', document.getElementById('gmail').value);
    formData.append('address', document.getElementById('addrField').value);

    // Collect multi-select interests
    const interests = [];
    document.querySelectorAll('input[name="interest"]:checked').forEach(cb => {
        interests.push(cb.value);
    });
    formData.append('interests', JSON.stringify(interests));

    // Append Files
    if (capturedPhotoBlob) {
        formData.append('photo', capturedPhotoBlob, 'profile_capture.jpg');
    } else {
        alert("Please take a photo and click 'OK, UPLOAD THIS' first.");
        return;
    }

    const aadhaarInput = document.getElementById('aadhaarInput');
    if (aadhaarInput.files[0]) {
        formData.append('aadhaar', aadhaarInput.files[0]);
    } else {
        alert("Please upload your Aadhaar card (max 50KB).");
        return;
    }

    try {
        const response = await fetch('/register/submit', {
            method: 'POST',
            body: formData
        });
        const result = await response.json();

        if (result.status === "success") {
            showTab(3); // Success Screen
        } else {
            alert("SQL Error: " + result.message);
        }
    } catch (err) {
        alert("Network Error: Check if Flask is running.");
        console.error(err);
    }
}
import os
import re
import random
import string
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_mail import Mail, Message
from pymongo import DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from database import (
    users_col,
    alerts_col,
    otp_col,
    serialize_alert,
    save_ai_result_to_mongo,
)

from call_safety_assistant import CallSafetyAssistant, analyse_call
from voice_clone_detector import VoiceCloneDetector, detect_voice_clone
from scam_script_detector import ScamScriptDetector, detect_scam_script
from audio_utils import load_audio, save_audio, delete_audio_file
from stt import transcribe_file
from services.stt_service import SpeechToTextService

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import random

# Temporary storage for OTPs during the session
otp_storage = {}


app = Flask(__name__, static_folder="frontend", static_url_path="")
CORS(app)

app.config["MAIL_SERVER"] = os.getenv("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.getenv("MAIL_PORT", "587"))
app.config["MAIL_USE_TLS"] = os.getenv("MAIL_USE_TLS", "True").lower() == "true"
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME", "")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD", "")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER", "noreply@fraud30.local")

mail = Mail(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "ogg", "flac"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_otp():
    return "".join(random.choices(string.digits, k=6))


def send_otp_email(email, otp_code, username):
    try:
        msg = Message(
            subject="Fraud30 - Email Verification OTP",
            recipients=[email],
            body=f"Hello {username},\n\nYour OTP code for Fraud30 registration is: {otp_code}\n\nThis OTP is valid for 10 minutes.\n\nRegards,\nFraud30 Security Team",
            html=f"<html><body style='font-family:sans-serif;background:#020617;color:#e2e8f0;padding:30px;'><div style='max-width:600px;margin:0 auto;background:#0f172a;border:1px solid #334155;border-radius:12px;padding:40px;'><div style='text-align:center;margin-bottom:30px;'><div style='font-size:32px;font-weight:800;color:#22d3ee;margin-bottom:8px;'><span style='color:#3b82f6;'>FRAUD</span><span style='color:#22d3ee;'>30</span></div><div style='color:#94a3b8;font-size:14px;'>Voice-Clone & Digital Arrest Call Detector</div></div><h2 style='color:#22d3ee;margin-bottom:20px;'>Email Verification</h2><p style='color:#cbd5e1;margin-bottom:25px;'>Hello <strong style='color:#ffffff;'>{username}</strong>,</p><p style='color:#cbd5e1;margin-bottom:25px;'>Your OTP code for Fraud30 registration is:</p><div style='background:#1e293b;border:2px dashed #22d3ee;border-radius:8px;padding:20px;text-align:center;font-size:32px;font-weight:800;color:#22d3ee;letter-spacing:8px;margin-bottom:25px;'>{otp_code}</div><p style='color:#94a3b8;font-size:13px;'>This OTP is valid for <strong>10 minutes</strong>.</p><div style='border-top:1px solid #334155;margin-top:30px;padding-top:20px;'><p style='color:#64748b;font-size:12px;'>If you did not request this, please ignore this email.</p><p style='color:#64748b;font-size:12px;'>Regards,<br>Fraud30 Security Team</p></div></div></body></html>",
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False


@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("frontend", path)


@app.route("/api/auth/resend-otp", methods=["POST"])
def resend_otp():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    otp_record = otp_col.find_one({"email": email})
    if not otp_record:
        return jsonify({"error": "No pending registration found for this email"}), 404

    new_otp = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    otp_col.update_one(
        {"email": email},
        {"$set": {"otp": new_otp, "expires_at": expires_at, "created_at": datetime.utcnow()}}
    )

    email_sent = send_otp_email(email, new_otp, otp_record["username"])

    return jsonify({
        "message": "OTP resent to your email.",
        "otp_sent": email_sent
    }), 200


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = users_col.find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "username": user.get("username", ""),
            "family_email": user.get("family_email", ""),
            "family_phone": user.get("family_phone", ""),
            "analyst_name": user.get("analyst_name", user.get("username", "Analyst SecOps")),
            "soc_tier": user.get("soc_tier", "SOC Tier-1")
        }
    }), 200


# --- ALERTS ROUTES (MongoDB) ---
@app.route("/api/alerts", methods=["POST"])
def add_alert():
    data = request.get_json() or {}
    saved = save_ai_result_to_mongo(
        type_val=data["type"],
        source=data["source"],
        description=data["description"],
        risk_level=data["risk_level"],
        confidence=data.get("confidence", 99.82),
        quarantined=data.get("quarantined", True),
        user_id=data.get("user_id")
    )
    return jsonify(saved), 201


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    query = {}
    if request.args.get("type") and request.args.get("type").upper() != "ALL":
        query["type"] = request.args.get("type").upper()
    if request.args.get("risk_level"):
        query["risk_level"] = request.args.get("risk_level").upper()
    if request.args.get("search"):
        regex = re.compile(re.escape(request.args.get("search")), re.IGNORECASE)
        query["$or"] = [{"source": regex}, {"description": regex}, {"type": regex}]

    alerts = [serialize_alert(d) for d in alerts_col.find(query).sort("created_at", DESCENDING)]
    total = alerts_col.count_documents({})
    high_risk = alerts_col.count_documents({"risk_level": "HIGH"})
    quarantined = alerts_col.count_documents({"quarantined": True})

    return jsonify({
        "stats": {
            "totalAlerts": total,
            "highRisk": high_risk,
            "quarantinedPercent": round((quarantined / total) * 100) if total > 0 else 0,
            "tabs": {
                "all": total,
                "sms": alerts_col.count_documents({"type": "SMS"}),
                "calls": alerts_col.count_documents({"type": "CALL"}),
                "voiceClones": alerts_col.count_documents({"type": "VOICE CLONE"}),
                "highRisk": high_risk
            }
        },
        "alerts": alerts
    })


@app.route("/api/alerts/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    alerts_col.delete_one({"_id": ObjectId(alert_id)})
    return jsonify({"deleted": True, "id": alert_id})


# --- AI ANALYSIS ROUTES ---

@app.route("/api/analyse/audio", methods=["POST"])
def analyse_audio_route():
    """Analyze an uploaded audio file for voice clone + scam detection."""
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    transcript = request.form.get("transcript", None)
    delete_after = request.form.get("delete_after", "true").lower() == "true"

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        assistant = CallSafetyAssistant(del_after=delete_after)
        result = assistant.analyse_call(filepath, transcript=transcript, delete_audio=delete_after)

        risk = result.get("combined_risk", "safe")
        if risk != "safe":
            vc = result.get("voice_clone", {})
            sc = result.get("scam_script", {}) or {}
            risk_level = "HIGH" if risk in ("critical", "warning") else "MEDIUM"
            desc = result.get("summary", "Call analysis completed")
            save_ai_result_to_mongo(
                type_val="CALL",
                source=filename,
                description=desc,
                risk_level=risk_level,
                confidence=vc.get("synthetic_probability", 0) * 100,
                quarantined=risk == "critical",
                user_id=request.form.get("user_id")
            )

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analyse/text", methods=["POST"])
def analyse_text_route():
    """Analyze a transcript text for scam script detection."""
    data = request.get_json() or {}
    text = data.get("transcript", "") or data.get("text", "")

    if not text or not text.strip():
        return jsonify({"error": "No transcript text provided"}), 400

    try:
        detector = ScamScriptDetector()
        result = detector.detect(text)

        if result.get("is_scam"):
            risk_level = "HIGH" if result.get("risk_score", 0) >= 0.8 else "MEDIUM"
            save_ai_result_to_mongo(
                type_val="CALL",
                source="text_input",
                description=result.get("summary", "Scam detected in transcript"),
                risk_level=risk_level,
                confidence=result.get("risk_score", 0) * 100,
                quarantined=result.get("risk_score", 0) >= 0.8,
                user_id=data.get("user_id")
            )

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/analyse/voice", methods=["POST"])
def analyse_voice_route():
    """Analyze audio for voice clone detection only."""
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        detector = VoiceCloneDetector()
        result = detector.detect_from_file(filepath, delete_after=False)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/transcribe", methods=["POST"])
def transcribe_route():
    """Transcribe an audio file to text."""
    if "file" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    language = request.form.get("language", "en-IN")
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        result = transcribe_file(filepath, language=language)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "fraud30-call-safety"}), 200

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    
    # 1. Get the standard fields
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    
    # 2. Get your new frontend fields
    family_contact = data.get("family_contact", "")
    security_tier = data.get("security_tier", "Standard")

    # 3. Validation (This is likely where the 400 error is happening)
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
        
    if users_col.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 409

    # 4. Save everything to MongoDB
    res = users_col.insert_one({
        "email": email,
        "password_hash": generate_password_hash(password),
        "family_contact": family_contact,
        "security_tier": security_tier,
        "created_at": datetime.utcnow().isoformat()
    })
    
    return jsonify({
        "id": str(res.inserted_id), 
        "email": email, 
        "security_tier": security_tier
    }), 201
@app.route("/api/auth/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json() or {}
    email = data.get("email")
    
    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Generate a random 6-digit OTP
    otp = str(random.randint(100000, 999999))
    otp_storage[email] = otp
    
    # Print it to your VS Code terminal so you can test it easily
    print("\n" + "="*40)
    print(f" 🔐 MOCK OTP FOR {email}: {otp} ")
    print("="*40 + "\n")
    
    return jsonify({"message": "OTP generated successfully"}), 200

@app.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json() or {}
    email = data.get("email")
    user_otp = data.get("otp")
    
    if not email or not user_otp:
        return jsonify({"error": "Missing email or OTP"}), 400
        
    # Check if OTP matches
    if otp_storage.get(email) == str(user_otp):
        del otp_storage[email] # Clear it after successful use
        return jsonify({"message": "OTP verified successfully!"}), 200
        
    return jsonify({"error": "Invalid or expired OTP"}), 400
import subprocess

# Global variable to track the background script
stt_process = None

@app.route("/api/stt/start", methods=["POST"])
def start_stt():
    global stt_process
    # Only start if it isn't already running
    if stt_process is None or stt_process.poll() is not None:
        print(" Starting Live Call Intercept...")
        stt_process = subprocess.Popen(["python", "scrcpy_stt.py"])
        return jsonify({"message": "Live transcription started"}), 200
    return jsonify({"message": "Already running"}), 200

@app.route("/api/stt/stop", methods=["POST"])
def stop_stt():
    global stt_process
    if stt_process is not None:
        print(" Stopping Live Call Intercept...")
        stt_process.terminate()  # Kills the script
        stt_process = None
        return jsonify({"message": "Live transcription stopped"}), 200
    return jsonify({"message": "Not running"}), 200
import sqlite3
from flask import jsonify # Ensure this is at the top of your file if not already imported

@app.route("/api/transcriptions", methods=["GET"])
def get_transcriptions():
    try:
        conn = sqlite3.connect('database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM transcriptions ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        
        return jsonify([dict(row) for row in rows]), 200
        
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify([]), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

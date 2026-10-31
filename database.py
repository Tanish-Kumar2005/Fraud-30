import os
import re
from datetime import datetime
from bson.objectid import ObjectId
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient, DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
CORS(app)

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/")
DB_NAME = os.getenv("DB_NAME", "fraud30_db")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
users_col = db["users"]
alerts_col = db["alerts"]
otp_col = db["otp"]

# Ensure unique index on email for user credentials
users_col.create_index("email", unique=True)
otp_col.create_index("email", unique=True)
otp_col.create_index("expires_at", expireAfterSeconds=0)


def serialize_alert(doc):
    """Convert MongoDB ObjectId to string for JSON responses."""
    return {
        "id": str(doc["_id"]),
        "user_id": doc.get("user_id"),
        "date_label": doc.get("date_label"),
        "type": doc.get("type"),
        "source": doc.get("source"),
        "description": doc.get("description"),
        "risk_level": doc.get("risk_level"),
        "quarantined": doc.get("quarantined", True),
        "confidence": doc.get("confidence", 99.82),
        "created_at": doc.get("created_at")
    }


# ==========================================
# 1. USER CREDENTIALS / AUTH ROUTES
# ==========================================

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    analyst_name = data.get("analyst_name", "Analyst SecOps")
    soc_tier = data.get("soc_tier", "SOC Tier-1")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    if users_col.find_one({"email": email}):
        return jsonify({"error": "User with this email already exists"}), 409

    user_doc = {
        "email": email,
        "password_hash": generate_password_hash(password),
        "analyst_name": analyst_name,
        "soc_tier": soc_tier,
        "created_at": datetime.utcnow().isoformat()
    }

    result = users_col.insert_one(user_doc)

    return jsonify({
        "id": str(result.inserted_id),
        "email": email,
        "analyst_name": analyst_name,
        "soc_tier": soc_tier
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = users_col.find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "analyst_name": user.get("analyst_name", "Analyst SecOps"),
            "soc_tier": user.get("soc_tier", "SOC Tier-1")
        }
    }), 200


# ==========================================
# 2. AI SCAN RESULT -> MONGODB -> FRONTEND
# ==========================================

def save_ai_result_to_mongo(type_val, source, description, risk_level, confidence=99.82, quarantined=True, user_id=None):
    """
    Call this directly from your Python AI model script or via POST /api/alerts
    """
    valid_types = {"SMS", "CALL", "VOICE CLONE"}
    valid_risks = {"LOW", "MEDIUM", "HIGH"}

    clean_type = type_val.upper().strip()
    clean_risk = risk_level.upper().strip()

    if clean_type not in valid_types:
        raise ValueError(f"type must be one of {valid_types}")
    if clean_risk not in valid_risks:
        raise ValueError(f"risk_level must be one of {valid_risks}")

    alert_doc = {
        "user_id": user_id,
        "date_label": f"Today, {datetime.now().strftime('%H:%M')}",
        "type": clean_type,
        "source": source.strip(),
        "description": description.strip(),
        "risk_level": clean_risk,
        "quarantined": bool(quarantined),
        "confidence": float(confidence),
        "created_at": datetime.utcnow()
    }

    result = alerts_col.insert_one(alert_doc)
    alert_doc["_id"] = result.inserted_id
    return serialize_alert(alert_doc)


@app.route("/api/alerts", methods=["POST"])
def add_alert():
    data = request.get_json() or {}
    type_val = data.get("type")           # 'SMS', 'CALL', or 'VOICE CLONE'
    source = data.get("source")           # e.g., 'VK-BANKSC'
    description = data.get("description") # AI threat explanation
    risk_level = data.get("risk_level")   # 'LOW', 'MEDIUM', or 'HIGH'
    confidence = data.get("confidence", 99.82)
    quarantined = data.get("quarantined", True)
    user_id = data.get("user_id")

    if not all([type_val, source, description, risk_level]):
        return jsonify({"error": "type, source, description, and risk_level are required"}), 400

    try:
        saved = save_ai_result_to_mongo(
            type_val, source, description, risk_level, confidence, quarantined, user_id
        )
        return jsonify(saved), 201
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    type_filter = request.args.get("type")
    risk_filter = request.args.get("risk_level")
    search = request.args.get("search")
    user_id = request.args.get("user_id")

    query = {}

    if user_id:
        query["user_id"] = user_id

    if type_filter and type_filter.upper() != "ALL":
        query["type"] = type_filter.upper()

    if risk_filter:
        query["risk_level"] = risk_filter.upper()

    if search:
        regex = re.compile(re.escape(search), re.IGNORECASE)
        query["$or"] = [
            {"source": regex},
            {"description": regex},
            {"type": regex},
            {"date_label": regex}
        ]

    cursor = alerts_col.find(query).sort("created_at", DESCENDING)
    alerts = [serialize_alert(doc) for doc in cursor]

    # Calculate top dashboard cards & filter tab counters
    total_alerts = alerts_col.count_documents({})
    high_risk = alerts_col.count_documents({"risk_level": "HIGH"})
    quarantined = alerts_col.count_documents({"quarantined": True})
    sms_count = alerts_col.count_documents({"type": "SMS"})
    call_count = alerts_col.count_documents({"type": "CALL"})
    voice_count = alerts_col.count_documents({"type": "VOICE CLONE"})

    quarantined_percent = round((quarantined / total_alerts) * 100) if total_alerts > 0 else 0

    return jsonify({
        "stats": {
            "totalAlerts": total_alerts,
            "highRisk": high_risk,
            "quarantinedPercent": quarantined_percent,
            "tabs": {
                "all": total_alerts,
                "sms": sms_count,
                "calls": call_count,
                "voiceClones": voice_count,
                "highRisk": high_risk
            }
        },
        "alerts": alerts
    })


@app.route("/api/alerts/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    try:
        result = alerts_col.delete_one({"_id": ObjectId(alert_id)})
        if result.deleted_count == 0:
            return jsonify({"error": "Alert not found"}), 404
        return jsonify({"deleted": True, "id": alert_id})
    except Exception:
        return jsonify({"error": "Invalid alert ID"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

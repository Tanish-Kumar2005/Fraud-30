import re
from datetime import datetime
from bson.objectid import ObjectId
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash

# Import database collections and functions from db.py
from db import (
    users_col,
    alerts_col,
    get_sqlite_conn,
    serialize_alert,
    save_ai_result_to_mongo,
    save_transcription_to_sqlite
)

app = Flask(__name__)
CORS(app)


# --- AUTH ROUTES ---
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
        return jsonify({"error": "User already exists"}), 409

    res = users_col.insert_one({
        "email": email,
        "password_hash": generate_password_hash(password),
        "analyst_name": analyst_name,
        "soc_tier": soc_tier,
        "created_at": datetime.utcnow().isoformat()
    })
    return jsonify({"id": str(res.inserted_id), "email": email, "analyst_name": analyst_name, "soc_tier": soc_tier}), 201


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
            "analyst_name": user.get("analyst_name"),
            "soc_tier": user.get("soc_tier")
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

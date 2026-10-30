import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)
DB_NAME = "fraud30.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionaries
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Create User Credentials Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            analyst_name TEXT DEFAULT 'Analyst SecOps',
            soc_tier TEXT DEFAULT 'SOC Tier-1',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Create Alerts Table (starts empty, populated by AI results)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date_label TEXT NOT NULL,
            type TEXT CHECK(type IN ('SMS', 'CALL', 'VOICE CLONE')) NOT NULL,
            source TEXT NOT NULL,
            description TEXT NOT NULL,
            risk_level TEXT CHECK(risk_level IN ('LOW', 'MEDIUM', 'HIGH')) NOT NULL,
            quarantined INTEGER DEFAULT 1,
            confidence REAL DEFAULT 99.82,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    conn.commit()
    conn.close()


# Initialize tables on startup
init_db()


# ==========================================
# USER CREDENTIALS / AUTH ROUTES
# ==========================================

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    analyst_name = data.get("analyst_name", "Analyst SecOps")
    soc_tier = data.get("soc_tier", "SOC Tier-1")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    password_hash = generate_password_hash(password)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, analyst_name, soc_tier) VALUES (?, ?, ?, ?)",
            (email, password_hash, analyst_name, soc_tier),
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "id": user_id,
            "email": email,
            "analyst_name": analyst_name,
            "soc_tier": soc_tier
        }), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "User with this email already exists"}), 409


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "analyst_name": user["analyst_name"],
            "soc_tier": user["soc_tier"]
        }
    }), 200


# ==========================================
# AI SCAN RESULT -> SQLITE -> FRONTEND TABLE
# ==========================================

def save_ai_result_to_db(type_val, source, description, risk_level, confidence=99.82, quarantined=1, user_id=None):
    """
    Helper function you can call directly from your Python AI script
    OR via the POST /api/alerts endpoint.
    """
    date_label = f"Today, {datetime.now().strftime('%H:%M')}"
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO alerts (user_id, date_label, type, source, description, risk_level, quarantined, confidence)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        date_label,
        type_val.upper(),
        source,
        description,
        risk_level.upper(),
        1 if quarantined else 0,
        confidence
    ))

    conn.commit()
    new_id = cursor.lastrowid
    row = conn.execute("SELECT * FROM alerts WHERE id = ?", (new_id,)).fetchone()
    conn.close()
    return dict(row)


@app.route("/api/alerts", methods=["POST"])
def add_alert():
    data = request.get_json()
    type_val = data.get("type")          # 'SMS', 'CALL', or 'VOICE CLONE'
    source = data.get("source")          # e.g., 'VK-BANKSC' or '+91 98XXX XX210'
    description = data.get("description")# AI threat summary
    risk_level = data.get("risk_level")  # 'LOW', 'MEDIUM', or 'HIGH'
    confidence = data.get("confidence", 99.82)
    quarantined = data.get("quarantined", 1)
    user_id = data.get("user_id")

    if not all([type_val, source, description, risk_level]):
        return jsonify({"error": "type, source, description, and risk_level are required"}), 400

    try:
        saved_alert = save_ai_result_to_db(
            type_val, source, description, risk_level, confidence, quarantined, user_id
        )
        return jsonify(saved_alert), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    type_filter = request.args.get("type")
    risk_filter = request.args.get("risk_level")
    search = request.args.get("search")
    user_id = request.args.get("user_id")

    query = "SELECT * FROM alerts WHERE 1=1"
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    if type_filter and type_filter.upper() != "ALL":
        query += " AND type = ?"
        params.append(type_filter.upper())

    if risk_filter:
        query += " AND risk_level = ?"
        params.append(risk_filter.upper())

    if search:
        query += " AND (source LIKE ? OR description LIKE ? OR type LIKE ? OR date_label LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY id DESC"

    conn = get_db_connection()
    rows = conn.execute(query, params).fetchall()
    alerts = [dict(row) for row in rows]

    # Calculate top dashboard cards & filter tab counters
    total_alerts = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
    high_risk = conn.execute("SELECT COUNT(*) FROM alerts WHERE risk_level = 'HIGH'").fetchone()[0]
    quarantined = conn.execute("SELECT COUNT(*) FROM alerts WHERE quarantined = 1").fetchone()[0]
    sms_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE type = 'SMS'").fetchone()[0]
    call_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE type = 'CALL'").fetchone()[0]
    voice_count = conn.execute("SELECT COUNT(*) FROM alerts WHERE type = 'VOICE CLONE'").fetchone()[0]
    conn.close()

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


@app.route("/api/alerts/<int:alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()
    return jsonify({"deleted": True, "id": alert_id})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

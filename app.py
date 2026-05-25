from flask import (
    Flask,
    request,
    jsonify,
    send_from_directory,
    render_template,
    redirect,
    url_for,
    send_file
)

from flask_cors import CORS
from flask_mail import Mail, Message

import sqlite3
import os
import json
import random
import requests
import pandas as pd
import razorpay
import firebase_admin
import cloudinary
import cloudinary.uploader

from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from firebase_admin import credentials, messaging

from datetime import datetime, timedelta

from math import radians, cos, sin, asin, sqrt

# Load environment variables
load_dotenv()




firebase_key = os.environ.get("FIREBASE_KEY")



TELEGRAM_BOT_TOKEN = "8674468800:AAG-Th-PKddYC9TeIuSkBLrP5g2Vxo3y14A"
TELEGRAM_CHAT_ID = 8771789372  # replace with your chat id

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)



# ==============================
# APP SETUP
# ==============================


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "rapidlabs.db")

print("DATABASE PATH:", DB_PATH)


app = Flask(__name__)
CORS(app)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password_hash TEXT,
        role TEXT
    )
    """)

    # LEADS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile_number TEXT,
        test_name TEXT,
        location TEXT,
        pincode TEXT,
        created_at TEXT,
        status TEXT,
        payment_status TEXT,
        amount REAL,
        sample_date TEXT,
        sample_time TEXT
    )
    """)

    # SAMPLE COLLECTORS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sample_collectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        email TEXT,
        password TEXT,
        salary REAL,
        status TEXT,
        fcm_token TEXT
    )
    """)

    #Assign Collection Task

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS collection_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        patient_name TEXT,
        mobile TEXT,
        test TEXT,
        location TEXT,
        pincode TEXT,
        collector_id INTEGER,
        collector_name TEXT,
        collection_date TEXT,
        collection_time TEXT,
        status TEXT,
        collector_status TEXT,
        created_at TEXT
    )
    """)


    # TRACKING

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        status TEXT,
        patient_name TEXT,
        mobile TEXT,
        location TEXT,
        tests TEXT,
        addon_tests TEXT,
        amount REAL,
        reschedule_datetime TEXT,
        cancel_reason TEXT,
        created_at TEXT
    )
    """)

# INCENTIVES

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incentives (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        worker_id INTEGER,
        incentive REAL,
        created_at TEXT
    )
    """)


    # REPORTS

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        report_file TEXT,
        report_status TEXT
    )
    """)

    # PAYMENTS


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER,
        payment_id TEXT,
        method TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    # STAFF

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT,
        email TEXT,
        role TEXT,
        salary REAL,
        incentive REAL,
        join_date TEXT,
        status TEXT
    )
    """)

    # TESTS

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL
    )
    """)

    # BILLS

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        patient_name TEXT,
        phone TEXT,
        total REAL,
        payment_method TEXT,
        created_at TEXT
    )
    """)


    # BILL ITEMS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        test_name TEXT,
        price REAL
    )
    """)

    # SAMPLE TYPES

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sample_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)

    # PRESCRIPTIONS

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prescriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT,
        file TEXT,
        notes TEXT,
        created_at TEXT
    )
    """)

    # BILLING

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS billing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_name TEXT,
        test_name TEXT,
        amount REAL,
        date TEXT
    )
    """)



    # ==============================
    # LAB SYSTEM TABLES (FINAL UPDATED)
    # ==============================

    # CLIENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)

    # PATIENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        mobile TEXT,
        gender TEXT,
        client_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # TESTS (FROM EXCEL)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_name TEXT NOT NULL,
        service_code TEXT UNIQUE NOT NULL,
        mrp REAL DEFAULT 0,
        price REAL DEFAULT 0
    )
    """)

    # ✅ MUST be inside same indentation (very important)
    try:
        cursor.execute("ALTER TABLE lab_tests ADD COLUMN mrp REAL DEFAULT 0")
    except:
        pass

    # SAMPLES (BARCODE LEVEL)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_samples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT UNIQUE NOT NULL,
        patient_id INTEGER NOT NULL,
        status TEXT DEFAULT 'Collected',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # SAMPLE TESTS (CORE TABLE)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lab_sample_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample_id INTEGER NOT NULL,
        test_id INTEGER NOT NULL,
        status TEXT DEFAULT 'Pending',
        start_time TEXT,
        end_time TEXT,
        duration_seconds INTEGER DEFAULT 0,
        report_file TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ✅ ADD HERE
    try:
        cursor.execute("ALTER TABLE lab_sample_tests ADD COLUMN duration_seconds INTEGER DEFAULT 0")
    except:
        pass

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verified_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_no TEXT,
        invoice_no TEXT,
        barcode TEXT,
        filename TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# CALL THIS
init_db()




# email

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = "rapidlabs.hr@gmail.com"
app.config['MAIL_PASSWORD'] = "xjqcflzgiaafmaio"

app.config['MAIL_DEFAULT_SENDER'] = "rapidlabs.hr@gmail.com"


mail = Mail(app)
# OTP STORAGE
reset_otps = {}
print("MAIL USER:", os.environ.get("EMAIL_USER"))
# report 

def get_report(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.report_file, l.email
        FROM reports r
        JOIN leads l ON r.lead_id = l.id
        WHERE r.lead_id = ?
    """, (task_id,))

    row = cursor.fetchone()
    conn.close()

    return row


# ==============================
# FIREBASE SETUP
# ==============================


firebase_key = os.environ.get("FIREBASE_KEY")

if firebase_key:
    try:
        firebase_json = json.loads(firebase_key)
        cred = credentials.Certificate(firebase_json)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized")
    except Exception as e:
        print("❌ Firebase init error:", e)
else:
    print("❌ FIREBASE_KEY not found in environment variables")



LAB_LAT = 12.957641767686127
LAB_LNG = 77.52771451534338

# ==============================
# DATABASE CONNECTION
# ==============================

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# location

def calculate_distance(lat1, lon1, lat2, lon2):

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))

    r = 6371
    return c * r



# ==============================
# HOME ROUTE
# ==============================

@app.route("/")
def home():
    return render_template("login.html")


# ==============================
# DASHBOARD PAGE
# ==============================

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ==============================
# LOGIN API
# ==============================

@app.route("/api/login", methods=["POST"])
def login():

    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email = ?",
        (email,)
    )

    user = cursor.fetchone()

    conn.close()

    if user is None:
        return jsonify({
            "success": False,
            "message": "User not found"
        }), 404


    if user["password_hash"] != password:
        return jsonify({
            "success": False,
            "message": "Invalid password"
        }), 401

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    })

# location
@app.route("/api/check-distance", methods=["POST"])
def check_distance():
    try:
        data = request.get_json()

        user_lat = float(data["latitude"])
        user_lng = float(data["longitude"])

        distance = calculate_distance(user_lat, user_lng, LAB_LAT, LAB_LNG)

        print("User location:", user_lat, user_lng)
        print("Lab location:", LAB_LAT, LAB_LNG)
        print("Distance:", distance)

        if distance <= 10:
            return jsonify({
                "allowed": True,
                "distance": distance
            })
        else:
            return jsonify({
                "allowed": False,
                "distance": distance,
                "message": "Home collection only available within 10km"
            })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({
            "allowed": False,
            "error": "Location verification failed"
        }), 500

# ==============================
# CREATE STAFF (ADMIN ONLY)
# ==============================

@app.route("/api/create-staff", methods=["POST"])
def create_staff():

    data = request.json

    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)",
        (name, email, password, "STAFF")
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Staff created successfully"
    })



# ==============================
# CHECK LOCATION API
# ==============================

@app.route("/api/check-location", methods=["POST"])
def check_location():

    data = request.json
    pincode = data.get("pincode")

    service_pincodes = ["560040", "560039", "560026", "560072"]

    if pincode in service_pincodes:
        return jsonify({
            "available": True
        })
    else:
        return jsonify({
            "available": False
        })



# ==============================
# GET ALL LEADS
# ==============================

@app.route("/api/leads", methods=["GET"])
def get_leads():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM leads ORDER BY id DESC")

    rows = cursor.fetchall()
    conn.close()

    leads = []

    for r in rows:
        leads.append({
            "id": r["id"],
            "name": r["name"],
            "mobile_number": r["mobile_number"],
            "test_name": r["test_name"],
            "location": r["location"],
            "pincode": r["pincode"],
            "amount": r["amount"],
            "created_at": r["created_at"],
            "status": r["status"],
            "payment": r["payment_status"],   # ✅ FIX
            "sample_date": r["sample_date"],  # ✅ FIX
            "sample_time": r["sample_time"]   # ✅ FIX
        })

    return jsonify(leads)

# ==============================
# UPDATE LEAD STATUS
# ==============================

@app.route("/api/update-lead-status", methods=["POST"])
def update_lead_status():

    data = request.json
    lead_id = data.get("id")
    status = data.get("status")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE leads SET status=? WHERE id=?",
        (status, lead_id)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Status updated"
    })


# ==============================
# UPDATE PAYMENT STATUS
# ==============================

@app.route("/api/update-payment-status", methods=["POST"])
def update_payment_status():

    data = request.json
    lead_id = data.get("id")
    payment_status = data.get("payment_status")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE leads SET payment_status=? WHERE id=?",
        (payment_status, lead_id)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Payment updated"
    })


# ==============================
# CREATE LEAD (FROM FRONTEND BOOKING)
# ==============================

@app.route("/api/create-lead", methods=["POST"])
def create_lead():

    data = request.json

    name = data.get("name")
    mobile = data.get("mobile_number")
    test_name = data.get("test_name")
    location = data.get("location")
    pincode = data.get("pincode")
    amount = data.get("amount", 0)   # ← change here

    sample_date = data.get("sample_date")
    sample_time = data.get("sample_time")

    conn = get_db_connection()
    cursor = conn.cursor()

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    
    cursor.execute("""
    INSERT INTO leads 
    (name, mobile_number, test_name, location, pincode, created_at, status, payment_status, amount, sample_date, sample_time)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("name"),
        data.get("mobile_number"),
        data.get("test_name"),
        data.get("location"),
        data.get("pincode"),
        created_at,   # ✅ ADD THIS
        "new",
        data.get("payment_status", "Not Paid"),
        data.get("amount"),
        sample_date,
        sample_time
    ))


    def fix_verified_reports_table():

        conn = get_db_connection()
        cursor = conn.cursor()

        existing_cols = [
            row["name"] for row in cursor.execute(
                "PRAGMA table_info(verified_reports)"
            ).fetchall()
        ]

        if "filename" not in existing_cols:
            cursor.execute("ALTER TABLE verified_reports ADD COLUMN filename TEXT")

        conn.commit()
        conn.close()


    fix_verified_reports_table()

        # ✅ Send Telegram notification
    send_telegram_message(f"📢 New Lead Created!\nName: {name}\nMobile: {mobile}\nTest: {test_name}\nLocation: {location}\nAmount: {amount}")


    return jsonify({
        "success": True,
        "message": "Lead created successfully"
    })


# ==============================
# LEADS PAGE (ADMIN)
# ==============================

@app.route("/leads")
def leads_page():
    return render_template("leads.html")





# reports

@app.route("/api/reports")
def get_reports():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS verified_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        report_no TEXT,
        invoice_no TEXT,
        barcode TEXT,
        filename TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    existing_cols = [
        row["name"] for row in cursor.execute(
            "PRAGMA table_info(verified_reports)"
        ).fetchall()
    ]

    if "filename" not in existing_cols:
        cursor.execute("ALTER TABLE verified_reports ADD COLUMN filename TEXT")

    cursor.execute("""
    SELECT
        leads.id,
        leads.name,
        leads.mobile_number,
        leads.test_name,
        leads.amount,
        reports.report_status,
        reports.report_file

    FROM leads

    LEFT JOIN reports
    ON leads.id = reports.lead_id

    ORDER BY leads.id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    reports = []

    for r in rows:
        reports.append({
            "id": r["id"],
            "name": r["name"],
            "mobile": r["mobile_number"],
            "test": r["test_name"],
            "amount": r["amount"],
            "report_status": r["report_status"] if r["report_status"] else "Pending",
            "report_file": r["report_file"]
        })

    return jsonify(reports)


# =========================
# Upload / Save Report URL
# =========================
@app.route("/api/upload-report/<int:lead_id>", methods=["POST"])
def upload_report(lead_id):
    try:
        data = request.get_json()

        if not data or "report_url" not in data:
            return jsonify({
                "success": False,
                "message": "report_url is required"
            }), 400

        report_url = data["report_url"]

        # OPTIONAL: if you use your own domain hosting
        # you can normalize it here if needed
        # report_url = f"https://yourdomain.com/{report_url}"

        conn = get_db_connection()
        cursor = conn.cursor()

        # update report file link
        cursor.execute("""
            UPDATE reports
            SET report_file = ?
            WHERE lead_id = ?
        """, (report_url, lead_id))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Report link saved successfully",
            "url": report_url
        })

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


# =========================
# Update Report Status
# =========================
@app.route("/api/update-report-status", methods=["POST"])
def update_report_status():
    try:
        data = request.get_json()

        lead_id = data.get("lead_id")
        status = data.get("status")

        if not lead_id or not status:
            return jsonify({
                "success": False,
                "message": "lead_id and status required"
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id FROM reports WHERE lead_id = ?
        """, (lead_id,))

        existing = cursor.fetchone()

        if existing:
            cursor.execute("""
                UPDATE reports
                SET report_status = ?
                WHERE lead_id = ?
            """, (status, lead_id))
        else:
            cursor.execute("""
                INSERT INTO reports (lead_id, report_status)
                VALUES (?, ?)
            """, (lead_id, status))

        conn.commit()
        conn.close()

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500



# payments 
@app.route("/api/payments")
def get_payments():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT
        leads.id,
        leads.name,
        leads.mobile_number,
        leads.test_name,
        leads.amount,
        payments.payment_id,
        payments.method,
        payments.status,
        payments.created_at

    FROM leads

    LEFT JOIN payments
    ON leads.id = payments.lead_id

    ORDER BY leads.id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    data = []

    for r in rows:

        data.append({
            "id": r["id"],
            "name": r["name"],
            "mobile": r["mobile_number"],
            "test": r["test_name"],
            "amount": r["amount"],
            "payment_id": r["payment_id"],
            "method": r["method"],
            "status": r["status"] if r["status"] else "Pending",
            "date": r["created_at"]
        })

    return jsonify(data)

@app.route("/payments")
def payments():
    return render_template("payments.html")



# staff

@app.route("/api/staff")
def get_staff():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM staff ORDER BY id DESC")

    rows = cursor.fetchall()

    conn.close()

    data = []

    for r in rows:
        data.append({
            "id": r["id"],
            "name": r["name"],
            "mobile": r["mobile"],
            "email": r["email"],
            "role": r["role"],
            "salary": r["salary"],
            "incentive": r["incentive"],
            "join_date": r["join_date"],
            "status": r["status"]
        })

    return jsonify(data)


# add staff

@app.route("/api/add-staff", methods=["POST"])
def add_staff():

    data = request.json

    name = data.get("name")
    mobile = data.get("mobile")
    email = data.get("email")
    role = data.get("role")
    salary = data.get("salary")
    incentive = data.get("incentive")
    join_date = data.get("join_date")

    login_email = email
    login_password = data.get("login_password")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO staff
    (name,mobile,email,role,salary,incentive,status,join_date)
    VALUES (?,?,?,?,?,?,?,?)
    """, (name, mobile, email, role, salary, incentive, "Active", join_date))

    cursor.execute("SELECT id FROM users WHERE email=?", (login_email,))
    existing_user = cursor.fetchone()

    if existing_user:
        cursor.execute("""
        UPDATE users
        SET name=?, password_hash=?, role=?
        WHERE email=?
        """, (name, login_password, "STAFF", login_email))
    else:
        cursor.execute("""
        INSERT INTO users (name,email,password_hash,role)
        VALUES (?,?,?,?)
        """, (name, login_email, login_password, "STAFF"))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/api/staff/<int:id>")
def get_single_staff(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM staff WHERE id=?", (id,))
    row = cursor.fetchone()

    conn.close()

    if row is None:
        return jsonify({"error": "Staff not found"}), 404

    return jsonify({
        "id": row["id"],
        "name": row["name"],
        "mobile": row["mobile"],
        "email": row["email"],
        "role": row["role"],
        "salary": row["salary"],
        "incentive": row["incentive"],
        "join_date": row["join_date"]
    })



@app.route("/api/delete-staff", methods=["POST"])
def delete_staff():

    data=request.json
    staff_id=data["staff_id"]

    conn=get_db_connection()
    cursor=conn.cursor()

    cursor.execute("DELETE FROM staff WHERE id=?", (staff_id,))

    conn.commit()
    conn.close()

    return jsonify({"success":True})


@app.route("/api/staff-credentials/<int:id>")
def staff_credentials(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT users.email, users.password_hash
    FROM users
    JOIN staff ON users.email = staff.email
    WHERE staff.id = ? AND users.role='STAFF'
    """, (id,))

    user = cursor.fetchone()

    conn.close()

    if user is None:
        return jsonify({
            "email": "",
            "password": ""
        })

    return jsonify({
        "email": user["email"],
        "password": user["password_hash"]
    })


@app.route("/api/update-staff", methods=["POST"])
def update_staff():

    data = request.json

    staff_id = data["id"]
    name = data["name"]
    mobile = data["mobile"]
    email = data["email"]
    role = data["role"]
    salary = data["salary"]
    incentive = data["incentive"]
    join_date = data["join_date"]

    login_email = email
    login_password = data.get("login_password")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM staff WHERE id=?", (staff_id,))
    old_staff = cursor.fetchone()

    if old_staff is None:
        conn.close()
        return jsonify({
            "success": False,
            "message": "Staff not found"
        })

    old_email = old_staff["email"]

    cursor.execute("""
    UPDATE staff
    SET name=?,
        mobile=?,
        email=?,
        role=?,
        salary=?,
        incentive=?,
        join_date=?
    WHERE id=?
    """, (
        name,
        mobile,
        email,
        role,
        salary,
        incentive,
        join_date,
        staff_id
    ))

    if login_password:
        cursor.execute("""
        UPDATE users
        SET name=?,
            email=?,
            password_hash=?,
            role=?
        WHERE email=? AND role='STAFF'
        """, (
            name,
            login_email,
            login_password,
            "STAFF",
            old_email
        ))
    else:
        cursor.execute("""
        UPDATE users
        SET name=?,
            email=?,
            role=?
        WHERE email=? AND role='STAFF'
        """, (
            name,
            login_email,
            "STAFF",
            old_email
        ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Staff updated successfully"
    })

@app.route("/staff")
def staff_page():
    return render_template("staff.html")


# ==============================
# DASHBOARD STATS
# ==============================

@app.route("/api/dashboard-stats")
def dashboard_stats():

    conn = get_db_connection()
    cursor = conn.cursor()

    # total leads
    cursor.execute("SELECT COUNT(*) FROM leads")
    total_leads = cursor.fetchone()[0]

    # today leads
    cursor.execute("""
        SELECT COUNT(*) FROM leads
        WHERE date(created_at) = date('now')
    """)
    today_leads = cursor.fetchone()[0]

    # completed tests
    cursor.execute("""
        SELECT COUNT(*) FROM leads
        WHERE status='completed'
    """)
    completed = cursor.fetchone()[0]

    # total staff
    cursor.execute("""
        SELECT COUNT(*) FROM users
        WHERE role='STAFF'
    """)
    staff = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "total_leads": total_leads,
        "today_leads": today_leads,
        "completed": completed,
        "staff": staff
    })



    # staff starts 

@app.route("/staff-dashboard")
def staff_dashboard():
    return render_template("staff_dashboard.html")

@app.route("/api/staff-dashboard/<int:staff_id>")
def staff_dashboard_data(staff_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leads")
    my_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE date(created_at)=date('now')")
    today_leads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE status='completed'")
    completed = cursor.fetchone()[0]

    # ✅ ADD THIS
    cursor.execute("SELECT COUNT(*) FROM prescriptions")
    prescriptions = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "my_leads": my_leads,
        "today_leads": today_leads,
        "completed": completed,
        "prescriptions": prescriptions   # ✅ NEW
    })


@app.route("/staff-prescriptions")
def staff_prescriptions():
    return render_template("staff_prescriptions.html")




# leads
@app.route("/staff-leads")
def staff_leads_page():
    return render_template("myleads.html")

# reports
@app.route("/staff-reports")
def staff_reports():
    return render_template("staff_reports.html")

@app.route('/staff-billing')
def staff_billing():
    return render_template('billing.html')



@app.route("/create-bill")
def create_bill():
    return render_template("create-bill.html")

@app.route("/search-patient")
def search_patient():

    name = request.args.get("name")

    conn = get_db_connection()
    c = conn.cursor()

    c.execute(
        "SELECT name, mobile_number FROM leads WHERE name LIKE ?",
        ('%' + name + '%',)
    )

    rows = c.fetchall()
    conn.close()

    patients = []

    for r in rows:
        patients.append({
            "name": r[0],
            "phone": r[1],
            "age": "",
            "gender": ""
        })

    return jsonify(patients)


@app.route('/save-test', methods=['POST'])
def save_test():

    data = request.get_json()

    test_name = data.get("test_name", "").strip()
    price = data.get("price", "").strip()

    if not test_name or not price:
        return jsonify({
            "success": False,
            "message": "Test name and price are required"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tests (test_name, mrp)
        VALUES (?, ?)
    """, (test_name, price))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Test saved successfully"
    })


@app.route('/get-tests')
def get_tests():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, test_name, mrp
        FROM tests
    """)

    rows = cursor.fetchall()

    conn.close()

    tests = []

    for row in rows:

        tests.append({
            "id": row["id"],
            "name": row["test_name"],
            "price": row["mrp"]
        })

    return jsonify(tests)


    
@app.route("/update-test-price", methods=["POST"])
def update_price():

    data = request.json
    name = data["name"]
    price = data["price"]

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("UPDATE tests SET price=? WHERE name=?", (price, name))

    conn.commit()
    conn.close()

    return jsonify({"message": "Price updated"})

@app.route("/debug-db")
def debug_db():

    conn = get_db_connection()
    c = conn.cursor()

    # show tables
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = c.fetchall()

    result = []
    for t in tables:
        result.append(t[0])

    conn.close()

    return jsonify({
        "db_path": DB_PATH,
        "tables": result
    })


@app.route("/generate-invoice", methods=["POST"])
def generate_invoice():

    data = request.json

    patient = data["patient"]
    phone = data["phone"]
    total = data["total"]
    payment = data["payment_method"]
    tests = data["tests"]

    conn = get_db_connection()
    cur = conn.cursor()

    year = datetime.now().year

    cur.execute("SELECT COUNT(*) FROM bills")
    count = cur.fetchone()[0] + 1

    invoice_no = f"RL-{year}-{count:04d}"

    cur.execute("""
    INSERT INTO bills(invoice_no,patient_name,phone,total,payment_method,created_at)
    VALUES(?,?,?,?,?,datetime('now'))
    """,(invoice_no,patient,phone,total,payment))

    for t in tests:

        cur.execute("""
        INSERT INTO bill_items(invoice_no,test_name,price)
        VALUES(?,?,?)
        """,(invoice_no,t["name"],t["price"]))

    conn.commit()
    conn.close()

    return jsonify({
        "status":"success",
        "invoice_no":invoice_no
    })

@app.route("/get-bills")
def get_bills():

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bills ORDER BY id DESC")
    rows = cur.fetchall()

    bills = []

    for r in rows:
        bills.append({
            "invoice": r["invoice_no"],
            "patient": r["patient_name"],
            "phone": r["phone"],
            "total": r["total"],
            "payment": r["payment_method"],
            "date": r["created_at"]
        })

    conn.close()

    return jsonify(bills)

@app.route("/total-bills")
def total_bills():
    return render_template("total-bills.html")


@app.route('/save_bill', methods=['POST'])
def save_bill():

    data = request.json

    patient_name = data['patient_name']
    test_name = data['test_name']
    amount = data['amount']
    date = datetime.now().strftime("%Y-%m-%d")

    conn = get_db_connection()

    conn.execute(
        "INSERT INTO billing (patient_name,test_name,amount,date) VALUES (?,?,?,?)",
        (patient_name,test_name,amount,date)
    )

    conn.commit()
    conn.close()

    return jsonify({"message":"Bill Saved"})

@app.route('/reports')
def reports():

    conn = get_db_connection()

    bills = conn.execute("SELECT * FROM billing").fetchall()

    conn.close()

    return render_template("reports.html", bills=bills)






@app.route('/report/<invoice>')
def generate_report(invoice):

    conn = get_db_connection()

    bill = conn.execute(
        "SELECT * FROM bills WHERE invoice_no=?",
        (invoice,)
    ).fetchone()

    items = conn.execute(
        "SELECT test_name, price FROM bill_items WHERE invoice_no=?",
        (invoice,)
    ).fetchall()

    conn.close()

    return render_template("report.html", bill=bill, items=items)




@app.route("/api/report-patient")
def report_patient():

    name = request.args.get("name")

    conn = get_db_connection()
    c = conn.cursor()

    c.execute("""
        SELECT name, mobile_number, test_name, amount
        FROM leads
        WHERE name LIKE ?
    """, ('%' + name + '%',))

    row = c.fetchone()

    conn.close()

    if row:
        return jsonify({
            "name": row["name"],
            "mobile": row["mobile_number"],
            "test": row["test_name"],
            "amount": row["amount"]
        })

    return jsonify({})

@app.route("/api/samples")
def get_samples():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sample_types")

    rows = cursor.fetchall()

    conn.close()

    samples = [r[0] for r in rows]

    return jsonify(samples)

@app.route("/api/add-sample", methods=["POST"])
def add_sample():

    data = request.json
    name = data["name"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT OR IGNORE INTO sample_types (name) VALUES (?)",
        (name,)
    )

    conn.commit()
    conn.close()

    return {"status": "added"}

@app.route("/api/send-report-email/<int:id>", methods=["POST"])
def send_report_email(id):

    report = get_report(id)

    patient_email = report["email"]
    report_file = report["report_file"]

    msg = Message(
        subject="Your Rapid Labs Report",
        recipients=[patient_email]
    )

    msg.body = "Your report is attached."

    with app.open_resource(report_file) as fp:
        msg.attach("report.pdf","application/pdf",fp.read())

    mail.send(msg)

    return jsonify({"success":True})



# sample collection part 

@app.route("/sample-collection")
def sample_collection():
    return render_template("sample_collection.html")

@app.route("/api/sample-collectors")
def get_collectors():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sample_collectors")

    collectors = cursor.fetchall()

    conn.close()

    return jsonify([dict(row) for row in collectors])


@app.route("/api/update-collector/<int:id>", methods=["POST"])
def update_collector(id):

    data=request.json

    conn=get_db_connection()
    cursor=conn.cursor()

    cursor.execute("""
    UPDATE sample_collectors
    SET name=?, phone=?, email=?, password=?, salary=?, status=?
    WHERE id=?
    """,(data["name"],data["phone"],data["email"],data["password"],data["salary"],data["status"],id))

    conn.commit()
    conn.close()

    return {"status":"success"}


@app.route("/api/delete-collector/<int:id>", methods=["POST"])
def delete_collector(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM sample_collectors WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return {"status":"deleted"}


@app.route("/api/add-collector", methods=["POST"])
def add_collector():

    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO sample_collectors
    (name, phone, email, password, salary, status)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data["name"],
        data["phone"],
        data["email"],
        data["password"],
        data["salary"],
        data["status"]
    ))

    conn.commit()
    conn.close()

    return {"status": "success"}
@app.route("/api/auto-assign/<int:lead_id>", methods=["POST"])
def auto_assign(lead_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get lead
    cursor.execute("SELECT * FROM leads WHERE id=?", (lead_id,))
    lead = cursor.fetchone()

    if not lead:
        conn.close()
        return {"status": "error", "message": "Lead not found"}

    # Get active collectors
    cursor.execute("SELECT * FROM sample_collectors WHERE LOWER(status)='active'")
    collectors = cursor.fetchall()

    if not collectors:
        conn.close()
        return {"status": "error", "message": "No active collectors"}

    collector_id = collectors[0]["id"]

    # Insert task (FIXED FIELD NAMES)
    cursor.execute("""
    INSERT INTO collection_tasks
    (lead_id, patient_name, mobile, test, location, pincode, collector_id, status, created_at)
    VALUES(?,?,?,?,?,?,?,?,datetime('now'))
    """, (
        lead["id"],
        lead["name"],
        lead["mobile_number"],   # ✅ FIXED
        lead["test_name"],       # ✅ FIXED
        lead["location"],
        lead["pincode"],
        collector_id,
        "assigned"
    ))

    conn.commit()
    conn.close()

    return {"status": "success"}

@app.route("/api/assign-task", methods=["POST"])
def assign_task():

    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()

    # get lead details
    cursor.execute("SELECT * FROM leads WHERE id=?", (data["lead_id"],))
    lead = cursor.fetchone()

    # get collector name
    cursor.execute("SELECT name FROM sample_collectors WHERE id=?", (data["collector_id"],))
    collector = cursor.fetchone()

    cursor.execute("""
    INSERT INTO collection_tasks
    (lead_id, patient_name, mobile, test, location, pincode,
     collector_id, collector_name, collection_date, collection_time,
     status, collector_status, created_at)
    VALUES (?,?,?,?,?,?,?,?,?,?,?, ?, datetime('now'))
    """, (
        lead["id"],
        lead["name"],
        lead["mobile_number"],
        lead["test_name"],
        lead["location"],
        lead["pincode"],
        data["collector_id"],
        collector["name"],
        data["collection_date"],
        data["collection_time"],
        "assigned",
        "assigned"
    ))

    conn.commit()

        # ==============================
    # SEND PUSH NOTIFICATION
    # ==============================

    cursor.execute(
        "SELECT fcm_token FROM sample_collectors WHERE id=?",
        (data["collector_id"],)
    )

    result = cursor.fetchone()

    if result and result[0]:
        send_push_notification(
            result[0],
            "New Task Assigned",
            f"Patient: {lead['name']} - {lead['location']}"
        )


    conn.close()

    return jsonify({"message": "Task Assigned"})


@app.route("/api/leads-for-assign", methods=["GET"])
def get_leads_for_assign():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM leads
    WHERE id NOT IN (
        SELECT lead_id FROM collection_tasks
    )
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    leads = []

    for r in rows:
        leads.append({
            "id": r["id"],
            "name": r["name"],
            "mobile_number": r["mobile_number"],
            "test_name": r["test_name"],
            "location": r["location"],
            "pincode": r["pincode"],
            "amount": r["amount"],
            "created_at": r["created_at"],
            "status": r["status"],
            "payment": r["payment_status"],
            "sample_date": r["sample_date"],
            "sample_time": r["sample_time"]
        })

    return jsonify(leads)


@app.route("/api/collection-tasks", methods=["GET"])
def get_collection_tasks():

    conn = get_db_connection()
    cursor = conn.cursor()

    # ✅ Explicit columns (BEST PRACTICE)
    cursor.execute("""
        SELECT 
            ct.id,
            ct.patient_name,
            ct.mobile,
            ct.test,
            l.amount,   -- ✅ TAKE FROM LEADS
            ct.collector_name,
            ct.location,
            ct.collection_date,
            ct.collection_time,
            ct.status,
            ct.collector_status
        FROM collection_tasks ct
        LEFT JOIN leads l ON ct.lead_id = l.id
        ORDER BY ct.id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    tasks = []

    for r in rows:
        tasks.append({
            "id": r["id"],
            "patient_name": r["patient_name"],
            "mobile": r["mobile"],
            "test": r["test"],
            "amount": r["amount"] if "amount" in r.keys() else 0,   # ✅ SAFE
            "collector": r["collector_name"] if "collector_name" in r.keys() else "",
            "location": r["location"] if "location" in r.keys() else "",
            "date": r["collection_date"],
            "time": r["collection_time"],
            "status": r["status"],
            "collector_status": r["collector_status"]
        })

    return jsonify(tasks)



@app.route("/api/delete-collection-task/<int:task_id>", methods=["DELETE"])
def delete_collection_task(task_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # ✅ DELETE from YOUR actual table
        cursor.execute("DELETE FROM collection_tasks WHERE id = ?", (task_id,))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": "Task deleted successfully"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
    

    

# collector app

@app.route("/api/collector-login", methods=["POST"])
def collector_login():
    try:
        data = request.get_json(force=True)

        worker_id = data.get("id")
        password = data.get("password")

        if not worker_id or not password:
            return jsonify({"error": "Missing ID or password"}), 400

        if not worker_id.startswith("RPID"):
            return jsonify({"error": "Invalid ID format"}), 400

        numeric_id = int(worker_id.replace("RPID", ""))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, password FROM sample_collectors WHERE id=?",
            (numeric_id,)
        )

        user = cursor.fetchone()
        conn.close()

        if user and user[1] == password:
            return jsonify({"collector_id": user[0]})
        else:
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        print("LOGIN ERROR:", e)   # 👈 VERY IMPORTANT
        return jsonify({"error": "Server error"}), 500



@app.route("/api/collector-tasks/<int:collector_id>")
def get_collector_tasks(collector_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            ct.id,
            ct.patient_name,
            ct.mobile,
            ct.test,
            l.amount,
            ct.location,
            ct.collection_date,
            ct.collection_time,
            ct.status,
            IFNULL(i.incentive, 0) as incentive   -- ✅ IMPORTANT
        FROM collection_tasks ct
        LEFT JOIN leads l ON ct.lead_id = l.id
        LEFT JOIN (
    SELECT task_id, incentive
    FROM incentives
    WHERE id IN (
        SELECT MAX(id)
        FROM incentives
        GROUP BY task_id
    )
) i ON ct.id = i.task_id   -- ✅ JOIN
        WHERE ct.collector_id = ?
    """, (collector_id,))

    rows = cursor.fetchall()
    conn.close()

    tasks = []

    for r in rows:
        tasks.append({
            "id": r[0],
            "patient_name": r[1],
            "mobile": r[2],
            "test": r[3],
            "amount": r[4],
            "location": r[5],
            "date": r[6],
            "time": r[7],
            "status": r[8],
            "incentive": r[9]   # ✅ CRITICAL
        })

    return jsonify(tasks)



client = razorpay.Client(auth=("rzp_live_SSBMTmhAOm7s8f", "L7maA5jQ4qpW5ll7b6UBg4HH"))

@app.route("/create-order", methods=["POST"])
def create_order():
    try:
        data = request.get_json()

        amount = int(data.get("amount", 0)) * 100

        order = client.order.create({
            "amount": amount,
            "currency": "INR",
            "payment_capture": 1
        })

        return jsonify(order)

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/update-task-status", methods=["POST"])
def update_task_status():

    data = request.json
    print("🔥 RECEIVED:", data)

    task_id = data.get("task_id")
    status = data.get("status")
    patient_name = data.get("patient_name")
    mobile = data.get("mobile")
    location = data.get("location")

    # ✅ FIX: handle string OR list
    tests = data.get("tests", "")
    if isinstance(tests, list):
        tests = ",".join(tests)

    # ✅ ADD THIS (MAIN FIX)
    addon_tests = data.get("addon_tests", "")

    amount = data.get("amount", 0)

    reschedule_datetime = data.get("reschedule_datetime")
    cancel_reason = data.get("cancel_reason")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO tracking
        (task_id, status, patient_name, mobile, location, tests, addon_tests, amount,
         reschedule_datetime, cancel_reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        task_id,
        status,
        patient_name,
        mobile,
        location,
        tests,
        addon_tests,   # ✅ ADDED
        amount,
        reschedule_datetime,
        cancel_reason
    ))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route("/api/get-tracking/<int:task_id>")
def get_tracking(task_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status, created_at
        FROM tracking
        WHERE task_id=?
        ORDER BY id ASC
    """, (task_id,))

    rows = cursor.fetchall()
    conn.close()

    data = []

    for r in rows:
        data.append({
            "status": r["status"],
            "time": r["created_at"]
        })

    return jsonify(data)

@app.route('/api/tracking')
def get_all_tracking():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.*
        FROM tracking t
        INNER JOIN (
            SELECT task_id, MAX(id) as max_id
            FROM tracking
            GROUP BY task_id
        ) latest
        ON t.id = latest.max_id
        ORDER BY t.id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    data = []

    for r in rows:
        data.append({
            "task_id": r["task_id"],
            "status": r["status"],
            "patient_name": r["patient_name"],
            "mobile": r["mobile"],
            "location": r["location"],
            "tests": r["tests"],
            "amount": r["amount"],
            "created_at": r["created_at"],
            "reschedule_datetime": r["reschedule_datetime"],
            "cancel_reason": r["cancel_reason"]
        })

    return jsonify(data)


@app.route('/api/completed-tasks')
def completed_tasks():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        t.task_id,
        t.status,
        t.tests,
        t.addon_tests,   -- ✅ ADD THIS LINE
        t.patient_name,
        t.mobile,
        t.location,
        i.worker_id,
        i.incentive
        FROM tracking t
        LEFT JOIN incentives i ON t.task_id = i.task_id
        WHERE LOWER(t.status) = 'completed'
        ORDER BY t.id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    data = []

    for r in rows:
        data.append({
            "task_id": r["task_id"],
            "status": r["status"],
            "tests": r["tests"],
            "addon_test": r["addon_tests"],   # ✅ ADD THIS
            "worker_id": r["worker_id"] if r["worker_id"] else "",
            "patient_name": r["patient_name"],
            "incentive": r["incentive"] if r["incentive"] else 0
        })

    return jsonify(data)


@app.route('/api/save-incentive', methods=['POST'])
def save_incentive():

    data = request.json
    task_id = data.get("task_id")
    worker_id = data.get("worker_id")
    incentive = data.get("incentive")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM incentives WHERE task_id=?", (task_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE incentives
            SET incentive=?
            WHERE task_id=?
        """, (incentive, task_id))
    else:
        cursor.execute("""
            INSERT INTO incentives (task_id, worker_id, incentive, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (task_id, worker_id, incentive))

    conn.commit()
    conn.close()

    return jsonify({"success": True})

@app.route('/api/get-next-task/<int:collector_id>')
def get_next_task(collector_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            ct.id,
            ct.patient_name,
            ct.mobile,
            ct.test,
            l.amount,
            ct.location,
            ct.collection_date,
            ct.collection_time,
            ct.status
        FROM collection_tasks ct
        LEFT JOIN leads l ON ct.lead_id = l.id
        WHERE ct.collector_id = ?
        AND LOWER(ct.status) != 'completed'
        ORDER BY ct.id ASC
        LIMIT 1
    """, (collector_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "id": row[0],
            "patient_name": row[1],
            "mobile": row[2],
            "test": row[3],
            "amount": row[4],
            "location": row[5],
            "date": row[6],
            "time": row[7],
            "status": row[8]
        })
    else:
        return jsonify(None)
    


@app.route("/api/manual-lead", methods=["POST"])
def manual_lead():

    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO leads (
            name, mobile_number, test_name, location, pincode,
            amount, status, payment_status,
            sample_date, sample_time, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (
        data.get("name"),
        data.get("mobile"),
        data.get("test"),
        data.get("location"),
        data.get("pincode"),
        data.get("amount"),
        "new",
        "Pending",
        data.get("sample_date"),
        data.get("sample_time")
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Lead added"})



# excel bulk data

@app.route('/api/bulk-create-tasks', methods=['POST'])
def bulk_create_tasks():
    data = request.json

    conn = get_db_connection()
    cursor = conn.cursor()

    for item in data:
        cursor.execute("""
            INSERT INTO leads 
            (name, mobile_number, test_name, location, amount, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            item.get('name'),
            item.get('phone'),
            item.get('test'),
            item.get('address'),
            item.get('amount'),
            'assigned'
        ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Bulk tasks created"})


@app.route("/api/collector/<int:id>")
def get_collector(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, name, phone, email
        FROM sample_collectors
        WHERE id=?
    """, (id,))

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return jsonify({"error": "Collector not found"}), 404

    return jsonify({
        "id": row["id"],
        "name": row["name"],
        "phone": row["phone"],
        "email": row["email"]
    })

def send_push_notification(token, title, body):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )

        response = messaging.send(message)
        print("Notification sent:", response)

    except Exception as e:
        print("FCM ERROR:", e)


@app.route("/api/save-fcm-token", methods=["POST"])
def save_fcm_token():
    data = request.json

    collector_id = data.get("collector_id")
    token = data.get("token")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sample_collectors
        SET fcm_token=?
        WHERE id=?
    """, (token, collector_id))

    conn.commit()
    conn.close()

    return jsonify({"success": True})






# ---------------- GET PRESCRIPTIONS ----------------
@app.route("/api/prescriptions")
def get_prescriptions():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, mobile, file, notes, created_at
        FROM prescriptions
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    data = []
    for r in rows:
        data.append({
            "name": r["name"],
            "mobile": r["mobile"],
            "file": r["file"],      # this is browser path like /static/prescriptions/xxx.png
            "notes": r["notes"],
            "date": r["created_at"]
        })

    return jsonify(data)

# ---------------- UPLOAD PRESCRIPTION ----------------@app.route("/api/upload-prescription", methods=["POST"])
def upload_prescription():
    try:
        import os

        # ✅ GET DATA
        file = request.files.get("file")
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        notes = request.form.get("notes")

        # ✅ VALIDATION
        if not file or file.filename == "":
            return jsonify({"success": False, "message": "No file uploaded"})

        # ✅ CLEAN FILE NAME
        filename = file.filename.replace(" ", "_").replace("(", "").replace(")", "")
        name_without_ext = os.path.splitext(filename)[0]
        ext = os.path.splitext(filename)[1].replace(".", "").lower()

        # ✅ DECIDE RESOURCE TYPE (IMPORTANT)
        if ext in ["jpg", "jpeg", "png", "webp"]:
            resource_type = "image"
        else:
            resource_type = "raw"

        # ✅ UPLOAD TO CLOUDINARY WITH FIX
        upload_result = cloudinary.uploader.upload(
            file,
            resource_type=resource_type,
            folder="prescriptions",
            public_id=name_without_ext,
            format=ext,
            overwrite=True
        )

        # ✅ GET URL
        file_url = upload_result["secure_url"]

        print("✅ Uploaded URL:", file_url)

        # ✅ SAVE IN DATABASE
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO prescriptions (name, mobile, file, notes, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (name, mobile, file_url, notes))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "file": file_url
        })

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({
            "success": False,
            "message": str(e)
        })


@app.route("/api/get-report", methods=["POST"])
def get_report_api():

    try:
        data = request.get_json(force=True)

        lead_id = data.get("id")
        mobile = data.get("mobile")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT r.report_file
            FROM reports r
            JOIN leads l ON r.lead_id = l.id
            WHERE l.id=? AND l.mobile_number=?
        """, (lead_id, mobile))

        row = cursor.fetchone()
        conn.close()

        # ✅ MATCH FOUND
        if row and row["report_file"]:
            return jsonify({
                "success": True,
                "status": "completed",
                "report_url": row["report_file"]
            })
        
        return jsonify({
            "success": True,
            "status": "pending",
            "report_url": None
        })

        # ❌ NO MATCH
        return jsonify({
            "success": False,
            "message": "Invalid ID or Mobile number"
        })

    except Exception as e:
        print("ERROR:", e)
        return jsonify({
            "success": False,
            "message": "Server error"
        }), 500
    

@app.route("/create-admin")
def create_admin():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO users (name, email, password_hash, role)
    VALUES (?, ?, ?, ?)
    """, ("Admin", "admin@gmail.com", "admin123", "ADMIN"))

    conn.commit()
    conn.close()

    return "Admin created"







        
# clientside report 

def add_client_columns_to_bills():
    conn = get_db_connection()
    cursor = conn.cursor()

    existing_cols = [row["name"] for row in cursor.execute("PRAGMA table_info(bills)").fetchall()]

    if "client_id" not in existing_cols:
        cursor.execute("ALTER TABLE bills ADD COLUMN client_id TEXT")

    if "client_name" not in existing_cols:
        cursor.execute("ALTER TABLE bills ADD COLUMN client_name TEXT")

    if "client_mobile" not in existing_cols:
        cursor.execute("ALTER TABLE bills ADD COLUMN client_mobile TEXT")

    conn.commit()
    conn.close()

    add_client_columns_to_bills()


@app.route("/client-login", methods=["GET"])
def client_login_page():
    return render_template("client-login.html")



@app.route("/client-login", methods=["POST"])
def client_login():

    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()

    # 👉 using existing users table
    cursor.execute("""
        SELECT id, name FROM users
        WHERE email=? AND password_hash=? AND role='CLIENT'
    """, (username, password))

    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({
            "status": "success",
            "client_id": user["id"],
            "name": user["name"]
        })
    else:
        return jsonify({"status": "fail"})
    


@app.route("/send-reset-otp", methods=["POST"])
def send_reset_otp():

    data = request.get_json()

    email = data.get("email", "").strip()

    if not email:
        return jsonify({
            "success": False,
            "message": "Email required"
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM users
        WHERE email=? AND role='CLIENT'
    """, (email,))

    user = cursor.fetchone()

    conn.close()

    if not user:
        return jsonify({
            "success": False,
            "message": "Email not found"
        })

    otp = str(random.randint(100000, 999999))

    expiry = datetime.now() + timedelta(minutes=5)

    reset_otps[email] = {
        "otp": otp,
        "expiry": expiry
    }

    try:

        msg = Message(
            subject="Rapid Labs Password Reset OTP",
            recipients=[email]
        )

        msg.html = f"""
        <div style="font-family: Arial, sans-serif; background:#f4f7fb; padding:40px 20px;">

            <div style="max-width:520px; margin:auto; background:white; border-radius:14px; overflow:hidden; box-shadow:0 8px 25px rgba(0,0,0,0.08);">

                <div style="background:linear-gradient(135deg,#06376d,#0877d8); padding:24px; text-align:center; color:white;">
                    <h2 style="margin:0; font-size:24px;">Rapid Labs</h2>
                    <p style="margin:8px 0 0; font-size:14px;">Password Reset Verification</p>
                </div>

                <div style="padding:30px; color:#333;">

                    <p style="font-size:15px; margin-bottom:18px;">
                        Hello,
                    </p>

                    <p style="font-size:15px; line-height:1.6; margin-bottom:22px;">
                        We received a request to reset your Rapid Labs account password.
                        Please use the OTP below to continue.
                    </p>

                    <div style="text-align:center; margin:30px 0;">
                        <span style="display:inline-block; background:#eef5ff; color:#06376d; font-size:34px; font-weight:bold; letter-spacing:8px; padding:16px 30px; border-radius:12px; border:2px dashed #0877d8;">
                            {otp}
                        </span>
                    </div>

                    <p style="font-size:14px; color:#555; line-height:1.6;">
                        This OTP is valid for <b>5 minutes</b>.
                    </p>

                    <p style="font-size:14px; color:#555; line-height:1.6;">
                        If you did not request this password reset, please ignore this email.
                    </p>

                    <p style="font-size:14px; color:#333; margin-top:26px;">
                        Regards,<br>
                        <b>Rapid Labs Team</b>
                    </p>

                </div>

                <div style="background:#f4f7fb; padding:16px; text-align:center; font-size:12px; color:#888;">
                    © Rapid Labs. All rights reserved.
                </div>

            </div>

        </div>
        """

        mail.send(msg)

        return jsonify({
            "success": True,
            "message": "OTP sent successfully"
        })

    except Exception as e:

        print("MAIL ERROR:", e)

        return jsonify({
            "success": False,
            "message": "Failed to send OTP"
        })

@app.route("/verify-reset-otp", methods=["POST"])
def verify_reset_otp():

    data = request.get_json()

    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()

    if email not in reset_otps:

        return jsonify({
            "success": False,
            "message": "OTP expired"
        })

    saved = reset_otps[email]

    if datetime.now() > saved["expiry"]:

        del reset_otps[email]

        return jsonify({
            "success": False,
            "message": "OTP expired"
        })

    if saved["otp"] != otp:

        return jsonify({
            "success": False,
            "message": "Invalid OTP"
        })

    return jsonify({
        "success": True,
        "message": "OTP verified"
    })


# admin staff login 

@app.route("/send-user-reset-otp", methods=["POST"])
def send_user_reset_otp():

    data = request.get_json()
    email = data.get("email", "").strip()

    if not email:
        return jsonify({"success": False, "message": "Email required"})

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, role FROM users
        WHERE email=? AND role IN ('ADMIN', 'STAFF')
    """, (email,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return jsonify({"success": False, "message": "Admin/Staff email not found"})

    otp = str(random.randint(100000, 999999))
    expiry = datetime.now() + timedelta(minutes=5)

    reset_otps[email] = {
        "otp": otp,
        "expiry": expiry
    }

    try:
        msg = Message(
            subject="Rapid Labs Password Reset OTP",
            recipients=[email]
        )

        msg.html = f"""
        <div style="font-family:Arial,sans-serif;background:#f4f7fb;padding:40px 20px;">
            <div style="max-width:520px;margin:auto;background:white;border-radius:14px;overflow:hidden;box-shadow:0 8px 25px rgba(0,0,0,0.08);">
                <div style="background:linear-gradient(135deg,#06376d,#0877d8);padding:24px;text-align:center;color:white;">
                    <h2 style="margin:0;">Rapid Labs</h2>
                    <p style="margin:8px 0 0;font-size:14px;">Admin/Staff Password Reset</p>
                </div>

                <div style="padding:30px;color:#333;">
                    <p>Hello,</p>

                    <p style="line-height:1.6;">
                        We received a request to reset your Rapid Labs account password.
                        Use the OTP below to continue.
                    </p>

                    <div style="text-align:center;margin:30px 0;">
                        <span style="display:inline-block;background:#eef5ff;color:#06376d;font-size:34px;font-weight:bold;letter-spacing:8px;padding:16px 30px;border-radius:12px;border:2px dashed #0877d8;">
                            {otp}
                        </span>
                    </div>

                    <p>This OTP is valid for <b>5 minutes</b>.</p>
                    <p>If you did not request this, please ignore this email.</p>

                    <p style="margin-top:26px;">
                        Regards,<br>
                        <b>Rapid Labs Team</b>
                    </p>
                </div>

                <div style="background:#f4f7fb;padding:16px;text-align:center;font-size:12px;color:#888;">
                    © Rapid Labs. All rights reserved.
                </div>
            </div>
        </div>
        """

        mail.send(msg)

        return jsonify({"success": True, "message": "OTP sent successfully"})

    except Exception as e:
        print("MAIL ERROR:", e)
        return jsonify({"success": False, "message": "Failed to send OTP"})


@app.route("/verify-user-reset-otp", methods=["POST"])
def verify_user_reset_otp():

    data = request.get_json()
    email = data.get("email", "").strip()
    otp = data.get("otp", "").strip()

    if email not in reset_otps:
        return jsonify({"success": False, "message": "OTP expired"})

    saved = reset_otps[email]

    if datetime.now() > saved["expiry"]:
        del reset_otps[email]
        return jsonify({"success": False, "message": "OTP expired"})

    if saved["otp"] != otp:
        return jsonify({"success": False, "message": "Invalid OTP"})

    return jsonify({"success": True, "message": "OTP verified"})

@app.route("/reset-user-password", methods=["POST"])
def reset_user_password():

    data = request.get_json()

    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({
            "success": False,
            "message": "Email and password required"
        })

    if email not in reset_otps:
        return jsonify({
            "success": False,
            "message": "OTP verification required"
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET password_hash=?
        WHERE email=? AND role IN ('ADMIN', 'STAFF')
    """, (password, email))

    conn.commit()

    updated_rows = cursor.rowcount

    conn.close()

    if updated_rows == 0:
        return jsonify({
            "success": False,
            "message": "Password not updated. Email or role not found."
        })

    del reset_otps[email]

    return jsonify({
        "success": True,
        "message": "Password updated successfully"
    })


@app.route("/reset-client-password", methods=["POST"])
def reset_client_password():

    data = request.get_json()

    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if email not in reset_otps:

        return jsonify({
            "success": False,
            "message": "Session expired"
        })

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET password_hash=?
        WHERE email=? AND role='CLIENT'
    """, (
        password,
        email
    ))

    conn.commit()
    conn.close()

    del reset_otps[email]

    return jsonify({
        "success": True,
        "message": "Password updated successfully"
    })


@app.route("/api/create-client", methods=["POST"])
def create_client():
    data = request.get_json()

    name = data.get("name")
    mobile = data.get("mobile")
    email = data.get("email")
    username = data.get("username")
    password = data.get("password")

    if not name or not mobile or not username or not password:
        return jsonify({"success": False, "message": "All fields required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (
                name,
                mobile,
                email,
                username,
                password_hash,
                role
            )
            VALUES (?, ?, ?, ?, ?, 'CLIENT')
        """, (
            name,
            mobile,
            email,
            username,
            password
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Client created successfully"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        conn.close()

@app.route("/api/clients", methods=["GET"])
def get_clients():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            id,
            name,
            mobile,
            email,
            username
        FROM users
        WHERE role='CLIENT'
        ORDER BY id DESC
    """)

    clients = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify(clients)




def import_tests_from_excel():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS tests")

    cursor.execute("""
        CREATE TABLE tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sl_no TEXT,
            service_code TEXT,
            department TEXT,
            test_name TEXT,
            mrp REAL,
            b2b REAL,
            sample_type TEXT,
            tat TEXT
        )
    """)

    df = pd.read_excel("test_master.xlsx", header=0)
    print(df.head())

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace("\n", " ")
        .str.replace(r"\s+", " ", regex=True)
    )

    print("EXCEL COLUMNS:", list(df.columns))

    inserted = 0

    for _, row in df.iterrows():
        test_name = str(row.get("TEST NAME", "")).strip()

        if not test_name or test_name.lower() in ["nan", "none"]:
            continue

        cursor.execute("""
            INSERT INTO tests (
                sl_no, service_code, department, test_name, mrp, b2b, sample_type, tat
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(row.get("SL NO", "")).strip(),
            str(row.get("SERVICE CODE", "")).strip(),
            str(row.get("DEPARTMENT", "")).strip(),
            test_name,
            float(row.get("MRP", 0) or 0),
            float(row.get("B2B", 0) or 0),
            str(row.get("SAMPLE TYPE", "")).strip(),
            str(row.get("TAT", "")).strip()
        ))

        inserted += 1

    conn.commit()
    conn.close()

    print(f"✅ Tests table recreated and {inserted} tests imported")

import_tests_from_excel()





def import_parameters_from_excel():
    import os

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS test_parameters")

    cursor.execute("""
        CREATE TABLE test_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_code TEXT,
            parameter_name TEXT,
            unit TEXT,
            normal_range TEXT,
            method TEXT
        )
    """)

    # 🔥 DEBUG PATH CHECK
    print("CURRENT FOLDER:", os.getcwd())
    print("PARAMETER FILE EXISTS:", os.path.exists("test_parameters.xlsx"))
    print("FULL PATH:", os.path.abspath("test_parameters.xlsx"))

    df = pd.read_excel("test_parameters.xlsx", sheet_name="Parameters", header=0)

    print("PARAMETER FILE COLUMNS:", list(df.columns))
    print(df.head())

    # 🔥 CLEAN COLUMN NAMES
    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\xa0", "")   # remove hidden spaces
        .str.strip()
        .str.upper()
        .str.replace("\n", " ")
        .str.replace(r"\s+", " ", regex=True)
    )

    inserted = 0

    for _, row in df.iterrows():
        service_code = str(row.get("SERVICE CODE", "")).strip()
        parameter_name = str(row.get("PARAMETER NAME", "")).strip()

        if not service_code or not parameter_name or parameter_name.lower() in ["nan", "none"]:
            continue

        cursor.execute("""
            INSERT INTO test_parameters (
                service_code, parameter_name, unit, normal_range, method
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            service_code,
            parameter_name,
            str(row.get("UNIT", "")).strip(),
            str(row.get("NORMAL RANGE", "")).strip(),
            str(row.get("METHOD", "")).strip()   # ✅ FIXED
        ))

        inserted += 1

    conn.commit()
    conn.close()

    print(f"✅ Parameters table recreated and {inserted} parameters imported")


import_parameters_from_excel()




@app.route("/api/save-report-entry", methods=["POST"])
def save_report_entry():
    data = request.get_json()

    invoice_no = data.get("invoice_no")
    barcode = data.get("barcode")
    report_no = data.get("report_no")
    patient_name = data.get("patient_name")
    patient_mobile = data.get("patient_mobile")
    client_name = data.get("client_name")
    sample_type = data.get("sample_type")
    results = data.get("results", [])

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS report_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT,
            barcode TEXT,
            report_no TEXT,
            patient_name TEXT,
            patient_mobile TEXT,
            client_name TEXT,
            sample_type TEXT,
            results_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    import json

    cursor.execute("""
        INSERT INTO report_entries (
            invoice_no, barcode, report_no, patient_name,
            patient_mobile, client_name, sample_type, results_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        invoice_no,
        barcode,
        report_no,
        patient_name,
        patient_mobile,
        client_name,
        sample_type,
        json.dumps(results)
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "message": "Report saved successfully"
    })
    

@app.route("/api/tests", methods=["GET"])
def get_tests_api():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            id,
            service_code,
            department,
            test_name,
            mrp,
            b2b,
            sample_type,
            tat
        FROM tests
        WHERE test_name IS NOT NULL 
          AND TRIM(test_name) != ''
        ORDER BY test_name ASC
    """)

    tests = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(tests)

@app.route("/api/parameters/<service_code>")
def get_parameters(service_code):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            parameter_name,
            method,
            unit,
            normal_range
        FROM parameter_master
        WHERE service_code = ?
    """, (service_code,))

    rows = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify(rows)



def create_billing_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔥 DROP old table (important)
    cursor.execute("DROP TABLE IF EXISTS bills")
    cursor.execute("DROP TABLE IF EXISTS bill_tests")

    # ✅ Create fresh table with bill_no
    cursor.execute("""
        CREATE TABLE bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_no TEXT UNIQUE,
            invoice_no TEXT UNIQUE,
            client_id INTEGER,
            client_name TEXT,
            client_mobile TEXT,
            patient_name TEXT,
            phone TEXT,
            gender TEXT,
            collected_by TEXT,
            payment_method TEXT,

            process_status TEXT DEFAULT 'Billing Done',

            total REAL,
            total_mrp REAL,
            total_b2b REAL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE bill_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_id INTEGER,
            test_name TEXT,
            service_code TEXT,
            sample_type TEXT,
            tat TEXT,
            mrp REAL,
            b2b REAL,
            source TEXT,
            barcode TEXT,
            sample_status TEXT DEFAULT 'Billing Done',
            report_status TEXT DEFAULT 'Pending',
            FOREIGN KEY (bill_id) REFERENCES bills(id)
        )
    """)

    conn.commit()
    conn.close()

    print("✅ Billing tables recreated with bill_no")

    create_billing_tables()


@app.route("/api/parameters/<service_code>", methods=["GET"])
def get_parameters_api(service_code):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            parameter_name,
            unit,
            normal_range,
            method
        FROM test_parameters
        WHERE UPPER(TRIM(service_code)) = UPPER(TRIM(?))
        ORDER BY id ASC
    """, (service_code,))

    parameters = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify({
        "success": True,
        "parameters": parameters
    })



@app.route("/api/create-bill", methods=["POST"])
def create_bill_api():
    data = request.get_json()

    client_id = data.get("clientId")
    client_name = data.get("clientName")
    client_mobile = data.get("clientMobile")

    patient_name = data.get("patientName")
    phone = data.get("patientMobile")
    gender = data.get("gender", "")
    payment_method = data.get("paymentStatus")
    tests = data.get("tests", [])

    if not client_id or not client_name:
        return jsonify({
            "success": False,
            "message": "Client required"
        }), 400

    if not patient_name or not tests:
        return jsonify({
            "success": False,
            "message": "Patient name and tests required"
        }), 400

    total = sum(float(t.get("mrp", 0)) for t in tests)
    invoice_no = "INV-" + datetime.now().strftime("%Y%m%d%H%M%S")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO bills (
                invoice_no,
                client_id,
                client_name,
                client_mobile,
                patient_name,
                phone,
                gender,
                total,
                payment_method,
                process_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_no,
                client_id,
                client_name,
                client_mobile,
                patient_name,
                phone,
                gender,
                total,
                payment_method,
                "Billing Done"
            ))

        for t in tests:
            cursor.execute("""
                INSERT INTO bill_items (
                    invoice_no, test_name, price, service_code, sample_type, tat, b2b
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_no,
                t.get("name"),
                float(t.get("mrp", 0)),
                t.get("serviceCode", ""),
                t.get("sampleType", ""),
                t.get("tat", ""),
                float(t.get("b2b", 0))
            ))

        conn.commit()

        return jsonify({
            "success": True,
            "invoice_no": invoice_no
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        conn.close()
# import_tests_from_excel()
import_tests_from_excel()


@app.route("/api/bills", methods=["GET"])
def get_bills_api():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM bills ORDER BY id DESC
    """)
    bills = cursor.fetchall()

    result = []

    for b in bills:
        invoice_no = b["invoice_no"]

        # 🔥 FIND UPLOADED REPORT
        uploaded_file = None

        uploaded_file = b["uploaded_report_file"] if "uploaded_report_file" in b.keys() else None

        cursor.execute("""
            SELECT test_name, price, b2b FROM bill_items WHERE invoice_no=?
        """, (invoice_no,))
        tests = cursor.fetchall()

        result.append({
            "id": invoice_no,

            # 🔥 SEND REPORT FILE TO FRONTEND
            "uploaded_report": uploaded_file,

            "clientId": b["client_id"] if "client_id" in b.keys() else "-",
            "clientName": b["client_name"] if "client_name" in b.keys() else "-",
            "patientName": b["patient_name"],
            "patientMobile": b["phone"],
            "paymentStatus": b["payment_method"],

            "tests": [
                {
                    "name": t["test_name"],
                    "mrp": t["price"],
                    "b2b": t["b2b"]
                } for t in tests
            ],

            "processStatus": b["process_status"] or "Billing Done"
        })

    conn.close()
    return jsonify(result)

@app.route("/clients", methods=["GET"])
def clients_page():
    return render_template("clients.html")


@app.route("/checkreport", methods=["GET"])
def checkreport_page():
    return render_template("checkreport.html")



@app.route("/clientprocess", methods=["GET"])
def clientprocess_page():
    return render_template("clientprocess.html")



@app.route("/barcode")
def barcode_page():
    return render_template("barcode.html")

from collections import defaultdict

@app.route("/api/barcode-data/<invoice_no>", methods=["GET"])
def barcode_data_api(invoice_no):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 🔥 UPDATE STATUS TO BARCODE CREATED ONLY FIRST TIME
    cursor.execute("""
        UPDATE bills
        SET process_status = ?
        WHERE invoice_no = ?
        AND (
            process_status IS NULL
            OR process_status = ''
            OR process_status = 'Billing Done'
        )
    """, (
        "Barcode Created",
        invoice_no
    ))

    conn.commit()

    # 🔹 Get bill details
    cursor.execute("""
        SELECT 
            invoice_no,
            patient_name,
            phone,
            total,
            payment_method,
            client_name
        FROM bills
        WHERE invoice_no=?
    """, (invoice_no,))
    bill = cursor.fetchone()

    if not bill:
        conn.close()
        return jsonify({"success": False, "message": "Bill not found"}), 404

    # 🔹 Get all tests
    cursor.execute("""
        SELECT 
            test_name,
            price,
            service_code,
            sample_type,
            tat,
            b2b
        FROM bill_items
        WHERE invoice_no=?
    """, (invoice_no,))
    items = cursor.fetchall()

    # 🔥 GROUP BY SAMPLE TYPE (IMPORTANT FIX)
    sample_groups = defaultdict(list)

    for item in items:
        sample_type = item["sample_type"] or "Sample"
        sample_groups[sample_type].append(item)

    samples = []

    for i, (sample_type, group_items) in enumerate(sample_groups.items(), start=1):
        samples.append({
            "sample_type": sample_type,
            "barcode": f"{invoice_no}-S{i}",
            "status": "Barcode Created",
            "tests": [
                {
                    "test_name": item["test_name"],
                    "service_code": item["service_code"] or "-",
                    "tat": item["tat"] or "-",
                    "sample_type": item["sample_type"] or "-",
                    "price": item["price"],
                    "b2b": item["b2b"] or 0
                }
                for item in group_items
            ]
        })

    conn.close()

    return jsonify({
        "success": True,
        "invoice_no": bill["invoice_no"],
        "patient_name": bill["patient_name"],
        "patient_mobile": bill["phone"],
        "client_name": bill["client_name"] or "-",
        "total_tests": len(items),
        "total_samples": len(samples),
        "bill_status": "Billing Done",
        "sample_status": "Barcode Created",
        "samples": samples
    })


@app.route("/api/mark-sample-ready", methods=["POST"])
def mark_sample_ready():

    data = request.get_json()
    barcode = data.get("barcode", "")

    if not barcode:
        return jsonify({
            "success": False,
            "message": "Barcode missing"
        }), 400

    invoice_no = barcode.split("-S")[0]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            UPDATE bills
            SET process_status = ?
            WHERE invoice_no = ?
        """, (
            "Ready For Testing",
            invoice_no
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Status updated"
        })

    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        conn.close()


@app.route("/api/update-testing-status", methods=["POST"])
def update_testing_status():

    data = request.get_json()

    barcode = data.get("barcode", "")
    status = data.get("status", "")

    if not barcode or not status:
        return jsonify({
            "success": False,
            "message": "Barcode and status required"
        }), 400

    invoice_no = barcode.split("-S")[0]

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            UPDATE bills
            SET process_status = ?
            WHERE invoice_no = ?
        """, (
            status,
            invoice_no
        ))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Testing status updated"
        })

    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        conn.close()



# new report test parameters 
def import_parameter_master():

    conn = get_db_connection()
    cursor = conn.cursor()

    # DROP OLD TABLE
    cursor.execute("DROP TABLE IF EXISTS parameter_master")

    # CREATE NEW TABLE
    cursor.execute("""
        CREATE TABLE parameter_master (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_code TEXT,
            parameter_name TEXT,
            unit TEXT,
            normal_range TEXT,
            method TEXT
        )
    """)

    # READ EXCEL
    df = pd.read_excel("test_parameters.xlsx", sheet_name="Parameters")

    # CLEAN COLUMN NAMES
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    print("LOADED FILE: test_parameters.xlsx")
    print("PARAMETER FILE COLUMNS:", df.columns.tolist())
    print(df.head())

    inserted = 0

    # INSERT DATA
    for _, row in df.iterrows():

        cursor.execute("""
            INSERT INTO parameter_master (
                service_code,
                parameter_name,
                unit,
                normal_range,
                method
            )
            VALUES (?, ?, ?, ?, ?)
        """, (

            str(row.get("service_code", "")).strip(),
            str(row.get("parameter_name", "")).strip(),
            str(row.get("unit", "")).strip(),
            str(row.get("normal_range", "")).strip(),
            str(row.get("method", "")).strip()

        ))

        inserted += 1

    conn.commit()
    conn.close()

    print(f"✅ Parameters table recreated and {inserted} parameters imported")


@app.route("/testongo")
def testongo_page():
    return render_template("testongo.html")


@app.route("/reportentry")
def reportentry_page():
    return render_template("reportentry.html")

@app.route("/api/update-test-master", methods=["POST"])
def update_test_master():

    data = request.json

    test_name = data.get("test_name")
    unit = data.get("unit")
    ref_low = data.get("ref_low")
    ref_high = data.get("ref_high")

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE test_master
        SET unit=%s,
            ref_low=%s,
            ref_high=%s
        WHERE LOWER(test_name)=LOWER(%s)
    """, (unit, ref_low, ref_high, test_name))

    conn.commit()

    cur.close()
    conn.close()

    return jsonify({"success": True})

# clientmonitor

@app.route("/checkprogress")
def checkprogress_page():
    return render_template("checkprogress.html")


@app.route("/api/client-progress/<client_id>", methods=["GET"])
def client_progress_api(client_id):
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM bills
            WHERE client_id = ?
            ORDER BY id DESC
        """, (client_id,))

        bills = cursor.fetchall()
        result = []

        for bill in bills:
            invoice_no = bill["invoice_no"]

            cursor.execute("""
                SELECT *
                FROM bill_items
                WHERE invoice_no = ?
            """, (invoice_no,))
            items = cursor.fetchall()

            samples_map = {}

            for item in items:
                sample_type = item["sample_type"] or "Sample"

                if sample_type not in samples_map:
                    samples_map[sample_type] = {
                        "sample_type": sample_type,
                        "barcode": f"{invoice_no}-S{len(samples_map)+1}",
                        "status": "Barcode Created",
                        "tests": []
                    }

                samples_map[sample_type]["tests"].append({
                    "test_name": item["test_name"],
                    "service_code": item["service_code"] or "-",
                    "tat": item["tat"] or "-",
                    "status": "Ready"
                })

            uploaded_file = None
            uploaded_file = bill["uploaded_report_file"] if "uploaded_report_file" in bill.keys() else None
            result.append({
                "invoice_no": invoice_no,
                "patient_name": bill["patient_name"],
                "patient_mobile": bill["phone"],
                "gender": bill["gender"] if "gender" in bill.keys() else "",
                "client_name": bill["client_name"],
                "bill_status": "Billing Done",
                "sample_status": "Barcode Created",
                "progress_status": bill["process_status"] or "Billing Done",
                "total_tests": len(items),
                "total_samples": len(samples_map),
                "total_mrp": sum(float(item["price"] or 0) for item in items),
                "total_b2b": sum(float(item["b2b"] or 0) for item in items),
                "created_at": bill["created_at"],
                "samples": list(samples_map.values()),
                "uploaded_report": uploaded_file if str(bill["report_sent_to_client"]) == "1" else None,
                "uploaded_report_file": uploaded_file,
                "report_sent_to_client": bill["report_sent_to_client"],
                "payment_status": bill["payment_method"],
                "tests": [
                    {
                        "name": item["test_name"],
                        "mrp": item["price"],
                        "b2b": item["b2b"],
                        "service_code": item["service_code"] or "-",
                        "sample_type": item["sample_type"] or "-",
                        "tat": item["tat"] or "-"
                    }
                    for item in items
                ]
            })

        return jsonify({
            "success": True,
            "data": result
        })

    except Exception as e:
        print("ERROR in client-progress:", str(e))
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        if conn:
            conn.close()



@app.route("/accounts")
def accounts_page():
    return render_template("accounts.html")


@app.route("/api/accounts")
def accounts_api():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            b.invoice_no,
            b.client_id,
            b.client_name,
            b.patient_name,
            b.phone AS patient_mobile,
            b.created_at,
            b.payment_method,
            SUM(bi.price) AS total_mrp,
            SUM(bi.b2b) AS total_b2b
        FROM bills b
        LEFT JOIN bill_items bi
        ON b.invoice_no = bi.invoice_no
        GROUP BY b.invoice_no
        ORDER BY b.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    data = []

    for r in rows:
        data.append({
            "invoice_no": r["invoice_no"],
            "client_id": r["client_id"],
            "client_name": r["client_name"],
            "patient_name": r["patient_name"],
            "patient_mobile": r["patient_mobile"],
            "created_at": r["created_at"],
            "payment_status": r["payment_method"],
            "total_mrp": r["total_mrp"] or 0,
            "total_b2b": r["total_b2b"] or 0,
            "paid_at": None
        })

    return jsonify({
        "success": True,
        "data": data
    })



@app.route("/api/accounts/approve-payment", methods=["POST"])
def approve_account_payment():
    data = request.get_json()

    invoice_no = data.get("invoice_no")

    if not invoice_no:
        return jsonify({
            "success": False,
            "message": "Invoice number required"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            UPDATE bills
            SET payment_method = 'Admin Paid'
            WHERE invoice_no = ?
        """, (invoice_no,))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Payment approved"
        })

    except Exception as e:
        conn.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        conn.close()



@app.route("/api/client/payment-submitted", methods=["POST"])
def client_payment_submitted_api():
    data = request.get_json()

    client_id = data.get("client_id")
    invoices = data.get("invoices", [])

    if not client_id or not invoices:
        return jsonify({
            "success": False,
            "message": "Client and invoices required"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        placeholders = ",".join(["?"] * len(invoices))

        cursor.execute(f"""
            UPDATE bills
            SET payment_method = 'Payment Submitted'
            WHERE client_id = ?
            AND invoice_no IN ({placeholders})
            AND payment_method != 'Admin Paid'
        """, [client_id] + invoices)

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Payment acknowledgement received"
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        conn.close()

@app.route("/api/upload-report", methods=["POST"])
def upload_report_api():
    file = request.files.get("file")
    invoice_no = request.form.get("invoice_no", "")
    barcode = request.form.get("barcode", "")
    report_no = request.form.get("report_no", "").strip()

    if not file:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    if report_no:
        ext = os.path.splitext(file.filename)[1]
        filename = secure_filename(f"{report_no}{ext}")
    else:
        filename = secure_filename(f"{invoice_no}_{barcode}_{file.filename}")

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE bills
        SET process_status = ?,
            report_sent_to_client = 0,
            uploaded_report_file = ?
        WHERE invoice_no = ?
    """, (
        "Report Ready",
        filename,
        invoice_no
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "file": filename
    })

@app.route("/api/send-report-to-client", methods=["POST"])
def send_report_to_client():

    data = request.get_json()

    invoice_no = data.get("invoice_no")

    if not invoice_no:
        return jsonify({
            "success": False,
            "message": "Invoice number required"
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
            UPDATE bills
            SET report_sent_to_client = 1
            WHERE invoice_no = ?
        """, (invoice_no,))

        conn.commit()

        return jsonify({
            "success": True,
            "message": "Report sent successfully"
        })

    except Exception as e:

        conn.rollback()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500

    finally:
        conn.close()


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/api/save-report-pdf", methods=["POST"])
def save_report_pdf():

    try:
        pdf = request.files.get("pdf")
        report_no = request.form.get("report_no", "").strip()
        invoice_no = request.form.get("invoice_no", "").strip()
        barcode = request.form.get("barcode", "").strip()

        if not pdf:
            return jsonify({
                "success": False,
                "message": "No PDF received"
            }), 400

        if not report_no:
            return jsonify({
                "success": False,
                "message": "Report number missing"
            }), 400

        filename = secure_filename(report_no + ".pdf")
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        pdf.save(filepath)

        conn = get_db_connection()
        cursor = conn.cursor()


        cursor.execute("""
        CREATE TABLE IF NOT EXISTS verified_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_no TEXT,
            invoice_no TEXT,
            barcode TEXT,
            filename TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        existing_cols = [
            row["name"] for row in cursor.execute(
                "PRAGMA table_info(verified_reports)"
            ).fetchall()
        ]

        if "filename" not in existing_cols:
            cursor.execute("ALTER TABLE verified_reports ADD COLUMN filename TEXT")
            conn.commit()

        cursor.execute("""
            INSERT INTO verified_reports (
                report_no,
                invoice_no,
                barcode,
                filename
            )
            VALUES (?, ?, ?, ?)
        """, (
            report_no,
            invoice_no,
            barcode,
            filename
        ))

        try:
            cursor.execute("""
                UPDATE bills
                SET process_status = ?,
                    report_sent_to_client = 0,
                    uploaded_report_file = ?
                WHERE invoice_no = ?
            """, (
                "Report Ready",
                filename,
                invoice_no
            ))
        except Exception as e:
            print("BILLS UPDATE SKIPPED:", e)

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "file": filename,
            "verify_url": "/verify-report/" + report_no
        })

    except Exception as e:
        print("SAVE REPORT PDF ERROR:", str(e))
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@app.route("/verify-report/<report_no>")
def verify_report(report_no):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT filename, created_at
        FROM verified_reports
        WHERE report_no = ?
        ORDER BY id DESC
        LIMIT 1
    """, (report_no,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return "Invalid report or report not found", 404

    created_at = row["created_at"]

    if created_at:
        created_date = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
        expiry_date = created_date + timedelta(days=30)

        if datetime.now() > expiry_date:
            return """
            <div style='font-family:Arial;text-align:center;margin-top:80px;'>
                <h2>Report verification link expired</h2>
                <p>This QR verification link was valid for 30 days only.</p>
                <p>Please contact Rapid Labs for verification.</p>
            </div>
            """, 403

    return redirect("/uploads/" + row["filename"])

@app.route("/api/delete-report", methods=["POST"])
def delete_report():
    data = request.get_json()
    filename = data.get("file")

    if not filename:
        return jsonify({"success": False, "message": "File missing"}), 400

    filepath = os.path.join(UPLOAD_FOLDER, secure_filename(filename))

    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"success": True})

    return jsonify({"success": False, "message": "File not found"})



@app.route("/api/generate-ai-note", methods=["POST"])
def generate_ai_note():

    data = request.json
    tests = data.get("tests", [])

    abnormal_tests = []
    normal_tests = []

    for t in tests:

        result = analyze_test_status(
            str(t.get("test", "")).strip(),
            str(t.get("value", "")).strip(),
            str(t.get("unit", "")).strip(),
            str(t.get("range", "")).strip()
        )

        if not result:
            continue

        if result["status"] == "normal":
            normal_tests.append(result)
        else:
            abnormal_tests.append(result)

    if abnormal_tests:
        final_note = build_advanced_clinical_note(abnormal_tests)
    else:
        final_note = """
    
        All reported parameters are within acceptable reference limits.<br>
        No significant abnormal laboratory variation is noted in the provided results.<br>
        Clinical correlation is advised.
        """

    return jsonify({
        "success": True,
        "note": final_note
    })


def analyze_test_status(test_name, value, unit, ref_range):

    import re

    if not test_name or not value:
        return None

    try:
        val = float(str(value).replace(",", "").strip())
    except:
        return None

    numbers = re.findall(r"\d+\.?\d*", ref_range)

    if len(numbers) >= 2:
        low = float(numbers[0])
        high = float(numbers[1])
    elif len(numbers) == 1:
        low = None
        high = float(numbers[0])
    else:
        low = None
        high = None

    status = "normal"

    if low is not None and val < low:
        status = "low"
    elif high is not None and val > high:
        status = "high"

    return {
        "name": test_name,
        "value": value,
        "unit": unit,
        "range": ref_range,
        "status": status,
        "category": detect_test_category(test_name)
    }


def detect_test_category(test_name):

    name = test_name.lower()

    if any(x in name for x in ["glucose", "sugar", "fbs", "ppbs", "rbs", "hba1c"]):
        return "sugar"

    if any(x in name for x in ["hemoglobin", "hb", "rbc", "hematocrit", "mcv", "mch", "mchc"]):
        return "cbc_red"

    if any(x in name for x in ["wbc", "tlc", "neutrophil", "lymphocyte", "eosinophil", "monocyte", "basophil"]):
        return "cbc_white"

    if "platelet" in name:
        return "platelet"

    if any(x in name for x in ["cholesterol", "triglyceride", "ldl", "vldl", "hdl"]):
        return "lipid"

    if any(x in name for x in ["sgpt", "sgot", "alt", "ast", "bilirubin", "alkaline", "alp", "protein", "albumin", "globulin"]):
        return "liver"

    if any(x in name for x in ["creatinine", "urea", "uric acid", "bun"]):
        return "kidney"

    if any(x in name for x in ["tsh", "t3", "t4", "thyroid"]):
        return "thyroid"

    if any(x in name for x in ["vitamin d", "vit d", "vitamin b12", "b12", "ferritin", "iron", "calcium"]):
        return "vitamin_mineral"

    return "general"


def build_advanced_clinical_note(abnormal_tests):

    test_parts = []
    categories = set()
    high_count = 0
    low_count = 0

    for t in abnormal_tests:

        categories.add(t["category"])

        if t["status"] == "high":
            high_count += 1
            status_text = "elevated"
        else:
            low_count += 1
            status_text = "reduced"

        value_text = f"{t['value']} {t['unit']}".strip()

        test_parts.append(
            f"<b>{t['name']}</b> (<b>{value_text}</b>) is {status_text}"
        )

    abnormal_summary = ", ".join(test_parts)

    category_note = build_category_summary(categories, high_count, low_count)

    final_note = f"""
    <b>Clinical Interpretation:</b><br>
    {abnormal_summary}.<br>
    {category_note}<br>
    These findings should be interpreted along with clinical history and doctor evaluation.
    """

    return final_note


def build_category_summary(categories, high_count, low_count):

    if "sugar" in categories:
        return "The pattern may suggest altered glycemic status or poor glucose control."

    if "lipid" in categories:
        return "The pattern may indicate lipid imbalance and possible cardiovascular risk."

    if "liver" in categories:
        return "The pattern may suggest hepatobiliary involvement or liver enzyme variation."

    if "kidney" in categories:
        return "The pattern may suggest altered renal function or metabolic imbalance."

    if "thyroid" in categories:
        return "The pattern may suggest thyroid functional variation."

    if "cbc_red" in categories:
        return "The pattern may suggest variation in red cell indices or hemoglobin status."

    if "cbc_white" in categories:
        return "The pattern may suggest infection, inflammation, or immune response variation."

    if "platelet" in categories:
        return "The pattern may suggest platelet count variation requiring clinical correlation."

    if "vitamin_mineral" in categories:
        return "The pattern may suggest vitamin, mineral, or nutritional imbalance."

    if high_count > 0 and low_count > 0:
        return "Multiple parameters show mixed high and low variations from reference limits."

    if high_count > 0:
        return "One or more parameters are above the reference range."

    if low_count > 0:
        return "One or more parameters are below the reference range."

    return "Laboratory variation is noted."




















import random
import string
from datetime import datetime

def generate_barcode():
    return "LAB" + datetime.now().strftime("%Y%m%d%H%M%S") + ''.join(random.choices(string.digits, k=3))


@app.route("/create-sample", methods=["POST"])
def create_sample():
    data = request.json

    name = data.get("name")
    mobile = data.get("mobile")
    gender = data.get("gender")
    client_id = data.get("client_id")
    test_ids = data.get("test_ids")  # list

    if not name or not test_ids:
        return jsonify({"error": "Missing required fields"}), 400

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create patient
    cursor.execute("""
        INSERT INTO lab_patients (name, mobile, gender, client_id)
        VALUES (?, ?, ?, ?)
    """, (name, mobile, gender, client_id))

    patient_id = cursor.lastrowid

    # 2. Create sample (barcode)
    barcode = generate_barcode()

    cursor.execute("""
        INSERT INTO lab_samples (barcode, patient_id)
        VALUES (?, ?)
    """, (barcode, patient_id))

    sample_id = cursor.lastrowid

    # 3. Add tests
    for test_id in test_ids:
        cursor.execute("""
            INSERT INTO lab_sample_tests (sample_id, test_id)
            VALUES (?, ?)
        """, (sample_id, test_id))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Sample created successfully",
        "barcode": barcode,
        "sample_id": sample_id
    })




@app.route("/scan-sample/<barcode>", methods=["GET"])
def scan_sample(barcode):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get sample + patient
    cursor.execute("""
        SELECT s.id, s.barcode, p.name, p.mobile, p.gender
        FROM lab_samples s
        JOIN lab_patients p ON s.patient_id = p.id
        WHERE s.barcode = ?
    """, (barcode,))

    sample = cursor.fetchone()

    if not sample:
        return jsonify({"error": "Sample not found"}), 404

    sample_id = sample[0]

    # Get tests
    cursor.execute("""
        SELECT st.id, t.test_name, st.status
        FROM lab_sample_tests st
        JOIN lab_tests t ON st.test_id = t.id
        WHERE st.sample_id = ?
    """, (sample_id,))

    tests = cursor.fetchall()

    conn.close()

    return jsonify({
        "barcode": sample[1],
        "patient_name": sample[2],
        "mobile": sample[3],
        "gender": sample[4],
        "tests": [
            {
                "sample_test_id": t[0],
                "test_name": t[1],
                "status": t[2] if t[2] else "Pending",
            } for t in tests
        ]
    })


from datetime import datetime

@app.route("/start-test/<int:sample_test_id>", methods=["POST"])
def start_test(sample_test_id):
    data = request.json
    duration = data.get("duration_seconds")  # from frontend

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # update test
    cursor.execute("""
        UPDATE lab_sample_tests
        SET status = 'Running',
            start_time = ?,
            duration_seconds = ?
        WHERE id = ?
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        duration,
        sample_test_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Test started",
        "sample_test_id": sample_test_id
    })



@app.route("/complete-test/<int:sample_test_id>", methods=["POST"])
def complete_test(sample_test_id):
    from datetime import datetime

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE lab_sample_tests
        SET status = 'Completed',
            end_time = ?
        WHERE id = ?
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        sample_test_id
    ))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Test completed",
        "sample_test_id": sample_test_id
    })






UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/upload-report/<int:sample_test_id>", methods=["POST"])
def upload_report_lab(sample_test_id):
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "Empty file"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    file.save(filepath)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE lab_sample_tests
        SET report_file = ?
        WHERE id = ?
    """, (filepath, sample_test_id))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Report uploaded",
        "file": filepath
    })


@app.route("/client-samples/<int:client_id>", methods=["GET"])
def client_samples(client_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.barcode, p.name,
               COUNT(st.id),
               SUM(CASE WHEN st.status = 'Completed' THEN 1 ELSE 0 END)
        FROM lab_samples s
        JOIN lab_patients p ON s.patient_id = p.id
        JOIN lab_sample_tests st ON s.id = st.sample_id
        WHERE p.client_id = ?
        GROUP BY s.id
    """, (client_id,))

    data = cursor.fetchall()
    conn.close()

    result = []

    for row in data:
        total_tests = row[2]
        completed_tests = row[3]

        if completed_tests == 0:
            status = "Collected"
        elif completed_tests < total_tests:
            status = "Running"
        else:
            status = "Report Ready"

        result.append({
            "barcode": row[0],
            "patient_name": row[1],
            "status": status
        })

    return jsonify(result)



@app.route("/lab")
def lab_home():
    return render_template("lab_home.html")


@app.route("/lab/create")
def create_page():
    return render_template("create.html")


@app.route("/lab/scan")
def scan_page():
    return render_template("scan.html")
    
@app.route("/client/lab-dashboard")
def client_lab_dashboard():
    return render_template("client_lab_dashboard.html")


# ==============================
# RUN SERVER
# ==============================



import_tests_from_excel()
import_parameter_master()



if __name__ == "__main__":
    app.run(
    host="0.0.0.0",
    port=5000,
    debug=True
)

  
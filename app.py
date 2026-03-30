from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
import sqlite3
from math import radians, cos, sin, asin, sqrt
import os
from flask import request, jsonify
from datetime import datetime
import razorpay
import firebase_admin
from firebase_admin import credentials, messaging
import json
from flask_mail import Mail, Message
from flask import send_file

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



    conn.commit()
    conn.close()


# CALL THIS
init_db()




# email

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.environ.get("EMAIL_PASS")


mail = Mail(app)


# report 

def get_report(task_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT report_file 
        FROM reports 
        WHERE task_id = ?
    """, (task_id,))

    row = cursor.fetchone()
    conn.close()

    return row["report_file"] if row else None


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

    conn.commit()
    conn.close()

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

# upload report
@app.route("/api/upload-report/<int:lead_id>", methods=["POST"])
def upload_report(lead_id):

    try:

        if "report" not in request.files:
            return jsonify({"success": False, "message": "No file uploaded"})

        file = request.files["report"]

        if file.filename == "":
            return jsonify({"success": False, "message": "Empty file"})

        filename = f"report_{lead_id}.pdf"

        os.makedirs("static/reports", exist_ok=True)

        save_path = os.path.join("static", "reports", filename)

        file.save(save_path)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM reports WHERE lead_id=?", (lead_id,))
        existing = cursor.fetchone()

        if existing:

            cursor.execute("""
            UPDATE reports
            SET report_file=?, report_status='Completed'
            WHERE lead_id=?
            """, (save_path, lead_id))

        else:

            cursor.execute("""
            INSERT INTO reports (lead_id, report_file, report_status)
            VALUES (?, ?, 'Completed')
            """, (lead_id, save_path))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "file": save_path
        })

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"success": False, "message": str(e)})

# Update Report Status

@app.route("/api/update-report-status", methods=["POST"])
def update_report_status():

    data = request.json

    lead_id = data["lead_id"]
    status = data["status"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reports WHERE lead_id=?", (lead_id,))
    existing = cursor.fetchone()

    if existing:

        cursor.execute("""
        UPDATE reports
        SET report_status=?
        WHERE lead_id=?
        """, (status, lead_id))

    else:

        cursor.execute("""
        INSERT INTO reports (lead_id, report_status)
        VALUES (?, ?)
        """, (lead_id, status))

    conn.commit()
    conn.close()

    return jsonify({"success": True})






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

    login_email = data.get("login_email")
    login_password = data.get("login_password")

    conn = get_db_connection()
    cursor = conn.cursor()

    # insert into staff table
    cursor.execute("""
    INSERT INTO staff
    (name,mobile,email,role,salary,incentive,status,join_date)
    VALUES (?,?,?,?,?,?,?,?)
    """,(name,mobile,email,role,salary,incentive,"Active",join_date))

    # create login user
    cursor.execute("""
    INSERT INTO users (name,email,password_hash,role)
    VALUES (?,?,?,?)
    """,(name,login_email,login_password,"STAFF"))

    conn.commit()
    conn.close()

    return jsonify({"success":True})

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
    JOIN staff ON users.name = staff.name
    WHERE staff.id = ? AND users.role='STAFF'
    """,(id,))

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

    login_email = data.get("login_email")
    login_password = data.get("login_password")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Update staff table
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
    """,(
        name,
        mobile,
        email,
        role,
        salary,
        incentive,
        join_date,
        staff_id
    ))

    # Update login credentials in users table
    cursor.execute("""
    UPDATE users
    SET email=?,
        password_hash=?
    WHERE name=? AND role='STAFF'
    """,(
        login_email,
        login_password,
        name
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

    data = request.json
    test_name = data.get("test_name")
    price = data.get("price")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO tests (name, price) VALUES (?, ?)",
        (test_name, price)
    )

    conn.commit()
    conn.close()

    return jsonify({"status": "success"})


@app.route('/get-tests')
def get_tests():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, price FROM tests")
    rows = cursor.fetchall()

    conn.close()

    tests = []

    for row in rows:
        tests.append({
            "id": row["id"],
            "name": row["name"],
            "price": row["price"]
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

    conn.close()

    return render_template("report.html", bill=bill)

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

# ---------------- UPLOAD PRESCRIPTION ----------------
@app.route("/api/upload-prescription", methods=["POST"])
def upload_prescription():
    try:
        file = request.files.get("file")
        name = request.form.get("name")
        mobile = request.form.get("mobile")
        notes = request.form.get("notes")

        if not file or file.filename == "":
            return jsonify({"success": False, "message": "No file uploaded"})

        # create folder if not exist
        os.makedirs("static/prescriptions", exist_ok=True)

        # unique filename
        filename = f"{mobile}_{int(datetime.now().timestamp())}_{file.filename}"

        # save file in folder
        save_path = os.path.join("static/prescriptions", filename)
        file.save(save_path)

        # path to store in DB and use in browser
        filepath = f"/static/prescriptions/{filename}"

        # insert into DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO prescriptions (name, mobile, file, notes, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (name, mobile, filepath, notes))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "file": filepath})

    except Exception as e:
        print("UPLOAD ERROR:", e)
        return jsonify({"success": False, "message": str(e)})



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
                "report_url": f"http://127.0.0.1:5000/{file_path}"
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



# ==============================
# RUN SERVER
# ==============================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
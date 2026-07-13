from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, jsonify, session, redirect
from werkzeug.utils import secure_filename
from datetime import datetime
from dotenv import load_dotenv
import os
import sqlite3

load_dotenv()

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "dev-secret-key"
)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/report")
def report():

    if "user_email" not in session:
        return redirect("/login")

    return render_template("report.html")

@app.route("/dashboard")
def dashboard():

    if "user_email" not in session:
        return redirect("/login")

    return render_template("dashboard.html")

@app.route("/analytics")
def analytics():
    return render_template("analytics.html")

@app.route("/map")
def map_page():
    return render_template("map.html")

@app.route("/admin")
def admin():

    if "user_email" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return "Access Denied. Admins Only."

    return render_template("admin.html")

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/save_report", methods=["POST"])
def save_report():

    print("FORM DATA:", request.form)
    print("FILES:", request.files)

    image = request.files.get("image")

    image_path = None

    if image and image.filename != "":

        filename = secure_filename(image.filename)

        image.save(
            os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )
        )

        image_path = "uploads/" + filename

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    new_issue = request.form["issue"]
    new_location = request.form["location"]

    print("NEW ISSUE =", new_issue)
    print("NEW LOCATION =", new_location)

    cursor.execute("""
    SELECT complaint_id, issue, location, status
    FROM reports
    WHERE issue = ?
    AND status != 'Resolved'
    """, (new_issue,))

    existing_reports = cursor.fetchall()
    print("EXISTING REPORTS =", existing_reports)

    for report in existing_reports:
        print("CHECKING REPORT =", report)

        old_location = report[2]

        try:

            old_lat, old_lon = map(float, old_location.split(","))
            new_lat, new_lon = map(float, new_location.split(","))

            # Approximate distance check
            distance = (
                ((old_lat - new_lat) ** 2) +
                ((old_lon - new_lon) ** 2)
            ) ** 0.5

            print("OLD LOCATION =", old_location)
            print("NEW LOCATION =", new_location)
            print("DISTANCE =", distance)

            print("DISTANCE =", distance)

            if False:   # roughly 100 meters

                conn.close()

                return jsonify({
                    "message":
                    f"Duplicate Complaint Found. Existing ID: {report[0]}"
                })  

        except Exception as e:
            print("ERROR =", e)
            print("OLD LOCATION =", old_location)
            print("NEW LOCATION =", new_location)

    issue_text = (
        request.form["issue"] +
        " " +
        request.form["description"]
    ).lower()

    if any(word in issue_text for word in
       ["accident", "collapse", "hospital", "fire"]):

        priority = "High"

    elif any(word in issue_text for word in
         ["garbage", "drainage", "waterlogging"]):

        priority = "Medium"

    else:

        priority = "Low"

    cursor.execute("""
    INSERT INTO reports
(
    complaint_id,
    issue,
    location,
    description,
    status,
    date,
    ai_prediction,
    ai_confidence,
    verification_status,
    user_category,
    image_path,
    priority,
    user_email
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        request.form["complaint_id"],
        request.form["issue"],
        request.form["location"],
        request.form["description"],
        request.form["status"],
        request.form["date"],
        request.form["ai_prediction"],
        request.form["ai_confidence"],
        request.form["verification_status"],
        request.form["user_category"],
        image_path,
        priority,
        session["user_email"]

    ))

    cursor.execute("""
INSERT INTO notifications
(
    complaint_id,
    message
)
VALUES (?, ?)
""", (

    request.form["complaint_id"],
    "Complaint Submitted Successfully"

))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Report saved successfully"
    })

@app.route("/get_reports")
def get_reports():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reports")

    reports = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify(reports)

@app.route("/admin_data")
def admin_data():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reports")
    reports = [
        dict(row)
        for row in cursor.fetchall()
    ]

    cursor.execute(
        "SELECT COUNT(*) FROM reports"
    )
    total_reports = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM reports WHERE status='Pending'"
    )
    pending_reports = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM reports WHERE status='In Progress'"
    )
    inprogress_reports = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM reports WHERE status='Resolved'"
    )
    resolved_reports = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "reports": reports,
        "total_reports": total_reports,
        "pending_reports": pending_reports,
        "inprogress_reports": inprogress_reports,
        "resolved_reports": resolved_reports
    })

@app.route("/update_status", methods=["POST"])
def update_status():

    if session.get("role") != "admin":
        return jsonify({
            "message": "Access Denied"
        }), 403

    data = request.json

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE reports
        SET status = ?
        WHERE complaint_id = ?
        """,
        (
            data["status"],
            data["complaint_id"]
        )
    )

    cursor.execute("""
INSERT INTO notifications
(
    complaint_id,
    message
)
VALUES (?, ?)
""", (

    data["complaint_id"],
    f"Status Updated To {data['status']}"

))

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Status updated successfully"
    })

@app.route("/delete_report", methods=["POST"])
def delete_report():

    if session.get("role") != "admin":
        return jsonify({
        "message": "Access Denied"
    }), 403

    data = request.json

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM reports
        WHERE complaint_id = ?
        """,
        (
            data["complaint_id"],
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Report deleted successfully"
    })

@app.route("/get_stats")
def get_stats():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM reports")
    total_reports = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM reports WHERE status='Resolved'"
    )
    resolved_reports = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "total_reports": total_reports,
        "resolved_reports": resolved_reports,
        "citizens_engaged": total_reports,
        "ai_accuracy": 95
    })

@app.route("/get_next_complaint_id")
def get_next_complaint_id():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM reports"
    )

    count = cursor.fetchone()[0]

    conn.close()

    next_id = "CIV" + str(count + 1).zfill(3)

    return jsonify({
        "complaint_id": next_id
    })

@app.route("/debug_columns")
def debug_columns():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(reports)")

    columns = cursor.fetchall()

    conn.close()

    return jsonify(columns)

@app.route("/add_image_column")
def add_image_column():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "ALTER TABLE reports ADD COLUMN image_path TEXT"
        )

        conn.commit()

        message = "image_path column added"

    except Exception as e:

        message = str(e)

    conn.close()

    return jsonify({
        "message": message
    })


@app.route("/create_users_table")
def create_users_table():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        full_name TEXT,

        email TEXT UNIQUE,

        phone TEXT,

        password TEXT

    )
    """)

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Users table created successfully"
    })


@app.route("/register_user", methods=["POST"])
def register_user():

    data = request.json

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    try:

        hashed_password = generate_password_hash(
            data["password"]
        )
        print("HASH GENERATED:", hashed_password)

        cursor.execute("""
        INSERT INTO users
        (
            full_name,
            email,
            phone,
            password
        )
        VALUES (?, ?, ?, ?)
        """, (
            data["full_name"],
            data["email"],
            data["phone"],
            hashed_password
        ))

        conn.commit()

        message = "Registration Successful"

    except Exception as e:

        if "UNIQUE constraint failed" in str(e):
            message = "Email already exists. Please sign in."

        else:
            message = str(e)

    conn.close()

    return jsonify({
        "message": message
    })

@app.route("/get_users")
def get_users():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users")

    users = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify(users)

@app.route("/login_user", methods=["POST"])
def login_user():

    data = request.json

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (data["email"],)
    )

    user = cursor.fetchone()

    conn.close()

    if user and check_password_hash(
        user["password"],
        data["password"]
    ):

        session["user_email"] = data["email"]
        session["role"] = user["role"]

        return jsonify({
            "success": True,
            "message": "Login Successful"
        })

    return jsonify({
        "success": False,
        "message": "Invalid Email or Password"
    })

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

@app.route("/delete_all_users")
def delete_all_users():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute("DELETE FROM users")

    conn.commit()
    conn.close()

    return "All users deleted"

@app.route("/add_role_column")
def add_role_column():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    try:

        cursor.execute(
            "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'"
        )

        conn.commit()

        message = "Role column added successfully"

    except Exception as e:

        message = str(e)

    conn.close()

    return jsonify({
        "message": message
    })

@app.route("/make_admin")
def make_admin():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET role='admin'
        WHERE email=?
        """,
        ("test999@gmail.com",)
    )

    conn.commit()
    conn.close()

    return "Admin role assigned"

@app.route("/profile")
def profile():

    if "user_email" not in session:
        return redirect("/login")

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        (session["user_email"],)
    )

    user = cursor.fetchone()

    conn.close()

    return render_template(
        "profile.html",
        user=user
    )

@app.route("/my_profile_data")
def my_profile_data():

    if "user_email" not in session:
        return jsonify({"error": "Not logged in"})

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=?",
        (session["user_email"],)
    )

    user = dict(cursor.fetchone())

    conn.close()

    return jsonify(user)

@app.route("/track")
def track():

    if "user_email" not in session:
        return redirect("/login")

    return render_template("track.html")

@app.route("/track_complaint/<complaint_id>")
def track_complaint(complaint_id):

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM reports
        WHERE complaint_id = ?
        """,
        (complaint_id,)
    )

    report = cursor.fetchone()

    conn.close()

    if report:
        return jsonify(dict(report))

    return jsonify({
        "message": "Complaint Not Found"
    })

@app.route("/my_reports")
def my_reports():

    if "user_email" not in session:
        return redirect("/login")

    return render_template("my_reports.html")

@app.route("/my_reports_data")
def my_reports_data():

    if "user_email" not in session:
        return jsonify({"error": "Not logged in"}), 401

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM reports
        WHERE user_email = ?
        ORDER BY id DESC
        """,
        (session["user_email"],)
    )

    reports = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify(reports)

@app.route("/add_priority_column")
def add_priority_column():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "ALTER TABLE reports ADD COLUMN priority TEXT"
        )

        conn.commit()
        message = "Priority column added"

    except Exception as e:
        message = str(e)

    conn.close()

    return jsonify({
        "message": message
    })

@app.route("/heatmap_data")
def heatmap_data():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
        SELECT location, COUNT(*) as total
        FROM reports
        GROUP BY location
        ORDER BY total DESC
    """)

    data = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify(data)

@app.route("/create_notifications_table")
def create_notifications_table():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notifications(

        id INTEGER PRIMARY KEY AUTOINCREMENT,
        complaint_id TEXT,
        message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    )
    """)

    conn.commit()
    conn.close()

    return "Notifications Table Created"

@app.route("/get_notifications")
def get_notifications():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM notifications
    ORDER BY id DESC
    """)

    notifications = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify(notifications)

@app.route("/debug_notifications")
def debug_notifications():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM notifications"
    )

    data = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify(data)

@app.route("/add_officer_column")
def add_officer_column():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    try:

        cursor.execute(
            "ALTER TABLE reports ADD COLUMN assigned_officer TEXT"
        )

        conn.commit()

        message = "Officer column added"

    except Exception as e:

        message = str(e)

    conn.close()

    return jsonify({
        "message": message
    })

@app.route("/assign_officer", methods=["POST"])
def assign_officer():

    if session.get("role") != "admin":
        return jsonify({
            "message": "Access Denied"
        }), 403

    data = request.json

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE reports
        SET assigned_officer = ?
        WHERE complaint_id = ?
        """,
        (
            data["officer"],
            data["complaint_id"]
        )
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Officer Assigned Successfully"
    })

@app.route("/sla_data")
def sla_data():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM reports"
    )

    reports = []

    for row in cursor.fetchall():

        report = dict(row)

        try:

            report_date = datetime.strptime(
                report["date"],
                "%m/%d/%Y"
            )

            days_pending = (
                datetime.now() -
                report_date
            ).days

        except:

            days_pending = 0

        report["days_pending"] = days_pending

        reports.append(report)

    conn.close()

    return jsonify(reports)

@app.route("/advanced_analytics")
def advanced_analytics():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    # Issue Counts
    cursor.execute("""
    SELECT issue, COUNT(*) as total
    FROM reports
    GROUP BY issue
    ORDER BY total DESC
    """)

    issues = [
        dict(row)
        for row in cursor.fetchall()
    ]

    # Officer Counts
    cursor.execute("""
    SELECT assigned_officer,
           COUNT(*) as total
    FROM reports
    WHERE assigned_officer IS NOT NULL
    GROUP BY assigned_officer
    """)

    officers = [
        dict(row)
        for row in cursor.fetchall()
    ]

    # Priority Counts
    cursor.execute("""
    SELECT priority,
           COUNT(*) as total
    FROM reports
    GROUP BY priority
    """)

    priorities = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify({
        "issues": issues,
        "officers": officers,
        "priorities": priorities
    })

@app.route("/predictive_insights")
def predictive_insights():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
    SELECT issue, COUNT(*) as total
    FROM reports
    GROUP BY issue
    ORDER BY total DESC
    """)

    issues = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    prediction = "No Data"

    if issues:

        prediction = (
            f"Highest growth risk: "
            f"{issues[0]['issue']}"
        )

    return jsonify({
        "prediction": prediction
    })

@app.route("/government_summary")
def government_summary():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM reports"
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM reports WHERE status='Resolved'"
    )
    resolved = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM reports WHERE status='Pending'"
    )
    pending = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "total_reports": total,
        "resolved": resolved,
        "pending": pending
    })

@app.route("/overdue_complaints")
def overdue_complaints():

    conn = sqlite3.connect("database/civiceye.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM reports
    WHERE status != 'Resolved'
    """)

    data = [
        dict(row)
        for row in cursor.fetchall()
    ]

    conn.close()

    return jsonify(data)

@app.route("/add_user_email_column")
def add_user_email_column():

    conn = sqlite3.connect("database/civiceye.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "ALTER TABLE reports ADD COLUMN user_email TEXT"
        )
        conn.commit()
        message = "user_email column added"

    except Exception as e:
        message = str(e)

    conn.close()

    return jsonify({"message": message})

if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)
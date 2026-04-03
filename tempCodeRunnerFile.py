from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import date, timedelta

# 🔹 MAIL IMPORTS (ADDED)
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "supersecret-change-me"

# ---------- MAIL CONFIG (ADDED) ----------
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "abir221001020057@technoindiaeducation.com"      # 🔴 CHANGE THIS
app.config["MAIL_PASSWORD"] = "tuhw zdmv ocyr cjwm"        # 🔴 APP PASSWORD
app.config["MAIL_DEFAULT_SENDER"] = "LibraCore <abir221001020057@technoindiaeducation.com>"

mail = Mail(app)

# ---------- DB CONNECTION ----------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="lms_db"
)
cursor = db.cursor(dictionary=True)

# ---------- HELPERS ----------
def today():
    return date.today()

def logged_in():
    return "user_id" in session

def require_role(role):
    return logged_in() and session.get("role") == role

# ---------- MAIL HELPER (ADDED) ----------
def send_welcome_email(name, email, username, role):
    try:
        name = request.form["m_name"]
        email = request.form["m_email"]
        phone = request.form["m_phone"]
        duration = request.form["m_duration"]
        username = request.form["m_username"]
        password = request.form["m_password"]
        role = request.form["m_role"]

        msg = Message(
            subject="Your LibraCore Membership Details",
            recipients=[email]
        )

        msg.body = f"""
Hello {name},

Your Library Membership has been successfully created.

Here are your account details :

Name       : {name}
Email      : {email}
Phone      : {phone}
Duration   : {duration} months


Login Credentials :

Username   : {username}
Password   : {password}
Role       : {role}

Please keep this information secure.

You can now log in and access the Library Management System.

Regards,
LibraCore Team
"""

        mail.send(msg)

    except Exception as e:
        print("Mail Error:", e)


# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s AND role=%s",
            (
                request.form.get("username"),
                request.form.get("password"),
                request.form.get("role")
            )
        )
        user = cursor.fetchone()
        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            return redirect(url_for("home"))
        flash("Invalid credentials / role", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- HOME ----------
@app.route("/home")
def home():
    if not logged_in():
        return redirect(url_for("login"))
    return render_template(
        "home.html",
        username=session["username"],
        role=session["role"]
    )

# ---------- CHART ----------
@app.route("/chart")
def chart():
    return render_template("chart.html")

# ---------- MAINTENANCE ----------
@app.route("/maintenance")
def maintenance():
    if not require_role("admin"):
        flash("Only admin can access Maintenance", "error")
        return redirect(url_for("home"))

    cursor.execute("SELECT * FROM members ORDER BY id")
    members = cursor.fetchall()

    cursor.execute("SELECT * FROM books ORDER BY category, id")
    books = cursor.fetchall()

    cursor.execute("SELECT id, username, role FROM users ORDER BY id")
    users = cursor.fetchall()

    return render_template(
        "maintenance.html",
        members=members,
        books=books,
        users=users
    )

# ---------- ADMIN ACTIONS ----------
@app.route("/maintenance/add-membership", methods=["POST"])
def add_membership():
    if not require_role("admin"):
        return redirect(url_for("home"))
    name = request.form["m_name"]
    email = request.form["m_email"]
    phone = request.form["m_phone"]
    duration = request.form["m_duration"]
    username = request.form["m_username"]
    password = request.form["m_password"]
    role = request.form["m_role"]

    start = today()
    duration = int(request.form.get("m_duration", 6))
    end = start + timedelta(days=30 * duration)

    cursor.execute(
        "INSERT INTO members (name,email,phone,membership_start,membership_end) "
        "VALUES (%s,%s,%s,%s,%s)",
        (
            request.form["m_name"],
            request.form["m_email"],
            request.form["m_phone"],
            start,
            end
        )
    )
    db.commit()

    # 🔹 SEND MAIL (ADDED)
    send_welcome_email(
        name=request.form["m_name"],
        email=request.form["m_email"],
        username=request.form.get("m_username", "N/A"),
        role=request.form.get("m_role", "user")
    )

    flash("Membership added successfully", "success")
    return redirect(url_for("maintenance"))

@app.route("/maintenance/update-membership", methods=["POST"])
def update_membership():
    if not require_role("admin"):
        return redirect(url_for("home"))

    member_id = request.form["um_id"]
    action = request.form["um_action"]
    duration = int(request.form.get("um_duration", 6))

    cursor.execute("SELECT * FROM members WHERE id=%s", (member_id,))
    member = cursor.fetchone()

    if not member:
        flash("Member not found", "error")
        return redirect(url_for("maintenance"))

    if action == "extend":
        new_end = member["membership_end"] + timedelta(days=30 * duration)
        cursor.execute(
            "UPDATE members SET membership_end=%s WHERE id=%s",
            (new_end, member_id)
        )
    else:
        cursor.execute(
            "UPDATE members SET status='cancelled' WHERE id=%s",
            (member_id,)
        )

    db.commit()
    flash("Membership updated", "success")
    return redirect(url_for("maintenance"))

@app.route("/maintenance/add-book", methods=["POST"])
def add_book():
    if not require_role("admin"):
        return redirect(url_for("home"))

    cursor.execute(
        "INSERT INTO books (type,title,author,serial_no,category) "
        "VALUES (%s,%s,%s,%s,%s)",
        (
            request.form["ab_type"],
            request.form["ab_title"],
            request.form["ab_author"],
            request.form["ab_serial"],
            request.form["ab_category"]
        )
    )
    db.commit()
    flash("Book / Movie added", "success")
    return redirect(url_for("maintenance"))

@app.route("/maintenance/update-book", methods=["POST"])
def update_book():
    if not require_role("admin"):
        return redirect(url_for("home"))

    available = 1 if request.form.get("ub_available") else 0

    cursor.execute(
        "UPDATE books SET type=%s,title=%s,author=%s,category=%s,available=%s "
        "WHERE serial_no=%s",
        (
            request.form["ub_type"],
            request.form["ub_title"],
            request.form["ub_author"],
            request.form["ub_category"],
            available,
            request.form["ub_serial"]
        )
    )
    db.commit()
    flash("Book updated", "success")
    return redirect(url_for("maintenance"))

@app.route("/maintenance/user-update", methods=["POST"])
def user_update():
    if not require_role("admin"):
        return redirect(url_for("home"))

    cursor.execute(
        "UPDATE users SET password=%s, role=%s WHERE username=%s",
        (
            request.form["eu_password"],
            request.form["eu_role"],
            request.form["eu_username"]
        )
    )
    db.commit()
    flash("User updated", "success")
    return redirect(url_for("maintenance"))

# ---------- TRANSACTIONS ----------
@app.route("/transactions")
def transactions():
    if not logged_in():
        return redirect(url_for("login"))

    role = session.get("role")
    user_id = session.get("user_id")

    # ---- ADMIN: see ALL issued books ----
    if session.get("role") == "admin":
    # ADMIN → see ALL issued books
        cursor.execute("""
            SELECT 
                b.serial_no,
                b.title,
                b.author,
                b.category,
                i.issue_date,
                i.planned_return_date
            FROM issues i
            JOIN books b ON i.book_id = b.id
            WHERE i.status = 'issued'
            ORDER BY i.issue_date DESC
        """)
        borrowed_books = cursor.fetchall()

    else:
        # USER → see ONLY his borrowed books
        cursor.execute("""
            SELECT 
                b.serial_no,
                b.title,
                b.author,
                b.category,
                i.issue_date,
                i.planned_return_date
            FROM issues i
            JOIN books b ON i.book_id = b.id
            WHERE i.status = 'issued'
            AND i.member_id = %s
            ORDER BY i.issue_date DESC
        """, (session["user_id"],))
        borrowed_books = cursor.fetchall()

    return render_template(
        "transactions.html",
        today=today(),
        default_return_date=today() + timedelta(days=15),
        search_results=session.get("search_results", []),
        fine_info=session.get("fine_info"),
        borrowed_books=borrowed_books,
        role=role
    )

@app.route("/books/search", methods=["POST"])
def search_books():
    if not logged_in():
        return redirect(url_for("login"))

    name = request.form.get("bs_name")
    category = request.form.get("bs_category")

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if name:
        query += " AND title LIKE %s"
        params.append(f"%{name}%")
    if category:
        query += " AND category=%s"
        params.append(category)

    cursor.execute(query, tuple(params))
    session["search_results"] = cursor.fetchall()

    return redirect(url_for("transactions"))

@app.route("/books/issue", methods=["POST"])
def issue_book():
    if not logged_in():
        return redirect(url_for("login"))

    try:
        issue_date = date.fromisoformat(request.form["ib_issue_date"])
        return_date = date.fromisoformat(request.form["ib_return_date"])
    except ValueError:
        flash("Invalid issue or return date", "error")
        return redirect(url_for("transactions"))

    if issue_date > return_date:
        flash("Return date cannot be before issue date", "error")
        return redirect(url_for("transactions"))

    # 🔍 Check book existence & availability
    cursor.execute(
        "SELECT * FROM books WHERE title=%s AND available=1",
        (request.form["ib_name"],)
    )
    book = cursor.fetchone()

    if not book:
        flash("Book not found or already issued", "error")
        return redirect(url_for("transactions"))

    # ✅ Issue book
    cursor.execute(
        "INSERT INTO issues (book_id, member_id, issue_date, planned_return_date, status, remarks) "
        "VALUES (%s,%s,%s,%s,'issued',%s)",
        (book["id"], session["user_id"], issue_date, return_date, request.form.get("ib_remarks"))
    )

    cursor.execute("UPDATE books SET available=0 WHERE id=%s", (book["id"],))
    db.commit()

    flash("Book issued successfully", "success")
    return redirect(url_for("transactions"))

@app.route("/books/return", methods=["POST"])
def return_book():
    if not logged_in():
        return redirect(url_for("login"))

    try:
        actual_return = date.fromisoformat(request.form["rb_return_date"])
    except ValueError:
        flash("Invalid return date", "error")
        return redirect(url_for("transactions"))

    # 🔍 Validate book + serial
    cursor.execute(
        "SELECT * FROM books WHERE title=%s AND serial_no=%s",
        (request.form["rb_name"], request.form["rb_serial"])
    )
    book = cursor.fetchone()

    if not book:
        flash("Book title and serial number do not match", "error")
        return redirect(url_for("transactions"))

    # 🔍 Check issue record
    cursor.execute(
        "SELECT * FROM issues WHERE book_id=%s AND status='issued' "
        "ORDER BY issue_date DESC LIMIT 1",
        (book["id"],)
    )
    issue = cursor.fetchone()

    if not issue:
        flash("This book is not currently issued", "error")
        return redirect(url_for("transactions"))

    if actual_return < issue["issue_date"]:
        flash("Return date cannot be before issue date", "error")
        return redirect(url_for("transactions"))

    # 💰 Fine calculation
    fine = 0
    if actual_return > issue["planned_return_date"]:
        fine = (actual_return - issue["planned_return_date"]).days * 10

    session["fine_info"] = {
        "issue_id": issue["id"],
        "book_title": book["title"],
        "fine": fine,
        "return_date": actual_return.isoformat()
    }

    flash("Please confirm fine payment", "info")
    return redirect(url_for("transactions"))


@app.route("/fine/pay", methods=["POST"])
def pay_fine():
    if not logged_in():
        return redirect(url_for("login"))

    info = session.get("fine_info")
    if not info:
        return redirect(url_for("transactions"))

    if info["fine"] > 0 and not request.form.get("fp_paid"):
        flash("Please mark fine as paid", "error")
        return redirect(url_for("transactions"))

    cursor.execute(
        "UPDATE issues SET actual_return_date=%s, fine_amount=%s, status='returned' "
        "WHERE id=%s",
        (info["return_date"], info["fine"], info["issue_id"])
    )

    cursor.execute(
        "UPDATE books SET available=1 "
        "WHERE id=(SELECT book_id FROM issues WHERE id=%s)",
        (info["issue_id"],)
    )

    db.commit()
    session.pop("fine_info", None)
    flash("Book returned successfully", "success")

    return redirect(url_for("transactions"))

# ---------- REPORTS ----------
@app.route("/reports")
def reports():
    if not logged_in():
        return redirect(url_for("login"))

    cursor.execute(
        "SELECT i.*, b.title, m.name AS member_name "
        "FROM issues i "
        "JOIN books b ON i.book_id=b.id "
        "JOIN members m ON i.member_id=m.id "
        "ORDER BY i.issue_date DESC"
    )
    issues = cursor.fetchall()

    cursor.execute("SELECT * FROM books ORDER BY category, id")
    books = cursor.fetchall()

    cursor.execute("SELECT * FROM members ORDER BY id")
    members = cursor.fetchall()

    return render_template(
        "reports.html",
        issues=issues,
        books=books,
        members=members
    )

if __name__ == "__main__":
    app.run(debug=True)

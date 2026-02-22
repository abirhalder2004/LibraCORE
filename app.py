from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import date, timedelta
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "supersecret-change-me"

# ---------------- MAIL CONFIG ----------------
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = "abir221001020057@technoindiaeducation.com"
app.config["MAIL_PASSWORD"] = "**** **** **** ****"
app.config["MAIL_DEFAULT_SENDER"] = "LibraCore <abir221001020057@technoindiaeducation.com>"
mail = Mail(app)

def send_welcome_email(name, email, phone, duration, username, password, role):
    try:
        msg = Message(
            subject="Your LibraCore Membership Details",
            recipients=[email],
            sender=app.config["MAIL_DEFAULT_SENDER"]
        )

        msg.html = f"""
        <div style="font-family: Arial, sans-serif; background:#020617; padding:30px; color:#e5e7eb;">
          
          <h2 style="color:#22d3ee;">
            Welcome to 
            <span style="color:#22d3ee;">Libra</span><span style="color:#ec4899;">Core</span>
          </h2>

          <p>Hello <strong>{name}</strong>,</p>

          <p>Your library membership has been successfully created.</p>

          <h3 style="color:#38bdf8;">Membership Details</h3>
          <table style="border-collapse:collapse;">
            <tr><td><strong>Name:</strong></td><td>{name}</td></tr>
            <tr><td><strong>Email:</strong></td><td>{email}</td></tr>
            <tr><td><strong>Phone:</strong></td><td>{phone}</td></tr>
            <tr><td><strong>Duration:</strong></td><td>{duration} months</td></tr>
          </table>

          <h3 style="color:#38bdf8; margin-top:20px;">Login Credentials</h3>
          <table style="border-collapse:collapse;">
            <tr><td><strong>Username:</strong></td><td>{username}</td></tr>
            <tr><td><strong>Password:</strong></td><td>{password}</td></tr>
            <tr><td><strong>Role:</strong></td><td>{role}</td></tr>
          </table>

          <p style="margin-top:20px;">
            Please keep your credentials secure.
          </p>

          <hr style="margin:30px 0; border:1px solid #334155;">

          <div style="text-align:center;">
            <img src="cid:libracore_logo" width="140">
            <p style="font-size:12px; color:#94a3b8;">
              LibraCore Library Management System<br>
              Knowledge • Technology • Trust
            </p>
          </div>
        </div>
        """

        with app.open_resource("static/mail/libracore_logo.png") as fp:
            msg.attach(
                filename="libracore_logo.png",
                content_type="image/png",
                data=fp.read(),
                disposition="inline",
                headers={"Content-ID": "<libracore_logo>"}
            )

        mail.send(msg)
        print(f"✅ Welcome mail sent to {email}")

    except Exception as e:
        print("❌ Mail Error:", e)

# ---------------- DB ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="lms_db",
    autocommit=True
)
cursor = db.cursor(dictionary=True)

# ---------------- HELPERS ----------------
def today():
    return date.today()

def logged_in():
    return "user_id" in session

def require_role(role):
    return logged_in() and session.get("role") == role

def clear_cursor():
    while cursor.nextset():
        pass

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        cursor.execute(
            "SELECT * FROM users WHERE username=%s AND password=%s AND role=%s",
            (request.form["username"], request.form["password"], request.form["role"])
        )
        user = cursor.fetchone()
        clear_cursor()

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

# ---------------- HOME ----------------
@app.route("/home")
def home():
    if not logged_in():
        return redirect(url_for("login"))
    return render_template("home.html", username=session["username"], role=session["role"])

# ---------------- CHART ----------------
@app.route("/chart")
def chart():
    return render_template("chart.html")

# ---------------- MAINTENANCE ----------------
@app.route("/maintenance")
def maintenance():
    if not require_role("admin"):
        flash("Admin access only", "error")
        return redirect(url_for("home"))

    cursor.execute("SELECT * FROM members ORDER BY id")
    members = cursor.fetchall()
    clear_cursor()

    # ✅ BOOKS ORDERED BY ID ONLY
    cursor.execute("SELECT * FROM books ORDER BY id ASC")
    books = cursor.fetchall()
    clear_cursor()

    cursor.execute("SELECT id, username, role FROM users ORDER BY id")
    users = cursor.fetchall()
    clear_cursor()

    return render_template(
        "maintenance.html",
        members=members,
        books=books,
        users=users
    )

# ---------------- ADD MEMBERSHIP ----------------
@app.route("/maintenance/add-membership", methods=["POST"])
def add_membership():
    if not require_role("admin"):
        return redirect(url_for("home"))

    username = request.form["m_username"].strip()
    password = request.form["m_password"].strip()
    confirm  = request.form.get("m_password_confirm", "").strip()

    # 🔹 Username uniqueness
    cursor.execute("SELECT id FROM users WHERE username=%s", (username,))
    if cursor.fetchone():
        clear_cursor()
        flash("Username already exists", "error")
        return redirect(url_for("maintenance"))
    clear_cursor()

    # 🔹 Password validation
    if not password or password != confirm:
        flash("Password and Confirm Password do not match", "error")
        return redirect(url_for("maintenance"))

    start = today()
    duration = int(request.form["m_duration"])
    end = start + timedelta(days=30 * duration)

    # 🔹 Insert member
    cursor.execute("""
        INSERT INTO members (name,email,phone,membership_start,membership_end)
        VALUES (%s,%s,%s,%s,%s)
    """, (
        request.form["m_name"],
        request.form["m_email"],
        request.form["m_phone"],
        start,
        end
    ))

    # 🔹 Insert user
    cursor.execute("""
        INSERT INTO users (username,password,role)
        VALUES (%s,%s,%s)
    """, (
        username,
        password,
        request.form["m_role"]
    ))

    db.commit()  # ✅ MUST be before mail

    # ✅ SEND FULL DETAILS MAIL
    send_welcome_email(
        name=request.form["m_name"],
        email=request.form["m_email"],
        phone=request.form["m_phone"],
        duration=duration,
        username=username,
        password=password,
        role=request.form["m_role"]
    )

    flash("Membership added successfully & email sent", "success")
    return redirect(url_for("maintenance"))

# ---------------- UPDATE MEMBERSHIP ----------------
@app.route("/maintenance/update-membership", methods=["POST"])
def update_membership():
    if not require_role("admin"):
        return redirect(url_for("home"))

    member_id = request.form.get("um_id")
    action = request.form.get("um_action")
    duration = int(request.form.get("um_duration", 6))

    # 🔍 Get member
    cursor.execute("SELECT * FROM members WHERE id=%s", (member_id,))
    member = cursor.fetchone()
    cursor.fetchall()

    if not member:
        flash("Member not found", "error")
        return redirect(url_for("maintenance"))

    # 🔴 DELETE MEMBER + USER
    if action == "delete":
        # Delete user linked to this member ID
        cursor.execute("DELETE FROM users WHERE id=%s", (member_id,))
        cursor.fetchall()

        # Delete member record
        cursor.execute("DELETE FROM members WHERE id=%s", (member_id,))
        cursor.fetchall()

        db.commit()
        flash("Member and user deleted permanently", "success")
        return redirect(url_for("maintenance"))

    # ❌ CANCEL MEMBERSHIP
    if action == "cancel":
        cursor.execute(
            "UPDATE members SET status='cancelled' WHERE id=%s",
            (member_id,)
        )

    # ✅ EXTEND MEMBERSHIP
    elif action == "extend":
        new_end = member["membership_end"] + timedelta(days=30 * duration)
        cursor.execute(
            "UPDATE members SET membership_end=%s WHERE id=%s",
            (new_end, member_id)
        )

    db.commit()
    flash("Membership updated successfully", "success")
    return redirect(url_for("maintenance"))


# ---------------- ADD BOOK ----------------
@app.route("/maintenance/add-book", methods=["POST"])
def add_book():
    serial = request.form["ab_serial"]
    title = request.form["ab_title"]
    category = request.form["ab_category"]

    # serial must be unique
    cursor.execute("SELECT id FROM books WHERE serial_no=%s", (serial,))
    if cursor.fetchone():
        clear_cursor()
        flash("Serial number already exists", "error")
        return redirect(url_for("maintenance"))
    clear_cursor()

    # title + category must be unique
    cursor.execute(
        "SELECT id FROM books WHERE title=%s AND category=%s",
        (title, category)
    )
    if cursor.fetchone():
        clear_cursor()
        flash("Book already exists in this category", "error")
        return redirect(url_for("maintenance"))
    clear_cursor()

    cursor.execute("""
        INSERT INTO books (type,title,author,serial_no,category)
        VALUES (%s,%s,%s,%s,%s)
    """, (
        request.form["ab_type"],
        title,
        request.form["ab_author"],
        serial,
        category
    ))

    flash("Book added successfully", "success")
    return redirect(url_for("maintenance"))

# ---------------- UPDATE BOOK ----------------
@app.route("/maintenance/update-book", methods=["POST"])
def update_book():
    available = 1 if request.form.get("ub_available") else 0
    cursor.execute("""
        UPDATE books
        SET type=%s,title=%s,author=%s,category=%s,available=%s
        WHERE serial_no=%s
    """, (
        request.form["ub_type"],
        request.form["ub_title"],
        request.form["ub_author"],
        request.form["ub_category"],
        available,
        request.form["ub_serial"]
    ))
    flash("Book updated", "success")
    return redirect(url_for("maintenance"))

# ---------------- USER UPDATE (BY ID) ----------------
@app.route("/maintenance/user-update", methods=["POST"])
def user_update():
    if not require_role("admin"):
        return redirect(url_for("home"))

    user_id = request.form.get("um_id")
    new_username = request.form.get("eu_username").strip()
    new_password = request.form.get("eu_password", "").strip()
    new_role = request.form.get("eu_role")

    # 🔍 Check user exists by ID
    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    cursor.fetchall()

    if not user:
        flash("User not found", "error")
        return redirect(url_for("maintenance"))

    # 🔍 Check username uniqueness (excluding same user)
    cursor.execute(
        "SELECT id FROM users WHERE username=%s AND id!=%s",
        (new_username, user_id)
    )
    if cursor.fetchone():
        cursor.fetchall()
        flash("Username already exists", "error")
        return redirect(url_for("maintenance"))

    # 🔄 Update username + role
    if new_password:
        cursor.execute(
            "UPDATE users SET username=%s, password=%s, role=%s WHERE id=%s",
            (new_username, new_password, new_role, user_id)
        )
    else:
        cursor.execute(
            "UPDATE users SET username=%s, role=%s WHERE id=%s",
            (new_username, new_role, user_id)
        )

    db.commit()
    flash("User updated successfully", "success")
    return redirect(url_for("maintenance"))

@app.route("/books/search", methods=["POST"])
def search_books():
    if not logged_in():
        return redirect(url_for("login"))

    name = request.form.get("bs_name", "").strip()
    category = request.form.get("bs_category", "").strip()

    query = "SELECT * FROM books WHERE available = 1"
    params = []

    if name:
        query += " AND title LIKE %s"
        params.append(f"%{name}%")

    if category:
        query += " AND category LIKE %s"
        params.append(f"%{category}%")

    query += " ORDER BY id ASC"

    cursor.execute(query, tuple(params))
    results = cursor.fetchall()

    session["search_results"] = results
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

    cursor.execute(
        "SELECT * FROM books WHERE title=%s AND available=1",
        (request.form["ib_name"],)
    )
    book = cursor.fetchone()

    if not book:
        flash("Book not found or already issued", "error")
        return redirect(url_for("transactions"))

    cursor.execute(
        """
        INSERT INTO issues
        (book_id, member_id, issue_date, planned_return_date, status)
        VALUES (%s, %s, %s, %s, 'issued')
        """,
        (book["id"], session["user_id"], issue_date, return_date)
    )

    cursor.execute(
        "UPDATE books SET available=0 WHERE id=%s",
        (book["id"],)
    )

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

    # Validate book
    cursor.execute(
        "SELECT * FROM books WHERE title=%s AND serial_no=%s",
        (request.form["rb_name"], request.form["rb_serial"])
    )
    book = cursor.fetchone()

    if not book:
        flash("Book title and serial number do not match", "error")
        return redirect(url_for("transactions"))

    # Validate issue (only THIS user's issue)
    cursor.execute(
        """
        SELECT * FROM issues
        WHERE book_id=%s
        AND member_id=%s
        AND status='issued'
        ORDER BY issue_date DESC
        LIMIT 1
        """,
        (book["id"], session["user_id"])
    )
    issue = cursor.fetchone()

    if not issue:
        flash("This book is not issued to you", "error")
        return redirect(url_for("transactions"))

    if actual_return < issue["issue_date"]:
        flash("Return date cannot be before issue date", "error")
        return redirect(url_for("transactions"))

    # Calculate fine
    fine = 0
    if actual_return > issue["planned_return_date"]:
        fine = (actual_return - issue["planned_return_date"]).days * 10

    # 🔥 IMPORTANT: STORE IN SESSION, DO NOT UPDATE DB
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


# ---------------- TRANSACTIONS ----------------
@app.route("/transactions")
def transactions():
    if not logged_in():
        return redirect(url_for("login"))

    role = session.get("role")

    if role == "admin":
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
    else:
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


# ---------------- REPORTS ----------------
@app.route("/reports")
def reports():
    if not logged_in():
        return redirect(url_for("login"))

    cursor.execute("""
        SELECT i.*, b.title, m.name AS member_name
        FROM issues i
        JOIN books b ON i.book_id=b.id
        JOIN members m ON i.member_id=m.id
        ORDER BY i.issue_date DESC
    """)
    issues = cursor.fetchall()

    cursor.execute("SELECT * FROM books ORDER BY id")
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

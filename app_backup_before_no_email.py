import os
import re
import random
import smtplib
from datetime import datetime, timedelta
from functools import wraps
from email.message import EmailMessage
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error, pooling
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Database connection pool and error state variables
connection_pool = None
db_error = None

# Course specifics mapping
COURSES_INFO = {
    'Computer Science': {
        'fee': '$12,000',
        'start_date': 'September 1, 2026',
        'end_date': 'May 20, 2027',
        'dept': 'CSE'
    },
    'Cyber Security': {
        'fee': '$14,500',
        'start_date': 'September 10, 2026',
        'end_date': 'June 5, 2027',
        'dept': 'CSE Cyber Security'
    },
    'Artificial Intelligence': {
        'fee': '$16,000',
        'start_date': 'September 15, 2026',
        'end_date': 'June 15, 2027',
        'dept': 'AI & ML'
    }
}

def init_db_pool():
    """Import values from Config and establish MySQL thread pool connection."""
    global connection_pool, db_error
    try:
        db_config = {
            'host': app.config['MYSQL_HOST'],
            'user': app.config['MYSQL_USER'],
            'password': app.config['MYSQL_PASSWORD'],
            'port': app.config['MYSQL_PORT'],
            'database': app.config['MYSQL_DB']
        }
        
        # Initialize pool
        connection_pool = mysql.connector.pooling.MySQLConnectionPool(
            pool_name=app.config['MYSQL_POOL_NAME'],
            pool_size=app.config['MYSQL_POOL_SIZE'],
            pool_reset_session=True,
            **db_config
        )
        db_error = None
        app.logger.info("Successfully established MySQL connection pool.")
    except mysql.connector.Error as err:
        # Code 1049: Unknown database (means target DB needs creation)
        if err.errno == 1049:
            app.logger.warning("Database not found. Attempting to create database and setup schema...")
            try:
                temp_conn = mysql.connector.connect(
                    host=app.config['MYSQL_HOST'],
                    user=app.config['MYSQL_USER'],
                    password=app.config['MYSQL_PASSWORD'],
                    port=app.config['MYSQL_PORT']
                )
                cursor = temp_conn.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {app.config['MYSQL_DB']}")
                cursor.close()
                temp_conn.close()
                
                # Try setting up the pool again
                connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                    pool_name=app.config['MYSQL_POOL_NAME'],
                    pool_size=app.config['MYSQL_POOL_SIZE'],
                    pool_reset_session=True,
                    host=app.config['MYSQL_HOST'],
                    user=app.config['MYSQL_USER'],
                    password=app.config['MYSQL_PASSWORD'],
                    port=app.config['MYSQL_PORT'],
                    database=app.config['MYSQL_DB']
                )
                db_error = None
                app.logger.info("Database spawned successfully and connection pool initialized.")
            except Exception as inner_err:
                db_error = f"Database creation failed: {str(inner_err)}"
                app.logger.error(f"DB Creation failure: {db_error}")
        else:
            db_error = f"Connection failed: {str(err)}"
            app.logger.error(f"MySQL connection error: {db_error}")

def check_and_setup_tables():
    """Ensure student database table exists. Execute schema.sql and seed dynamic admin if missing."""
    global db_error
    if connection_pool is None:
        return
    
    conn = None
    cursor = None
    try:
        conn = connection_pool.get_connection()
        cursor = conn.cursor()
        
        # Check if required tables exist
        cursor.execute("SHOW TABLES")
        existing_tables = [row[0].lower() for row in cursor.fetchall()]
        
        if 'students' not in existing_tables or 'users' not in existing_tables:
            app.logger.info("Tables not found. Populating schema.sql...")
            schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    sql_script = f.read()
                
                # Filter out comments and split script by semicolons for clean execution
                sql_clean = re.sub(r'--.*?\n', '\n', sql_script)
                statements = [s.strip() for s in sql_clean.split(';') if s.strip()]
                
                for stmt in statements:
                    if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE"):
                        continue
                    cursor.execute(stmt)
                conn.commit()
                app.logger.info("Successfully executed schema.sql table layout.")
        
        # Seed default admin account if not exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            app.logger.info("Seeding default 'admin' supervisor account...")
            pw_hash = generate_password_hash("admin123")
            cursor.execute(
                "INSERT INTO users (username, email, phone, password_hash, email_verified) VALUES (%s, %s, %s, %s, 1)",
                ('admin', 'admin@edumanager.edu', '0000000000', pw_hash)
            )
            conn.commit()
            app.logger.info("Default admin seed successful.")
            
    except Exception as err:
        db_error = f"Table setup failed: {str(err)}"
        app.logger.error(f"Table Init Error: {db_error}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_db_connection():
    """Acquire thread-safe connection from pool."""
    if connection_pool is None:
        raise mysql.connector.Error("Connection pool is not initialized.")
    return connection_pool.get_connection()

# Decorator to verify db status before executing route logic
def db_connection_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        global db_error, connection_pool
        
        if connection_pool is None:
            init_db_pool()
            if connection_pool is not None:
                check_and_setup_tables()
        
        if db_error is not None:
            error_configs = {
                'host': app.config['MYSQL_HOST'],
                'port': app.config['MYSQL_PORT'],
                'user': app.config['MYSQL_USER']
            }
            return render_template('db_error.html', error_message=db_error, error_configs=error_configs), 503
        
        try:
            return f(*args, **kwargs)
        except mysql.connector.Error as err:
            db_error = str(err)
            error_configs = {
                'host': app.config['MYSQL_HOST'],
                'port': app.config['MYSQL_PORT'],
                'user': app.config['MYSQL_USER']
            }
            return render_template('db_error.html', error_message=db_error, error_configs=error_configs), 503
    return decorated_function

# Decorator to lock routes under active session login authorization
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Authorization Required: Please log in to manage records.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Email Dispatch Function
def send_email(subject, recipient, body_text):
    """Send a plain-text email using configured SMTP settings."""
    sender = app.config['SMTP_SENDER']
    smtp_server = app.config['SMTP_SERVER']
    smtp_port = app.config['SMTP_PORT']
    smtp_user = app.config['SMTP_USER']
    smtp_password = app.config['SMTP_PASSWORD']
    smtp_use_tls = app.config['SMTP_USE_TLS']

    if not smtp_user or not smtp_password:
        app.logger.warning("SMTP_USER and SMTP_PASSWORD are required before enrollment emails can be sent.")
        return False, "SMTP credentials are missing. Add SMTP_USER and SMTP_PASSWORD."

    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = recipient
        msg.set_content(body_text)

        with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
            if smtp_use_tls:
                server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        app.logger.info(f"Email successfully delivered to {recipient}")
        return True, "Email sent successfully."
    except Exception as e:
        err_msg = str(e)
        app.logger.error(f"SMTP Server Handshake Failed: {err_msg}")
        return False, f"SMTP Connection Issue: {err_msg}"

def build_enrollment_email(full_name, course, department):
    details = COURSES_INFO.get(course, {
        'fee': '$10,000',
        'start_date': 'TBD',
        'end_date': 'TBD',
        'dept': department
    })
    duration = f"{details['start_date']} to {details['end_date']}"
    subject = f"Successfully enrolled in {course} - EduManager PRO"
    body = (
        f"Dear {full_name},\n\n"
        f"Congratulations! You have been successfully enrolled in {course}.\n\n"
        f"Enrollment details:\n"
        f"Course: {course}\n"
        f"Department: {details['dept']}\n"
        f"Course fee: {details['fee']}\n"
        f"Course duration: {duration}\n\n"
        f"Please keep this email for your records. The administration office will contact you if any additional documents are required.\n\n"
        f"Best regards,\n"
        f"EduManager PRO Admissions"
    )
    return subject, body, details, duration

# Core Email Pattern Check
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')

# Route: Landing Cover Screen
@app.route('/')
@db_connection_required
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('cover.html')

# Route: Login Screen
@app.route('/login', methods=['GET', 'POST'])
@db_connection_required
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            flash("Both fields are required.", "danger")
            return render_template('login.html')
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            
            if user:
                # Password hash verification
                if check_password_hash(user['password_hash'], password):
                    # Establish User Logged session
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['email'] = user['email']
                    
                    flash(f"Welcome back, {user['username']}! Signed in successfully.", "success")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Incorrect password credentials entered.", "danger")
            else:
                flash("Admin Username not found. Register a new supervisor account below.", "danger")
        finally:
            cursor.close()
            conn.close()
            
    return render_template('login.html')

# Route: Register Admin
@app.route('/signup', methods=['GET', 'POST'])
@db_connection_required
def signup():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    user_data = {}
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        user_data = {'username': username, 'email': email, 'phone': phone}
        
        # Validation checks
        errors = []
        if not username or len(username) < 4: errors.append("Username must be at least 4 characters long.")
        if not email or not EMAIL_REGEX.match(email): errors.append("A valid email address is required.")
        if not phone: errors.append("Phone number is required.")
        if not password or len(password) < 6: errors.append("Password must be at least 6 characters long.")
        if password != confirm_password: errors.append("Passwords do not match.")
        
        if errors:
            flash(" & ".join(errors), "danger")
            return render_template('signup.html', user=user_data)
            
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Check unique parameters
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                flash("Validation Error: Username or Email is already registered.", "danger")
                return render_template('signup.html', user=user_data)
            
            pw_hash = generate_password_hash(password)
            
            # Write verified user directly
            cursor.execute(
                "INSERT INTO users (username, email, phone, password_hash, email_verified) VALUES (%s, %s, %s, %s, 1)",
                (username, email, phone, pw_hash)
            )
            conn.commit()
            
            flash(f"Success: Account '{username}' registered! You can now log in.", "success")
            return redirect(url_for('login'))
        finally:
            cursor.close()
            conn.close()
            
    return render_template('signup.html', user=user_data)

# Route: Create Admin From Admin Panel
@app.route('/admin/users/add', methods=['GET', 'POST'])
@db_connection_required
@login_required
def add_admin_user():
    user_data = {}
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        user_data = {'username': username, 'email': email, 'phone': phone}
        errors = []
        if not username or len(username) < 4: errors.append("Username must be at least 4 characters long.")
        if not email or not EMAIL_REGEX.match(email): errors.append("A valid email address is required.")
        if not phone: errors.append("Phone number is required.")
        if not password or len(password) < 6: errors.append("Password must be at least 6 characters long.")
        if password != confirm_password: errors.append("Passwords do not match.")

        if errors:
            flash(" & ".join(errors), "danger")
            return render_template('admin_add_user.html', user=user_data)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                flash("Validation Error: Username or Email is already registered.", "danger")
                return render_template('admin_add_user.html', user=user_data)

            pw_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO users (username, email, phone, password_hash, email_verified) VALUES (%s, %s, %s, %s, 1)",
                (username, email, phone, pw_hash)
            )
            conn.commit()

            flash(f"Admin account '{username}' created successfully.", "success")
            return redirect(url_for('admin'))
        finally:
            cursor.close()
            conn.close()

    return render_template('admin_add_user.html', user=user_data)

# Route: Secured System Dashboard
@app.route('/dashboard')
@db_connection_required
@login_required
def dashboard():
    return render_template('dashboard.html')

# Route: Admin Overview
@app.route('/admin')
@db_connection_required
@login_required
def admin():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total_students FROM students")
        total_students = cursor.fetchone()['total_students']

        cursor.execute("SELECT COUNT(*) AS total_admins FROM users")
        total_admins = cursor.fetchone()['total_admins']

        cursor.execute("SELECT COUNT(DISTINCT course) AS total_courses FROM students")
        total_courses = cursor.fetchone()['total_courses']

        cursor.execute("""
            SELECT course, COUNT(*) AS total
            FROM students
            GROUP BY course
            ORDER BY total DESC, course ASC
        """)
        course_counts = cursor.fetchall()

        cursor.execute("""
            SELECT id, full_name, email, course, department, created_at
            FROM students
            ORDER BY created_at DESC, id DESC
            LIMIT 8
        """)
        recent_students = cursor.fetchall()

        cursor.execute("""
            SELECT id, username, email, phone, created_at
            FROM users
            ORDER BY created_at DESC, id DESC
        """)
        admin_users = cursor.fetchall()

        stats = {
            'total_students': total_students,
            'total_admins': total_admins,
            'total_courses': total_courses
        }
        return render_template(
            'admin.html',
            stats=stats,
            course_counts=course_counts,
            recent_students=recent_students,
            admin_users=admin_users
        )
    finally:
        cursor.close()
        conn.close()

# Route: Secured System About
@app.route('/about')
@db_connection_required
@login_required
def about():
    return render_template('about.html')

# Route: Registered Students List (Original Index CRUD)
@app.route('/students')
@db_connection_required
@login_required
def students():
    query = request.args.get('q', '').strip()
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        if query:
            search_param = f"%{query}%"
            sql = """
                SELECT * FROM students 
                WHERE full_name LIKE %s 
                   OR email LIKE %s 
                   OR course LIKE %s 
                   OR department LIKE %s
                ORDER BY id DESC
            """
            cursor.execute(sql, (search_param, search_param, search_param, search_param))
        else:
            cursor.execute("SELECT * FROM students ORDER BY id DESC")
        
        students_list = cursor.fetchall()
        return render_template('index.html', students=students_list, query=query)
    finally:
        cursor.close()
        conn.close()

# Route: Enroll Student
@app.route('/students/add', methods=['GET', 'POST'])
@db_connection_required
@login_required
def add_student():
    student_data = {}
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        course = request.form.get('course', '').strip()
        department = request.form.get('department', '').strip()
        
        student_data = {
            'full_name': full_name,
            'email': email,
            'phone': phone,
            'course': course,
            'department': department
        }
        
        # Validation checks
        errors = []
        if not full_name: errors.append("Full Name is required.")
        if not email: errors.append("Email is required.")
        elif not EMAIL_REGEX.match(email): errors.append("Invalid email address format.")
        if not phone: errors.append("Phone number is required.")
        if not course: errors.append("Course Selection is required.")
        if not department: errors.append("Department Selection is required.")
        
        if errors:
            flash(" & ".join(errors), "danger")
            return render_template('add_student.html', student=student_data)
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            # Check duplicate email
            cursor.execute("SELECT id FROM students WHERE email = %s", (email,))
            if cursor.fetchone():
                flash(f"Validation Error: A student with email '{email}' already exists.", "danger")
                return render_template('add_student.html', student=student_data)
            
            # Insert student
            sql = "INSERT INTO students (full_name, email, phone, course, department) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (full_name, email, phone, course, department))
            conn.commit()
            
            mail_subject, mail_body, details, duration = build_enrollment_email(full_name, course, department)
            sent, info_str = send_email(mail_subject, email, mail_body)
            
            if sent:
                flash(f"Success: Student {full_name} enrolled! Email sent with course fee {details['fee']} and duration {duration}.", "success")
            else:
                flash(f"Student {full_name} enrolled, but the email was not sent: {info_str}", "warning")
                
            return redirect(url_for('students'))
        finally:
            cursor.close()
            conn.close()
            
    return render_template('add_student.html', student=student_data)

# Route: Modify Student Profile
@app.route('/students/edit/<int:id>', methods=['GET', 'POST'])
@db_connection_required
@login_required
def edit_student(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM students WHERE id = %s", (id,))
        student = cursor.fetchone()
        if not student:
            flash(f"Error: Student record #{id} was not found.", "warning")
            return redirect(url_for('students'))
            
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            course = request.form.get('course', '').strip()
            department = request.form.get('department', '').strip()
            
            updated_student = {
                'id': id,
                'full_name': full_name,
                'email': email,
                'phone': phone,
                'course': course,
                'department': department
            }
            
            # Validation
            errors = []
            if not full_name: errors.append("Full name is required.")
            if not email: errors.append("Email is required.")
            elif not EMAIL_REGEX.match(email): errors.append("Invalid email address format.")
            if not phone: errors.append("Phone number is required.")
            if not course: errors.append("Course Selection is required.")
            if not department: errors.append("Department Selection is required.")
            
            if errors:
                flash(" & ".join(errors), "danger")
                return render_template('edit_student.html', student=updated_student)
            
            # Check duplicate email excludes self
            cursor.execute("SELECT id FROM students WHERE email = %s AND id != %s", (email, id))
            if cursor.fetchone():
                flash(f"Validation Error: Another student is already registered with email '{email}'.", "danger")
                return render_template('edit_student.html', student=updated_student)
            
            # Execute Parameterized Update
            sql = "UPDATE students SET full_name = %s, email = %s, phone = %s, course = %s, department = %s WHERE id = %s"
            cursor.execute(sql, (full_name, email, phone, course, department, id))
            conn.commit()
            
            flash(f"Success: Student record #{id} updated successfully.", "success")
            return redirect(url_for('students'))
            
        return render_template('edit_student.html', student=student)
    finally:
        cursor.close()
        conn.close()

# Route: Remove Student File
@app.route('/students/delete/<int:id>', methods=['POST'])
@db_connection_required
@login_required
def delete_student(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT full_name FROM students WHERE id = %s", (id,))
        student = cursor.fetchone()
        
        if student:
            name = student['full_name']
            cursor.execute("DELETE FROM students WHERE id = %s", (id,))
            conn.commit()
            flash(f"Success: Student '{name}' has been successfully deleted from the registry.", "success")
        else:
            flash("Error: Student record not found.", "danger")
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('students'))

# Route: Clear User Session
@app.route('/logout')
@db_connection_required
def logout():
    session.clear()
    flash("Supervisor Session cleared. Logged out successfully.", "success")
    return redirect(url_for('index'))

# Server startup (optimized for AWS EC2 deploy binds to 0.0.0.0:5000)
if __name__ == '__main__':
    init_db_pool()
    if connection_pool is not None:
        check_and_setup_tables()
        
    app.run(host='0.0.0.0', port=5000, debug=True)

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import os
import bcrypt

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database connection
DB_PATH = '/app/db/members_data.db'  # Adjust based on your setup

def connect_db():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username, is_admin):
        self.id = id
        self.username = username
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, password, is_admin FROM Users WHERE id = ?", (user_id,))
    user_data = cur.fetchone()
    conn.close()

    if user_data:
        return User(user_data[0], user_data[1], bool(user_data[3]))
    return None

# Setup database and create tables if necessary
@app.before_request
def setup_db():
    init_db()

def init_db():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT NOT NULL,
            username TEXT NOT NULL,
            rank TEXT NOT NULL CHECK (rank IN ('R1', 'R2', 'R3', 'R4', 'R5')),
            furnace_level_start INTEGER NOT NULL,
            furnace_level_current INTEGER NOT NULL,
            power_start INTEGER NOT NULL,
            power_current INTEGER NOT NULL
        )
    """)
    # Ensure an admin user exists
    cur.execute("SELECT * FROM Users WHERE username = 'admin'")
    if not cur.fetchone():
        hashed_password = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt())
        cur.execute("INSERT INTO Users (username, password, is_admin) VALUES (?, ?, ?)", 
                    ('admin', hashed_password.decode('utf-8'), 1))
    conn.commit()
    conn.close()

# Home route - display all members
@app.route("/")
def index():
    conn = connect_db()
    if conn is None:
        return "Failed to connect to the database", 500
    cur = conn.cursor()
    cur.execute("SELECT member_id, username, rank, furnace_level_current, power_current FROM Members ORDER BY rank DESC, power_current DESC")
    members = cur.fetchall()
    total_power = sum([int(member[4]) for member in members])
    return render_template("index.html", members=members, total_power=total_power)

# Admin panel (protected route)
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash("You do not have access to this page", "error")
        return redirect(url_for('index'))

    # Admin-specific functionality
    return render_template('admin.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password, is_admin FROM Users WHERE username = ?", (username,))
        user_data = cur.fetchone()

        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[2].encode('utf-8')):
            user = User(user_data[0], user_data[1], bool(user_data[3]))
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password", "error")
            return redirect(url_for('login'))

    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Add new member form (only accessible to logged-in users)
@app.route('/add_member_form')
@login_required
def add_member_form():
    if not current_user.is_admin:
        flash("You do not have access to this page", "error")
        return redirect(url_for('index'))

    return render_template('add.html')

# Add new member (only accessible to logged-in users)
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_member():
    if not current_user.is_admin:
        flash("You do not have access to this page", "error")
        return redirect(url_for('index'))

    member_id = request.form['member_id']
    username = request.form['username']
    rank = request.form['rank']
    furnace_level = int(request.form['furnace_level'])
    power_level = int(request.form['power_level'])

    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Members (member_id, username, rank, furnace_level_start, furnace_level_current, power_start, power_current)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (member_id, username, rank, furnace_level, furnace_level, power_level, power_level))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

# Update member details (admin only)
@app.route('/update/<int:member_id>', methods=['POST'])
@login_required
def update_member(member_id):
    if not current_user.is_admin:
        flash("You do not have access to this page", "error")
        return redirect(url_for('index'))

    furnace_level = request.form['furnace_level']
    power_level = request.form['power_level']
    rank = request.form['rank']

    conn = connect_db()
    conn.execute('UPDATE Members SET furnace_level_current = ?, power_current = ?, rank = ? WHERE id = ?',
                 (furnace_level, power_level, rank, member_id))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

# Delete member (admin only)
@app.route('/delete/<int:member_id>', methods=['POST'])
@login_required
def delete_member(member_id):
    if not current_user.is_admin:
        flash("You do not have access to this page", "error")
        return redirect(url_for('index'))

    conn = connect_db()
    conn.execute('DELETE FROM Members WHERE id = ?', (member_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

# Show top 5 members by power and top 5 members with the biggest changes
@app.route('/top_stats')
@login_required
def top_stats():
    conn = connect_db()
    cur = conn.cursor()

    # Top 5 highest power
    cur.execute("SELECT username, power_current FROM Members ORDER BY power_current DESC LIMIT 5")
    top_powers = cur.fetchall()

    # Top 5 biggest power changes
    cur.execute("""
        SELECT username, (power_current - power_start) AS power_change
        FROM Members ORDER BY power_change DESC LIMIT 5
    """)
    biggest_power_changes = cur.fetchall()

    # Top 5 lowest power
    cur.execute("SELECT username, power_current FROM Members ORDER BY power_current ASC LIMIT 5")
    lowest_powers = cur.fetchall()

    # Top 5 smallest changes in power
    cur.execute("""
        SELECT username, (power_current - power_start) AS power_change
        FROM Members ORDER BY power_change ASC LIMIT 5
    """)
    smallest_power_changes = cur.fetchall()

    return render_template("top_stats.html",
                           top_powers=top_powers,
                           biggest_power_changes=biggest_power_changes,
                           lowest_powers=lowest_powers,
                           smallest_power_changes=smallest_power_changes)
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file:
            # Read the CSV file and decode it
            data = file.read().decode("utf-8-sig").splitlines()  # Removes any hidden BOM
            
            conn = connect_db()
            cur = conn.cursor()
            
            for line in data:
                # Assume CSV format: member_id, username, rank, furnace_level, power_level
                member_id, username, rank, furnace_level, power_level = [x.strip() for x in line.split(',')]
                
                # Insert or update existing records using ON CONFLICT
                cur.execute("""
                    INSERT INTO Members (member_id, username, rank, furnace_level_start, furnace_level_current, power_start, power_current)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(member_id) DO UPDATE SET
                        username=excluded.username, 
                        rank=excluded.rank, 
                        furnace_level_current=excluded.furnace_level_current, 
                        power_current=excluded.power_current
                """, (member_id, username, rank, furnace_level, furnace_level, power_level, power_level))
            
            conn.commit()
            conn.close()
            flash('File uploaded and processed successfully!', 'success')
            return redirect(url_for('index'))

    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

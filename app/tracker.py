from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import os
import bcrypt

app = Flask(__name__)
app.secret_key = os.urandom(24)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Path to the database
DB_PATH = '/app/db/members_data.db'

def connect_db():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

def init_db():
    conn = connect_db()
    cur = conn.cursor()
    
    # Create Members table if it doesn't exist
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

    # Create Users table if it doesn't exist
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0 -- 1 means admin, 0 means regular user
        )
    """)

    # Check if an admin user exists, if not, create one
    cur.execute("SELECT * FROM Users WHERE username = 'admin'")
    if cur.fetchone() is None:
        # Hash the default password
        hashed_password = bcrypt.hashpw(b"adminpass", bcrypt.gensalt()).decode('utf-8')
        cur.execute("INSERT INTO Users (username, password, is_admin) VALUES (?, ?, ?)", ('admin', hashed_password, 1))
        print("Default admin user created with username 'admin' and password 'adminpass'")
    
    conn.commit()
    conn.close()

@app.before_request
def setup_db():
    init_db()

@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, is_admin FROM Users WHERE id = ?", (user_id,))
    user_data = cur.fetchone()
    conn.close()

    if user_data:
        return User(user_data[0], user_data[1], bool(user_data[2]))
    return None

class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

# Home page - Display all members
@app.route("/")
def index():
    conn = connect_db()
    if conn is None:
        return "Failed to connect to the database", 500
    cur = conn.cursor()

    # Fetch members sorted by rank and then by power
    cur.execute("SELECT id, member_id, username, rank, furnace_level_current, power_current FROM Members ORDER BY rank DESC, power_current DESC")
    members = cur.fetchall()

    # Sum the power values from the 'power_current' column
    total_power = sum([int(member[5]) for member in members])

    return render_template("index.html", members=members, total_power=total_power)

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
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Admin panel
@app.route('/admin_panel')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash("You don't have permission to access the admin panel", "error")
        return redirect(url_for('index'))

    return render_template('admin_panel.html')

# Create new user (accessible only by admin)
@app.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        flash("You don't have permission to create users", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = connect_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO Users (username, password, is_admin) VALUES (?, ?, ?)", (username, hashed_password, 0))
        conn.commit()
        conn.close()

        flash("User created successfully", "success")
        return redirect(url_for('admin_panel'))
    return render_template('create_user.html')

# Update member power and furnace level
@app.route('/update/<int:member_id>', methods=['POST'])
@login_required
def update_member(member_id):
    if not current_user.is_admin:
        flash("You don't have permission to update members", "error")
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

# Delete member
@app.route('/delete/<int:member_id>', methods=['POST'])
@login_required
def delete_member(member_id):
    if not current_user.is_admin:
        flash("You don't have permission to delete members", "error")
        return redirect(url_for('index'))

    conn = connect_db()
    conn.execute('DELETE FROM Members WHERE id = ?', (member_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Show top 5 members by power and top 5 members with biggest changes
@app.route('/top_stats')
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

    return render_template("top_stats.html",
                           top_powers=top_powers,
                           biggest_power_changes=biggest_power_changes)

# Upload CSV for bulk addition or update of members
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if not current_user.is_admin:
        flash("You don't have permission to upload files", "error")
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file:
            data = file.read().decode("utf-8-sig").splitlines()  # Remove BOM here with utf-8-sig
            conn = connect_db()
            cur = conn.cursor()

            for line in data:
                member_id, username, rank, furnace_level, power_level = [x.strip() for x in line.split(',')]

                cur.execute("""
                    INSERT OR REPLACE INTO Members (member_id, username, rank, furnace_level_start, furnace_level_current, power_start, power_current)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (member_id, username, rank, furnace_level, furnace_level, power_level, power_level))

            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

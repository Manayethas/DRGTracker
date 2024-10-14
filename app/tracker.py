from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# In-memory user storage for simplicity
# Username: admin, Password: password
users = {"admin": {"password": "password"}}

class User(UserMixin):
    def __init__(self, username):
        self.id = username

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None

# Path to the database
DB_PATH = '/app/db/members_data.db'

# Database connection
def connect_db():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

# Initialize the database
def init_db():
    conn = connect_db()
    cur = conn.cursor()
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
    conn.commit()
    conn.close()

# Set up the database before each request
@app.before_request
def setup_db():
    init_db()

# Home page - Display all members
@app.route("/")
def index():
    conn = connect_db()
    if conn is None:
        return "Failed to connect to the database", 500
    cur = conn.cursor()

    # Fetch members sorted by rank and power
    cur.execute("SELECT member_id, username, rank, furnace_level_current, power_current FROM Members ORDER BY rank DESC, power_current DESC")
    members = cur.fetchall()

    # Sum the power values from the 'power_current' column
    total_power = sum([int(member[4]) for member in members])

    # Pass the correct information to the template
    return render_template("index.html", members=members, total_power=total_power)

# Add new member
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_member():
    if request.method == 'POST':
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
    else:
        return render_template('add.html')

# Update member power and furnace level
@app.route('/update/<int:member_id>', methods=['POST'])
@login_required
def update_member(member_id):
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
    conn = connect_db()
    conn.execute('DELETE FROM Members WHERE id = ?', (member_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Show top 5 members by power and top 5 with the biggest changes
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

# Upload CSV for bulk addition of members
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file:
            data = file.read().decode("utf-8-sig").splitlines()
            conn = connect_db()
            cur = conn.cursor()

            for line in data:
                member_id, username, rank, furnace_level, power_level = [x.strip() for x in line.split(',')]
                cur.execute("""
                    INSERT INTO Members (member_id, username, rank, furnace_level_start, furnace_level_current, power_start, power_current)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (member_id, username, rank, furnace_level, furnace_level, power_level, power_level))

            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('upload.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials')
            return redirect(url_for('login'))
    return render_template('login.html')

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Handle method not allowed errors
@app.errorhandler(405)
def method_not_allowed(e):
    return "Method Not Allowed: {}".format(request.url), 405

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

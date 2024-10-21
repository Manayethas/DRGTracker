from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import os
import bcrypt
from datetime import timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)  # Set session timeout

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to login page if not logged in

# Ensure that session is permanent for every request
@app.before_request
def make_session_permanent():
    session.permanent = True

# Dummy user class for login
class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = id
        self.username = username
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT id, username, is_admin FROM Users WHERE id = ?", (user_id,))
    user_data = cur.fetchone()
    conn.close()

    if user_data:
        return User(user_data[0], user_data[1], user_data[2])
    return None

# Home page - Display all members
@app.route("/")
def index():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT member_id, username, rank, furnace_level_current, power_current FROM Members ORDER BY rank DESC, power_current DESC")
    members = cur.fetchall()

    total_power = sum([int(member[4]) for member in members])

    return render_template("index.html", members=members, total_power=total_power, current_user=current_user)

# Admin panel
@app.route("/admin")
@login_required
def admin_panel():
    if not current_user.is_admin:
        return redirect(url_for('index'))

    return render_template("admin_panel.html")

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
            return redirect(url_for('admin_panel'))
        else:
            flash("Invalid username or password", "error")
    return render_template('login.html')

# Ensure the route for admin panel is decorated with login_required
@app.route('/admin')
@login_required
def admin_panel():
    return render_template("admin_panel.html")

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Add new member form
@app.route('/add_member_form')
@login_required
def add_member_form():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    return render_template('add.html')

# Route to create a new user (Admin only)
@app.route('/create_user', methods=['GET', 'POST'])
@login_required
def create_user():
    if not current_user.is_admin:
        flash('You do not have access to this page.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        is_admin = request.form.get('is_admin', False)

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = connect_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO Users (username, password, is_admin) VALUES (?, ?, ?)",
                    (username, hashed_password.decode('utf-8'), is_admin))
        conn.commit()
        conn.close()

        flash('New user created successfully!', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('create_user.html')
    
# Add new member
@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_member():
    if request.method == 'POST':
        if not current_user.is_admin:
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

        flash('Member added successfully', 'success')
        return redirect(url_for('admin_panel'))
    else:
        return render_template('add.html')

# Update member
@app.route('/update/<int:member_id>', methods=['POST'])
@login_required
def update_member(member_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))

    furnace_level = request.form['furnace_level']
    power_level = request.form['power_level']
    rank = request.form['rank']

    conn = connect_db()
    conn.execute('UPDATE Members SET furnace_level_current = ?, power_current = ?, rank = ? WHERE id = ?',
                 (furnace_level, power_level, rank, member_id))
    conn.commit()
    conn.close()

    flash('Member updated successfully', 'success')
    return redirect(url_for('admin_panel'))

# Delete member
@app.route('/delete/<int:member_id>', methods=['POST'])
@login_required
def delete_member(member_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))

    conn = connect_db()
    conn.execute('DELETE FROM Members WHERE id = ?', (member_id,))
    conn.commit()
    conn.close()

    flash('Member deleted successfully', 'success')
    return redirect(url_for('admin_panel'))

# Upload CSV for bulk addition or update of members
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(url_for('admin_panel'))

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(url_for('admin_panel'))

        if file and file.filename.endswith('.csv'):
            try:
                # Read CSV file content and process it
                data = file.read().decode("utf-8-sig").splitlines()  # Handle BOM if present
                conn = connect_db()
                cur = conn.cursor()

                # Loop through each line in the CSV and insert or update records
                for line in data:
                    try:
                        member_id, username, rank, furnace_level, power_level = [x.strip() for x in line.split(',')]
                        cur.execute("""
                            INSERT INTO Members (member_id, username, rank, furnace_level_start, furnace_level_current, power_start, power_current)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(member_id) DO UPDATE SET
                            username=excluded.username, rank=excluded.rank, furnace_level_current=excluded.furnace_level_current, power_current=excluded.power_current
                        """, (member_id, username, rank, furnace_level, furnace_level, power_level, power_level))
                    except Exception as e:
                        print(f"Error processing line {line}: {e}")
                        continue

                conn.commit()
                conn.close()
                flash("CSV file processed successfully.")
            except Exception as e:
                flash(f"An error occurred while processing the CSV: {e}")
                return redirect(url_for('admin_panel'))

        else:
            flash('File type not allowed, only CSV is accepted.')
            return redirect(url_for('admin_panel'))

    return render_template('upload.html')
    
# Top Stats page
@app.route("/top_stats")
def top_stats():
    conn = connect_db()
    cur = conn.cursor()

    # Top 5 members with the highest power
    cur.execute("SELECT username, power_current FROM Members ORDER BY power_current DESC LIMIT 5")
    top_powers = cur.fetchall()

    # Bottom 5 members with the lowest power
    cur.execute("SELECT username, power_current FROM Members ORDER BY power_current ASC LIMIT 5")
    lowest_powers = cur.fetchall()

    # Top 5 biggest power changes
    cur.execute("""
        SELECT username, (power_current - power_start) AS power_change
        FROM Members ORDER BY power_change DESC LIMIT 5
    """)
    biggest_changes = cur.fetchall()

    # Top 5 smallest power changes
    cur.execute("""
        SELECT username, (power_current - power_start) AS power_change
        FROM Members ORDER BY power_change ASC LIMIT 5
    """)
    smallest_changes = cur.fetchall()

    return render_template("top_stats.html",
                           top_powers=top_powers,
                           lowest_powers=lowest_powers,
                           biggest_changes=biggest_changes,
                           smallest_changes=smallest_changes)

# Error handler for unauthorized access
@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

# Error handler for 404 not found
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Run the app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

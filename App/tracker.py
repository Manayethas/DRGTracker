from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import matplotlib.pyplot as plt
import io
import os
import csv
from werkzeug.utils import secure_filename
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')  # Change as needed
app.config['UPLOAD_FOLDER'] = 'uploads'  # Ensure this folder exists

# Path to the database inside the Docker container or local system
DB_PATH = '/app/db/members_data.db'

def connect_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        return None

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
            power_start INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.got_first_request
def setup_db():
    init_db()

# Home page - Display all members
@app.route("/")
def index():
    conn = connect_db()
    if conn is None:
        return "Failed to connect to the database", 500
    cur = conn.cursor()
    cur.execute("SELECT * FROM Members")
    members = cur.fetchall()

    total_power = sum([member[5] for member in members])

    return render_template("index.html", members=members, total_power=total_power)

# Add new member
@app.route('/add', methods=['GET', 'POST'])
def add_member():
    if request.method == 'POST':
        member_id = request.form['member_id']
        username = request.form['username']
        rank = request.form['rank']
        furnace_level = int(request.form['furnace_level'])
        power_level = int(request.form['power_level'])

        conn = connect_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO Members (member_id, username, rank, furnace_level_start, power_start) VALUES (?, ?, ?, ?, ?)",
                    (member_id, username, rank, furnace_level, power_level))
        conn.commit()
        conn.close()

        return redirect(url_for('index'))
    return render_template("add.html")

# Update member power and furnace level
@app.route('/update/<int:member_id>', methods=['POST'])
def update_member(member_id):
    furnace_level = int(request.form['furnace_level'])
    power_level = int(request.form['power_level'])

    conn = connect_db()
    cur = conn.cursor()
    cur.execute("UPDATE Members SET furnace_level_start = ?, power_start = ? WHERE id = ?",
                (furnace_level, power_level, member_id))
    conn.commit()
    conn.close()

    return redirect(url_for('index'))

# Delete member
@app.route('/delete/<int:member_id>', methods=['POST'])
def delete_member(member_id):
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM Members WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

# Export the graph and member list as JPEG or PNG
@app.route('/export_graph')
def export_graph():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT username, power_start FROM Members ORDER BY power_start DESC")
    members = cur.fetchall()

    usernames = [member[0] for member in members]
    powers = [member[1] for member in members]

    fig, ax = plt.subplots()
    ax.barh(usernames, powers, color='blue')
    ax.set_xlabel('Power')
    ax.set_ylabel('Username')
    ax.set_title('Alliance Power Chart')

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return output.getvalue(), 200, {'Content-Type': 'image/png'}

# Show top 5 members by power and top 5 members with biggest changes
@app.route('/top_stats')
def top_stats():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT username, power_start FROM Members ORDER BY power_start DESC LIMIT 5")
    top_powers = cur.fetchall()

    cur.execute("""
        SELECT username, (power_start - furnace_level_start) AS power_change
        FROM Members ORDER BY power_change DESC LIMIT 5
    """)
    biggest_changes = cur.fetchall()

    return render_template("top_stats.html", top_powers=top_powers, biggest_changes=biggest_changes)

# Upload CSV for mass data entry
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Process the CSV file
            process_csv(filepath)

            flash('CSV file uploaded and processed successfully!')
            return redirect(url_for('index'))

    return render_template('upload.html')

# Function to process the uploaded CSV
def process_csv(filepath):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()

        with open(filepath, newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip header row
            for row in reader:
                c.execute('''INSERT INTO Members (member_id, username, rank, furnace_level_start, power_start)
                             VALUES (?, ?, ?, ?, ?)''', (row[0], row[1], row[2], row[3], row[4]))

        conn.commit()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

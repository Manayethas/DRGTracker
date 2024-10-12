from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Path to the database
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
            furnace_level_current INTEGER NOT NULL,
            power_start INTEGER NOT NULL,
            power_current INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()

@app.before_first_request
def setup_db():
    init_db()

# Home page - Display all members
@app.route("/")
def index():
    conn = connect_db()
    if conn is None:
        return "Failed to connect to the database", 500
    cur = conn.cursor()
    
    # Fetch members sorted by rank and then by power
    cur.execute("SELECT * FROM Members ORDER BY rank DESC, power_current DESC")
    members = cur.fetchall()

    total_power = sum([member[7] for member in members])

    return render_template("index.html", members=members, total_power=total_power)

# Add new member form
@app.route('/add_member_form')
def add_member_form():
    return render_template('add.html')

# Add new member
@app.route('/add', methods=['POST'])
def add_member():
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

# Update member power and furnace level
@app.route('/update/<int:member_id>', methods=['POST'])
def update_member(member_id):
    new_furnace_level = int(request.form['furnace_level'])
    new_power_level = int(request.form['power_level'])
    new_rank = request.form['rank']

    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT furnace_level_start, power_start, furnace_level_current, power_current 
        FROM Members WHERE id = ?
    """, (member_id,))
    member = cur.fetchone()

    if member:
        furnace_change = new_furnace_level - member[1]
        power_change = new_power_level - member[3]

        cur.execute("""
            UPDATE Members 
            SET furnace_level_current = ?, power_current = ?, rank = ?
            WHERE id = ?
        """, (new_furnace_level, new_power_level, new_rank, member_id))

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

# Upload CSV for bulk addition of members
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file:
        data = file.read().decode("utf-8").splitlines()
        conn = connect_db()
        cur = conn.cursor()

        for line in data:
            member_id, username, rank, furnace_level, power_level = line.split(',')
            cur.execute("""
                INSERT INTO Members (member_id, username, rank, furnace_level_start, furnace_level_current, power_start, power_current) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (member_id, username, rank, furnace_level, furnace_level, power_level, power_level))
        
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

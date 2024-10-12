from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import matplotlib.pyplot as plt
import io
import os
from datetime import datetime
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

app = Flask(__name__)
app.secret_key = os.urandom(24)

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
    cur.execute("SELECT * FROM Members")
    members = cur.fetchall()

    total_power = sum([member[7] for member in members])

    return render_template("index.html", members=members, total_power=total_power)

# Add new member
@app.route('/add_member', methods=['GET', 'POST'])
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
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (member_id, username, rank, furnace_level, furnace_level, power_level, power_level))
        conn.commit()
        conn.close()

        flash('Member added successfully!')
        return redirect(url_for('index'))
    
    return render_template('add.html')

# Update member power and furnace level
@app.route('/update/<int:member_id>', methods=['POST'])
def update_member(member_id):
    furnace_level = int(request.form['furnace_level'])
    power_level = int(request.form['power_level'])
    rank = request.form['rank']

    conn = connect_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE Members
        SET furnace_level_current = ?, power_current = ?, rank = ?
        WHERE id = ?""",
        (furnace_level, power_level, rank, member_id))
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
    cur.execute("SELECT username, power_current FROM Members ORDER BY power_current DESC")
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

# Show top 5 members by power, least changed members, and lowest power
@app.route('/top_stats')
def top_stats():
    conn = connect_db()
    cur = conn.cursor()

    # Top 5 members by highest power
    cur.execute("SELECT username, power_current FROM Members ORDER BY power_current DESC LIMIT 5")
    top_powers = cur.fetchall()

    # Top 5 members with biggest changes in power
    cur.execute("""
        SELECT username, (power_current - power_start) AS power_change
        FROM Members ORDER BY power_change DESC LIMIT 5
    """)
    biggest_power_changes = cur.fetchall()

    # Top 5 members with least changes in power
    cur.execute("""
        SELECT username, (power_current - power_start) AS power_change
        FROM Members ORDER BY power_change ASC LIMIT 5
    """)
    least_power_changes = cur.fetchall()

    # Lowest 5 members by current power
    cur.execute("SELECT username, power_current FROM Members ORDER BY power_current ASC LIMIT 5")
    lowest_powers = cur.fetchall()

    # Top 5 members with least changes in furnace level
    cur.execute("""
        SELECT username, (furnace_level_current - furnace_level_start) AS furnace_change
        FROM Members ORDER BY furnace_change ASC LIMIT 5
    """)
    least_furnace_changes = cur.fetchall()

    conn.close()

    return render_template(
        "top_stats.html",
        top_powers=top_powers,
        biggest_power_changes=biggest_power_changes,
        least_power_changes=least_power_changes,
        lowest_powers=lowest_powers,
        least_furnace_changes=least_furnace_changes
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

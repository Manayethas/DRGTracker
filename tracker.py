from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# Connect to SQLite database
def connect_db():
    conn = sqlite3.connect('members_data.db')
    return conn

# Home page - Display all members
@app.route('/')
def index():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Members")
    members = cur.fetchall()
    conn.close()
    return render_template('index.html', members=members)

# Add new member
@app.route('/add', methods=['POST'])
def add_member():
    member_id = request.form['member_id']
    username = request.form['username']
    rank = request.form['rank']
    furnace_level = request.form['furnace_level']
    power_level = request.form['power_level']

    conn = connect_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO Members (member_id, username, rank, furnace_level_start, power_start) VALUES (?, ?, ?, ?, ?)",
                (member_id, username, rank, furnace_level, power_level))
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

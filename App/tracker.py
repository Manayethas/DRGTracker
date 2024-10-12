import os
import csv
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'csv'}
app.secret_key = 'supersecretkey'

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extension check
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Database initialization
def init_db():
    with sqlite3.connect('member_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            rank TEXT NOT NULL,
            furnace_level INTEGER NOT NULL,
            power REAL NOT NULL
        )
        ''')
        conn.commit()

# Route to display the home page and upload form
@app.route('/')
def index():
    return render_template('upload.html')

# Route to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if the request contains the file part
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']

    # If the user does not select a file
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)
        flash('File successfully uploaded and processed!')
        
        # Process the CSV and insert data into the database
        process_csv(filename)
        return redirect(url_for('index'))
    else:
        flash('Allowed file types are CSV')
        return redirect(request.url)

# Process the CSV file and insert the data into the database
def process_csv(filepath):
    with sqlite3.connect('member_data.db') as conn:
        cursor = conn.cursor()
        
        # Open the CSV file and insert its contents into the database
        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip the header row
            members = []
            for row in reader:
                members.append((row[1], row[2], int(row[3]), float(row[4])))  # Skip id in CSV

            cursor.executemany('''
            INSERT INTO members (username, rank, furnace_level, power)
            VALUES (?, ?, ?, ?)
            ''', members)

        conn.commit()

# Route to display the member list
@app.route('/members')
def list_members():
    with sqlite3.connect('member_data.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM members')
        members = cursor.fetchall()
    
    return render_template('members.html', members=members)

# Start the Flask app
if __name__ == '__main__':
    init_db()  # Ensure the database is initialized
    app.run(debug=True)

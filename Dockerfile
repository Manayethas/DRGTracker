# Use the official Python image as a base
FROM python:3.13-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y sqlite3 libsqlite3-dev && \
    apt-get clean

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Flask runs on
EXPOSE 5000

# Initialize the database (this step will ensure the database exists)
RUN sqlite3 /app/db/members_data.db "CREATE TABLE IF NOT EXISTS Members (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT NOT NULL, username TEXT NOT NULL, rank TEXT NOT NULL, furnace_level_start TEXT NOT NULL, power_start TEXT NOT NULL);"

# Command to run the Flask app with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "tracker:app"]

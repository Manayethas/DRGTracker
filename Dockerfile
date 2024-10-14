# Use a base Python image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy all project files (including the app directory) into the container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 for Flask
EXPOSE 5000

# Use Gunicorn to serve the Flask app
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app.tracker:app"]

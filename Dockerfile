# Use Python 3.9 or newer
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install any necessary dependencies
RUN pip install -r requirements.txt

# Expose the port the app runs on
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.tracker:app"]

# Step 1: Use the official Python 3.13 image as a base image
FROM python:3.13-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the current directory contents into the container
COPY . /app

# Step 4: Install apt-utils to avoid the configuration warning and system dependencies
RUN apt-get update && \
    apt-get install -y apt-utils sqlite3 libsqlite3-dev build-essential gcc && \
    apt-get clean

# Step 5: Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Step 6: Expose the port that Flask will run on
EXPOSE 5000

# Step 7: Run the application using Gunicorn
CMD ["gunicorn", "-w", "4", "tracker:app", "-b", "0.0.0.0:5000"]

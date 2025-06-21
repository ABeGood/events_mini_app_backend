FROM python:3.11-slim

WORKDIR /app

# Copy requirements from backend folder
COPY backend/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only backend code
COPY backend/ .

# Expose port
EXPOSE $PORT

# Run the app (adjust based on your main file)
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
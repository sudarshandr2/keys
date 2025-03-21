
# Use Python 3.11 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client

# Copy requirements from pyproject.toml
COPY pyproject.toml .
COPY main.py .
COPY app.py .
COPY models.py .
COPY auth.py .
COPY admin.py .
COPY reseller.py .
COPY storage.py .
COPY templates/ templates/
COPY static/ static/

# Install dependencies
RUN pip install email-validator flask-login flask flask-sqlalchemy gunicorn psycopg2-binary werkzeug sqlalchemy

# Expose port 5000
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]

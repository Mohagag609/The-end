#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Set environment variables for production
export FLASK_APP=app.py
export FLASK_ENV=production

# Initialize database (create tables)
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully!')
"

echo "Build completed successfully!"
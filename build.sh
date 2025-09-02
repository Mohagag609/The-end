#!/usr/bin/env bash
# Build script for Render deployment

set -o errexit

# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# Install Python dependencies
pip install -r requirements.txt

# Set environment variables for production
export FLASK_APP=app.py
export FLASK_ENV=production

# Initialize database (create tables)
python -c "
import os
os.environ.setdefault('FLASK_APP', 'app.py')
os.environ.setdefault('FLASK_ENV', 'production')

from app import app, db
with app.app_context():
    try:
        db.create_all()
        print('Database tables created successfully!')
    except Exception as e:
        print(f'Warning: Could not create tables - {e}')
        print('Tables may already exist or will be created on first run.')
"

echo "Build completed successfully!"
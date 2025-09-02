#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate --no-input

# Create sample data if database is empty
python manage.py shell << EOF
from projects.models import Project
if not Project.objects.exists():
    print("Creating initial data...")
    exec(open('setup_complete_data.py').read())
EOF

echo "Build completed successfully!"
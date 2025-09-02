#!/usr/bin/env bash

# Kill any existing Django server
pkill -f "python.*runserver"

# Wait a moment
sleep 1

# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate --no-input

# Check if project exists, if not create sample data
python manage.py shell << EOF
from projects.models import Project
if not Project.objects.exists():
    print("Creating sample data...")
    exec(open('setup_complete_data.py').read())
else:
    print("Data already exists")
EOF

# Start the server
echo "Starting server at http://localhost:8000"
python manage.py runserver 0.0.0.0:8000
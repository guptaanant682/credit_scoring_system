#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z "${DATABASE_HOST:-db}" "${DATABASE_PORT:-5432}"; do
  sleep 0.1
done
echo "Database started"

# Wait for redis to be ready
echo "Waiting for Redis..."
while ! nc -z "${REDIS_HOST:-redis}" "${REDIS_PORT:-6379}"; do
  sleep 0.1
done
echo "Redis started"

# Run migrations
echo "Running database migrations..."
python manage.py makemigrations credit_app
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser..."
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("Superuser created successfully")
else:
    print("Superuser already exists")
EOF

# Load initial data from Excel files
echo "Loading initial data from Excel files..."
if [ -f "customer_data.xlsx" ] && [ -f "loan_data.xlsx" ]; then
    python manage.py load_initial_data || echo "Failed to load initial data, but continuing..."
else
    echo "Excel data files not found, skipping data loading"
fi

echo "Starting application..."
exec "$@"
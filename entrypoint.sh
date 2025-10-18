#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Waiting for postgres..."

# Loop until the postgres service is reachable
while ! nc -z $DB_HOST $DB_PORT; do
  sleep 0.1
done

echo "PostgreSQL started"

# Run database migrations
python manage.py migrate

# Execute the command passed to this script
exec "$@"
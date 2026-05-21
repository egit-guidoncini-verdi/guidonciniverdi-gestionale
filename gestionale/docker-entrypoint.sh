#!/bin/sh
set -e

echo "Running database migrations..."
flask db upgrade

echo "Starting gunicorn..."
exec gunicorn -w 3 -b 0.0.0.0 app:app
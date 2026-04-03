#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
sleep 5 

echo "Creating database tables..."
python initial.py

echo "Seeding started rules..."
python rule_seeder.py

echo 'Starting FastAPI server...'
exec uvicorn app:app --host 0.0.0.0 --port 8000
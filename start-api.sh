# this script is used as the entrypoint for the FastAPI server in the Docker container.
# It waits for PostgreSQL to be ready, initializes the database tables, seeds any started rules, and then starts the FastAPI server using uvicorn.

#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
sleep 5 

echo "Creating database tables..."
python initial.py

echo "Seeding started rules..."
python rule_seeder.py

echo 'Starting FastAPI server...'
exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"

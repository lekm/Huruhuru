#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Build script starting..."

echo "Updating package list and installing SQLite dev libraries..."
apt-get update -y && apt-get install -y libsqlite3-dev

# Removed pip install commands - Vercel handles this based on requirements.txt
# echo "Installing dependencies..."
# pip install --upgrade pip
# pip install -r requirements.txt

echo "Running wordlist generation..."
python3 generate_wordlists.py

echo "Initializing database..."
python3 -m flask init-db

echo "Build script finished successfully." 
#!/bin/bash
# Exit immediately if a command exits with a non-zero status.
set -e

echo "Build script starting..."
pip install -r requirements.txt
echo "Dependencies installed."
# Use python3.12 explicitly as we know it works
python3.12 -m flask init-db
echo "Database initialized."
# No need to output anything else, @vercel/python will handle the rest if 'builds' is removed
echo "Build script finished." 
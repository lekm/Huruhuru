#!/bin/bash

# Navigate to the directory where the script is located (optional but good practice)
# cd "$(dirname "$0")"

# Activate virtual environment if you use one (replace 'venv' with your env name)
# source venv/bin/activate

echo "Ensuring dependencies are installed..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "Error installing dependencies. Please check pip3 and requirements.txt."
    exit 1
fi

# Define the port
PORT=5001

echo "Attempting to stop any existing process on port $PORT..."
# Find the PID listening on the specified TCP port
PID=$(lsof -t -i tcp:$PORT -s tcp:LISTEN)

if [ -n "$PID" ]; then
    echo "Found process $PID listening on port $PORT. Terminating..."
    kill -9 $PID
    sleep 1 # Give it a moment to terminate
else
    echo "No process found listening on port $PORT."
fi

echo "Starting the Spelling Bee Flask server..."
echo "Open your browser to http://127.0.0.1:$PORT (or the address shown below)"

# Try to open the browser automatically (macOS)
if [[ "$(uname)" == "Darwin" ]]; then
  open http://127.0.0.1:$PORT &
fi

# Run the Flask application (ensure app.py uses the same PORT)
python3 app.py

# Deactivate virtual environment (if applicable)
# deactivate 
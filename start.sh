#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Stop existing processes
print_color $YELLOW "Stopping any existing processes..."
pkill -f "python backend/app.py"
pkill -f "http-server"

# Forcefully terminate any process using port 5001
lsof -ti:5001 | xargs kill -9

# Check if Python virtual environment exists
if [ ! -d "backend/venv" ]; then
    print_color $RED "Virtual environment not found. Please run setup.sh first."
    exit 1
fi

# Activate virtual environment
source backend/venv/bin/activate

# Check if required files exist
if [ ! -f "backend/app.py" ]; then
    print_color $RED "backend/app.py is missing. Please check your project structure."
    exit 1
fi

if [ ! -d "frontend" ] || [ ! -f "frontend/index.html" ] || [ ! -f "frontend/search_results.js" ]; then
    print_color $RED "Frontend files are missing. Please check your project structure."
    exit 1
fi

# Start the Flask server in the background
print_color $GREEN "Starting the Flask server..."
python backend/app.py &

# Wait for Flask server to start and check if it's running
sleep 5
if ! lsof -ti:5001 > /dev/null
then
    print_color $RED "Failed to start Flask server. Please check for errors."
    exit 1
fi

# Check if http-server is installed
if ! command -v http-server &> /dev/null; then
    print_color $YELLOW "http-server not found. Installing..."
    npm install -g http-server
fi

# Start the frontend server with CORS enabled
print_color $GREEN "Starting the frontend server with CORS enabled..."
(cd frontend && http-server -p 8080 --cors) &

print_color $GREEN "Application is now running."
print_color $GREEN "Access the frontend at http://localhost:8080"
print_color $GREEN "The backend API is available at http://localhost:5001"
print_color $YELLOW "Press Ctrl+C to stop the servers when you're done."

# Wait for user input to keep the script running and servers active
read -p "Press Enter to stop the servers and exit..."

# Kill the background processes
pkill -f "python backend/app.py"
pkill -f "http-server"
lsof -ti:5001 | xargs kill -9

print_color $GREEN "Servers stopped. Goodbye!"
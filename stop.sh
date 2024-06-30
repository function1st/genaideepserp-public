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

# Stop the Flask server
print_color $YELLOW "Stopping Flask server..."
pkill -f "python backend/app.py"

# Forcefully terminate any process using port 5001
lsof -ti:5001 | xargs kill -9

# Stop the http-server
print_color $YELLOW "Stopping http-server..."
pkill -f "http-server"

# Check if processes are still running
if pgrep -f "python backend/app.py" > /dev/null || lsof -ti:5001 > /dev/null
then
    print_color $RED "Failed to stop Flask server. Please stop it manually."
else
    print_color $GREEN "Flask server stopped successfully."
fi

if pgrep -f "http-server" > /dev/null
then
    print_color $RED "Failed to stop http-server. Please stop it manually."
else
    print_color $GREEN "http-server stopped successfully."
fi

print_color $GREEN "Stop script completed."
#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    print_color $RED "Python3 is not installed. Please install Python3 and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null
then
    print_color $RED "pip3 is not installed. Please install pip3 and try again."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null
then
    print_color $RED "Node.js is not installed. Please install Node.js and try again."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null
then
    print_color $RED "npm is not installed. Please install npm and try again."
    exit 1
fi

# Create and activate virtual environment
print_color $YELLOW "Creating and activating virtual environment..."
python3 -m venv backend/venv
source backend/venv/bin/activate

# Install backend dependencies
print_color $YELLOW "Installing backend dependencies..."
pip install -r backend/requirements.txt

# Prompt for API keys and brand name
print_color $YELLOW "Please enter the following information:"
read -p "OpenAI API Key: " openai_api_key
read -p "Bing Web API Subscription Key: " bing_subscription_key
read -p "Bing Custom Search Configuration ID: " custom_config_id
read -p "Brand Name (e.g., YourBrand without .com): " brand_name

# Create .env file
print_color $YELLOW "Creating .env file..."
cat > backend/.env << EOL
OPENAI_API_KEY=${openai_api_key}
BING_SUBSCRIPTION_KEY=${bing_subscription_key}
CUSTOM_CONFIG_ID=${custom_config_id}
EOL

# Update sysprompt.txt with the brand name
print_color $YELLOW "Updating system prompt with brand name..."
sed -i '' "s/\[Your Brand\]=your_brand_here/[Your Brand]=${brand_name}/" backend/sysprompt.txt

# Frontend setup
print_color $YELLOW "Setting up frontend..."

# Check if frontend directory and files exist
if [ ! -d "frontend" ] || [ ! -f "frontend/index.html" ] || [ ! -f "frontend/search_results.js" ]; then
    print_color $RED "Frontend directory or required files are missing. Please check your project structure."
    exit 1
fi

# Update API endpoint in frontend code
print_color $YELLOW "Updating API endpoint in frontend code..."
sed -i '' "s|const API_URL = .*|const API_URL = 'http://localhost:5001/websearch';|" frontend/search_results.js

# Check if package.json exists in the frontend directory
if [ -f "frontend/package.json" ]; then
    print_color $YELLOW "Installing frontend dependencies..."
    (cd frontend && npm install)
fi

# Install http-server globally if not already installed
if ! command -v http-server &> /dev/null
then
    print_color $YELLOW "Installing http-server..."
    npm install -g http-server
fi

print_color $GREEN "Setup complete!"
print_color $GREEN "To start the application, run ./start.sh"
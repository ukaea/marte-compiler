#!/bin/bash

# Check if Python 3 is installed
PYTHON_EXEC="/usr/bin/python3"
if ! command -v $PYTHON_EXEC &> /dev/null
then
    echo "Python 3 could not be found. Please install Python 3 before running this script."
    exit 1
fi

# Check if Python 3 is installed
GIT_EXEC="/usr/bin/git"
if ! command -v $GIT_EXEC &> /dev/null
then
    echo "Git could not be found. Please install Git before running this script."
    exit 1
fi

# Define variables
SERVICE_NAME="martecompiler"
REPO_PATH="/opt/martecompiler"
VENV_PATH="$REPO_PATH/venv"
MAIN_SCRIPT="$REPO_PATH/main.py"
USER="martecompilerrunner"
USER_HOME="/home/$USER"

# Step 1: Create the system user if it doesn't exist
if ! id -u "$USER" &>/dev/null; then
    echo "Creating system user $USER..."
    useradd -r -m -d "$USER_HOME" -s /usr/sbin/nologin "$USER"
    echo "System user $USER created with home directory $USER_HOME."
else
    echo "System user $USER already exists."
fi

# Step 1: Clone the repository (if necessary) or update it
if [ ! -d "$REPO_PATH" ]; then
    echo "Cloning the repository..."
    git clone https://git.ccfe.ac.uk/marte21/public/marte-compiler.git "$REPO_PATH"
else
    echo "Updating the repository..."
    cd "$REPO_PATH" && git pull
fi

pip install venv --exists-action=w

# Step 2: Set up the Python virtual environment
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating Python virtual environment..."
    $PYTHON_EXEC -m venv "$VENV_PATH"
fi

# Step 3: Install Python dependencies if not already installed
echo "Installing Python dependencies..."
source "$VENV_PATH/bin/activate"

# Check if requirements need to be installed or updated
pip install --upgrade pip
pip install --upgrade $REPO_PATH --exists-action=w

# Step 3: Set up the systemd service file
echo "Creating systemd service file..."
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

cat <<EOT > $SERVICE_FILE
[Unit]
Description=MARTe2 Compiler Service for remote compilations
After=network.target

[Service]
User=root
WorkingDirectory=$REPO_PATH
ExecStart=$VENV_PATH/bin/python3 -m martecompiler
Restart=always
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOT

# Step 4: Reload systemd, enable and start the service
echo "Reloading systemd, enabling, and starting the service..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl start $SERVICE_NAME

echo "Service $SERVICE_NAME has been installed and started."
#!/bin/bash
# Strict mode: exit immediately on error, treat unset variables as errors,
# and propagate failures through pipes rather than silently ignoring them
set -euo pipefail

# -----------------------------------------------------------------------
# deploy_ec2.sh
# Automates the deployment of the Flask observability app on an Ubuntu EC2
# instance. Running this script produces a reproducible deployment state,
# which supports the dissertation requirement for a documented methodology.
# -----------------------------------------------------------------------

REPO_URL="https://github.com/Oshim123/observability-cicd-pipeline.git"
REPO_DIR="$HOME/observability-cicd-pipeline"
APP_LOG_DIR="/var/log/observability-app"
APP_LOG_FILE="$APP_LOG_DIR/app.log"
APP_PORT=5000

echo "=== Starting EC2 deployment ==="

# Install system-level dependencies needed to run the app and clone the repo
# python3 and pip are required for Flask; git is required to fetch the repository
echo "Installing system dependencies..."
sudo apt update -y
sudo apt install -y python3 python3-pip git

# Clone the repository if it does not already exist,
# or pull the latest changes if it does.
# This ensures the deployment always reflects the current codebase
# without requiring a manual clone on each run.
if [ -d "$REPO_DIR" ]; then
    echo "Repository already exists. Pulling latest changes..."
    cd "$REPO_DIR"
    git pull
else
    echo "Cloning repository..."
    git clone "$REPO_URL" "$REPO_DIR"
    cd "$REPO_DIR"
fi

# Install Python dependencies from the root requirements file
# using the repo's requirements.txt ensures the same versions
# are used consistently across deployments
echo "Installing Python requirements..."
pip3 install -r requirements.txt

# Create the log directory and file that CloudWatch agent reads from
# the directory must exist before the Flask app starts,
# otherwise the file handler in app.py will fall back to console-only logging
echo "Setting up log directory..."
sudo mkdir -p "$APP_LOG_DIR"
sudo touch "$APP_LOG_FILE"
# Transfer ownership to the current user so the app can write without sudo
sudo chown "$USER":"$USER" "$APP_LOG_DIR"
sudo chown "$USER":"$USER" "$APP_LOG_FILE"

# Kill any existing Flask process running on the app port
# to prevent port conflicts when redeploying without rebooting
echo "Stopping any existing Flask process on port $APP_PORT..."
fuser -k "$APP_PORT"/tcp 2>/dev/null || true
# the '|| true' prevents the script from exiting if no process was found

# Start the Flask app in the background using nohup
# so it continues running after the SSH session ends.
# Output is appended to the application log file for CloudWatch ingestion.
echo "Starting Flask application..."
nohup python3 "$REPO_DIR/app/app.py" >> "$APP_LOG_FILE" 2>&1 &

# Brief pause to allow the process to start before we inspect it
sleep 2

echo ""
echo "=== Deployment complete ==="
echo "Flask process:"
# Display the running Flask process to confirm it started successfully
pgrep -a -f "app.py" || echo "Warning: Flask process not detected. Check $APP_LOG_FILE for errors."

echo ""
echo "Test the application at:"
echo "  http://<EC2_PUBLIC_IP>:$APP_PORT/"
echo "  http://<EC2_PUBLIC_IP>:$APP_PORT/health"
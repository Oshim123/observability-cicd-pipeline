import os
import subprocess
import sys
import time

# Automated bootstrap script to handle environment setup and execution.
# Automates virtual environment creation and dependency installation.

def setup_the_environment(venv_path):
    # Check for existing environment to prevent redundant creation.
    # If .venv is missing, initialize a new environment using the venv module.
    if not os.path.exists(venv_path):
        print("Setup: Virtual environment not found. Creating it now...")
        # Utilize sys.executable to maintain Python version consistency.
        subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
    else:
        # Skip creation if directory exists to decrease startup latency.
        print("Setup: Virtual environment already exists. Skipping creation.")

def get_python_executable(venv_path):
    # Determine the operating system to locate the correct Python binary path.
    # Windows utilizes 'Scripts', while POSIX systems (Linux/Mac) utilize 'bin'.
    if os.name == "nt":
        return os.path.join(venv_path, "Scripts", "python.exe")
    else:
        return os.path.join(venv_path, "bin", "python")

def run_the_project():
    # Entry point for the automated setup and execution sequence.
    print("Automated bootstrap starting up")
    
    # Resolve absolute path of the current script to ensure correct working directory.
    current_folder = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_folder)

    # Standardized naming for the local virtual environment.
    venv_folder = os.path.join(current_folder, ".venv")
    
    # Verify environment integrity.
    setup_the_environment(venv_folder)

    # Resolve the path to the Python interpreter within the environment.
    python_exe = get_python_executable(venv_folder)
    
    print("Setup: Upgrading pip...")
    # Upgrade pip to ensure compatibility with modern wheel distributions.
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    print("Setup: Installing dependencies from requirements.txt...")
    # Isolated installation of required libraries (Flask, Boto3, Requests).
    # Ensures system portability and prevents dependency conflicts.
    subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

    print("Running: Launching the main demo script...")
    # Execute the primary demonstration script within the virtual environment context.
    try:
        # Direct execution via the venv interpreter ensures all dependencies are resolved.
        subprocess.run([python_exe, "demo.py"], check=True)
    except Exception as e:
        print("Error: The application failed to initialize. Message: " + str(e))
        return 1
        
    return 0

if __name__ == "__main__":
    # Return execution status code to the shell.
    # Standard practice for pipeline integration and automated reporting.
    status = run_the_project()
    sys.exit(status)
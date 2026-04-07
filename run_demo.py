import os
import subprocess
import sys
import time

# This script is meant to handle the setup and run everything at once
# It makes sure the virtual environment is ready before launching the demo

def setup_the_environment(venv_path):
    # Checking if the .venv folder is already there
    # If it is missing, we need to create it using the venv module
    if not os.path.exists(venv_path):
        print("Setup: Virtual environment not found. Creating it now...")
        # Running the python command to make the venv
        subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
    else:
        # If it's already there, we just skip this part to save time
        print("Setup: Virtual environment already exists. Skipping creation.")

def get_python_executable(venv_path):
    # I need to know if this is Windows or Linux/Mac because the folders are different
    # Windows uses 'Scripts' but Mac/Linux uses 'bin'
    if os.name == "nt":
        return os.path.join(venv_path, "Scripts", "python.exe")
    else:
        return os.path.join(venv_path, "bin", "python")

def run_the_project():
    print("One-command bootstrap starting up")
    
    # Get the current folder where this script is located
    current_folder = os.path.dirname(os.path.abspath(__file__))
    os.chdir(current_folder)

    # Define the name of the virtual environment folder
    venv_folder = os.path.join(current_folder, ".venv")
    
    # Call the setup function
    setup_the_environment(venv_folder)

    # Find the right python path inside that venv
    python_exe = get_python_executable(venv_folder)
    
    print("Setup: Making sure pip is up to date...")
    # It's usually good practice to upgrade pip first
    subprocess.run([python_exe, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    
    print("Setup: Installing everything from requirements.txt...")
    # This installs flask and requests and whatever else is in the file
    subprocess.run([python_exe, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

    print("Running: Launching the main demo script...")
    # Now we actually run the demo.py using the venv python
    # This ensures it has access to all the libraries we just installed
    try:
        subprocess.run([python_exe, "demo.py"])
    except Exception as e:
        print("Error: The demo failed to start. Message: " + str(e))
        return 1
        
    return 0

if __name__ == "__main__":
    # Running everything and exiting with the right code
    status = run_the_project()
    sys.exit(status)
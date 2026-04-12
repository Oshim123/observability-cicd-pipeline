import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# List of files needed for the system to operate. 
# Checking these early stops the programme from failing halfway through.
REQUIRED_FILES = [
    "app/app.py",
    "scripts/experiment_runner.py",
    "scripts/load_test.py",
    "scripts/cpu_stress.py",
    "scripts/memory_stress.py",
]

def section(title):
    # Helper to print a visual header in the terminal.
    # Helps keep track of which step the setup is currently performing.
    print("\n****************************************")
    print("=== " + str(title).upper() + " ===")
    print("****************************************")

def validate_environment():
    # Checking that the Python version is up to date.
    # This ensures modern features used in the code behave properly.
    major = sys.version_info.major
    minor = sys.version_info.minor
    
    print("Checking Python version...")
    if major != 3 or minor < 10 or minor > 12:
        print("Error: Python 3.10-3.12 is required.")
        print("Your version is: " + str(sys.version.split()[0]))
        return False

    # Confirms every necessary file is present in the folder.
    # If a file is missing, the script stops to avoid a crash later.
    print("Checking for required files...")
    for f in REQUIRED_FILES:
        file_path_obj = Path(f)
        if file_path_obj.exists() == False:
            print("Missing a file: " + str(f))
            return False
            
    print("Environment is OK!")
    return True

def find_free_port():
    # Scans a few ports to find one that is not being used.
    # This prevents the web server from failing due to a port conflict.
    print("Looking for a free port...")
    for p in range(5000, 5011):
        # A quick connection test is done on each port.
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Non-zero result means the port is available.
        res = test_socket.connect_ex(('127.0.0.1', p))
        test_socket.close()
        
        if res != 0:
            print("Found free port: " + str(p))
            return p
            
    return 5000 

def wait_for_server(base_url, timeout_seconds=30):
    # Waits for the web server to finish starting up.
    # Ensures the tests do not begin before the system is ready.
    max_time = time.time() + timeout_seconds
    count = 1

    while time.time() < max_time:
        print("Checking if server is awake... attempt " + str(count))
        try:
            # Calls the health check endpoint to confirm the server is responsive.
            r = requests.get(base_url + "/health", timeout=2)
            if r.status_code == 200:
                print("Server is ready and healthy!")
                return True
        except:
            # If the server is not ready, the script waits a second and tries again.
            pass
        
        count = count + 1
        time.sleep(1)

    print("Server took too long to start.")
    return False

def stop_server(proc_object):
    # Closes the background web server once the work is finished.
    # This keeps the system tidy and frees up memory.
    if proc_object is None:
        return
        
    if proc_object.poll() is not None:
        return

    print("Closing the web server...")
    # Tries to stop it properly first.
    proc_object.terminate()
    
    try:
        proc_object.wait(timeout=5)
    except:
        # Forces it to close if it becomes stuck.
        proc_object.kill()
        proc_object.wait(timeout=5)

def show_summary(results_folder):
    # Finds the results file and reads the saved data.
    path = Path(results_folder) / "summary.json"
    
    if path.exists() == False:
        print("Could not find the summary.json file.")
        return False
        
    with open(path, 'r') as f:
        data = json.load(f)
    
    # Grabbing the detailed results list.
    d = data.get('details', [])

    if not d:
        print("No detailed results found.")
        return False

    section("Results Summary")

    # Looping through every test result found in the file.
    # This avoids crashes if a test failed or if the order changed.
    for item in d:
        name = item.get("scenario", "unknown")
        baseline = item.get("baseline", {}).get("metrics", {})
        fault = item.get("fault", {}).get("metrics", {})

        # Displaying the speed measurements.
        print(name.upper() + " Baseline: " + str(baseline.get("avg_ms", "N/A")) + "ms")
        print(name.upper() + " Fault:    " + str(fault.get("avg_ms", "N/A")) + "ms")

        # Displaying error rates if they are present in the data.
        if "error_rate" in baseline or "error_rate" in fault:
            print(name.upper() + " Error Baseline: " + str(baseline.get("error_rate", "N/A")))
            print(name.upper() + " Error Fault:    " + str(fault.get("error_rate", "N/A")))

        print("-" * 40)

    return True

def main():
    # Setting up the options for the test run.
    my_parser = argparse.ArgumentParser()
    my_parser.add_argument("--requests", type=int, default=10)
    my_parser.add_argument("--duration", type=int, default=5)
    my_parser.add_argument("--repeats", type=int, default=1)
    
    args = my_parser.parse_args()

    # Validating that the numbers provided are sensible.
    if args.requests <= 0 or args.duration <= 0 or args.repeats <= 0:
        print("Please use numbers greater than 0 for requests/duration/repeats")
        return 1

    section("Observability Project Demo")
    print("Step 1: Check environment")
    if validate_environment() == False:
        return 1

    # Marking the start time to see how long the whole process takes.
    start_time_float = time.time()
    
    # Finding a port and setting the web address.
    target_port = find_free_port()
    my_url = "http://127.0.0.1:" + str(target_port)
    
    # Creating a unique folder name for these results using the date and time.
    time_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = "run_" + str(time_stamp)
    final_results_path = Path("results") / folder_name

    print("\nStarting the web server on port " + str(target_port))
    # Launching the application in the background.
    my_app_process = subprocess.Popen([sys.executable, "app/app.py", "--port", str(target_port)])

    try:
        # Checking if the server is fully ready before starting the tests.
        if wait_for_server(my_url) == False:
            stop_server(my_app_process)
            return 1

        print("Now starting the experiment runner...")
        
        # Preparing the instruction to run the main testing logic.
        run_cmd = [
            sys.executable,
            "scripts/experiment_runner.py",
            "--base-url", my_url,
            "--requests", str(args.requests),
            "--duration", str(args.duration),
            "--repeats", str(args.repeats),
            "--results-dir", str(final_results_path),
        ]
        
        # Running the test and waiting for it to finish.
        # check=True ensures the script stops if something goes wrong here.
        subprocess.run(run_cmd, check=True)

        # Pulling the recorded data and showing it on the screen.
        is_successful = show_summary(final_results_path)
        
        # Calculating the total time the process took.
        total_seconds = int(time.time() - start_time_float)
        
        print("\nResults are saved in: " + str(final_results_path))
        print("The whole process took: " + str(total_seconds) + " seconds")
        
        if is_successful:
            return 0
        else:
            return 1

    except Exception as e:
        print("Something went wrong: " + str(e))
        return 1
    finally:
        # Ensuring the background server is always shut down at the end.
        stop_server(my_app_process)

if __name__ == "__main__":
    # Starting the programme and exiting with the correct status code.
    exit_code = main()
    sys.exit(exit_code)
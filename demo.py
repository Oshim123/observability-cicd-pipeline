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

# These are the files I need to make sure exist before I start the test
# I put them in a list so I can loop through them easily
REQUIRED_FILES = [
    "app/app.py",
    "scripts/experiment_runner.py",
    "scripts/load_test.py",
    "scripts/cpu_stress.py",
    "scripts/memory_stress.py",
]

def section(title):
    # Just a helper to print nice headers in the terminal
    print("\n****************************************")
    print("=== " + str(title).upper() + " ===")
    print("****************************************")

def validate_environment():
    # I'm checking the Python version first
    # This project needs 3.10 or 3.11 or 3.12
    major = sys.version_info.major
    minor = sys.version_info.minor
    
    print("Checking Python version...")
    if major != 3 or minor < 10 or minor > 12:
        print("Error: Python 3.10-3.12 is required.")
        print("Your version is: " + str(sys.version.split()[0]))
        return False

    # Now I loop through my list of required files
    print("Checking for required files...")
    for f in REQUIRED_FILES:
        file_path_obj = Path(f)
        if file_path_obj.exists() == False:
            print("Missing a file you need: " + str(f))
            return False
            
    print("Environment is OK!")
    return True

def find_free_port():
    # I loop through ports 5000 to 5010
    # I do this to find one that is not being used by another app
    print("Looking for a free port...")
    for p in range(5000, 5011):
        # Create a socket to test the port
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # connect_ex returns 0 if it CAN connect (meaning the port is busy)
        # It returns a non-zero number if it is FREE
        res = test_socket.connect_ex(('127.0.0.1', p))
        test_socket.close()
        
        if res != 0:
            print("Found free port: " + str(p))
            return p
            
    # Default to 5000 if I can't find one
    return 5000 

def wait_for_server(base_url, timeout_seconds=30):
    # I need to wait for Flask to actually start up
    # Otherwise the tests will fail immediately
    max_time = time.time() + timeout_seconds
    count = 1

    while time.time() < max_time:
        print("Checking if server is awake... attempt " + str(count))
        try:
            # I call the /health endpoint we made in app.py
            r = requests.get(base_url + "/health", timeout=2)
            if r.status_code == 200:
                print("Server is ready and healthy!")
                return True
        except:
            # If it fails, just wait and try again
            pass
        
        count = count + 1
        time.sleep(1)

    print("Server took too long to start.")
    return False

def stop_server(proc_object):
    # If the process is empty, do nothing
    if proc_object is None:
        return
        
    # Check if it's already finished
    if proc_object.poll() is not None:
        return

    print("Closing the Flask server...")
    # Try to stop it nicely
    proc_object.terminate()
    
    # Wait a few seconds for it to close
    try:
        proc_object.wait(timeout=5)
    except:
        # If it won't close, kill it forcefully
        proc_object.kill()
        proc_object.wait(timeout=5)

def show_summary(results_folder):
    # I need to find the summary.json file in the results folder
    path_to_results = Path(results_folder)
    summary_path = path_to_results / "summary.json"
    
    if summary_path.exists() == False:
        print("I could not find the summary.json file.")
        return False

    # Load the data from the JSON file
    file_content = summary_path.read_text(encoding="utf-8")
    json_data = json.loads(file_content)
    
    # Pull out the summary dictionary
    all_metrics = json_data.get("summary", {})

    section("Results Summary")
    
    # Helper to get the latency numbers easily
    def get_num(scen, ph, m_key):
        val = all_metrics.get(scen, {}).get(ph, {}).get(m_key, "N/A")
        return str(val)

    # Print out the results for the report
    print("CPU Baseline: " + get_num('cpu', 'baseline', 'mean_latency_ms') + "ms")
    print("CPU Fault:    " + get_num('cpu', 'fault', 'mean_latency_ms') + "ms")
    print("----------------------------------------")
    print("Mem Baseline: " + get_num('memory', 'baseline', 'mean_latency_ms') + "ms")
    print("Mem Fault:    " + get_num('memory', 'fault', 'mean_latency_ms') + "ms")
    print("----------------------------------------")
    print("Error Baseline: " + get_num('error', 'baseline', 'error_rate_percent') + "%")
    print("Error Fault:    " + get_num('error', 'fault', 'error_rate_percent') + "%")

    return bool(json_data.get("success"))

def main():
    # Setup the command line arguments
    my_parser = argparse.ArgumentParser()
    my_parser.add_argument("--requests", type=int, default=10)
    my_parser.add_argument("--duration", type=int, default=5)
    my_parser.add_argument("--repeats", type=int, default=1)
    
    args = my_parser.parse_args()

    # Basic check to make sure the numbers make sense
    if args.requests <= 0 or args.duration <= 0 or args.repeats <= 0:
        print("Please use numbers greater than 0 for requests/duration/repeats")
        return 1

    section("Observability Project Demo")
    print("Step 1: Check environment")
    if validate_environment() == False:
        return 1

    # Get the start time for the whole run
    start_time_float = time.time()
    
    # Find a port and set the URL
    target_port = find_free_port()
    my_url = "http://127.0.0.1:" + str(target_port)
    
    # Create a unique name for this results folder
    time_stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = "run_" + str(time_stamp)
    final_results_path = Path("results") / folder_name

    print("\nStarting the Flask app on port " + str(target_port))
    # Use Popen to run Flask in the background
    my_app_process = subprocess.Popen([sys.executable, "app/app.py", "--port", str(target_port)])

    try:
        # Wait for Flask to be ready
        if wait_for_server(my_url) == False:
            stop_server(my_app_process)
            return 1

        print("Now starting the experiment runner...")
        
        # Build the command to run the conductor script
        run_cmd = [
            sys.executable,
            "scripts/experiment_runner.py",
            "--base-url", my_url,
            "--requests", str(args.requests),
            "--duration", str(args.duration),
            "--repeats", str(args.repeats),
            "--results-dir", str(final_results_path),
        ]
        
        # Run it and wait for it to finish
        subprocess.run(run_cmd, check=True)

        # Show the final results on screen
        is_successful = show_summary(final_results_path)
        
        # Calculate how long the whole thing took
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
        # Always make sure to stop the server at the end
        stop_server(my_app_process)

if __name__ == "__main__":
    # Run the main function and exit with the correct code
    exit_code = main()
    sys.exit(exit_code)
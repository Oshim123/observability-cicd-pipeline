import argparse
import json
import os
import logging
import random
import time
from datetime import datetime
from flask import Flask, g, jsonify, request

# --- Start of the App ---
# initialising the Flask web server here
app = Flask(__name__)

# I am setting the logging level to ERROR to reduce noise in the console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) #this logs the requests to the console, but I set it to ERROR so it only logs when something goes wrong

# This is where I am going to save all the data I collect
# I named it app_logs.json so it's easy to find
MY_LOG_FILENAME = "app_logs.json"

def record_activity_to_file(message_text, status_code):
    """
    This is my manual logging function.
    I didn't use the standard Python logger because I wanted 
    to make sure the JSON format was exactly how I needed it.
    """
    
    # 1. Get the current time
    # I need this so I know when the request happened
    now_obj = datetime.now()
    time_string = str(now_obj)
    
    # 2. Calculate Latency
    # I'm checking how much time passed since the request started
    finish_time = time.time()
    total_time_taken = 0
    
    if hasattr(g, 'start_time'):
        # Calculate difference in seconds then convert to milliseconds
        start_time = g.start_time
        difference = finish_time - start_time
        total_time_taken = difference * 1000
        # Round it to 2 decimal places so it's not a huge number
        total_time_taken = round(total_time_taken, 2)

    # 3. Collect Headers
    # I need to know which experiment this is part of
    # I'm pulling these from the request headers sent by my demo script
    current_scenario = "none"
    if "X-Scenario" in request.headers:
        current_scenario = request.headers.get("X-Scenario")
    
    current_run_id = "none"
    if "X-Run-Id" in request.headers:
        current_run_id = request.headers.get("X-Run-Id")

    # 4. Build the dictionary
    # I am putting all the info into a dictionary before saving to JSON
    my_log_data = {}
    my_log_data["timestamp"] = time_string
    my_log_data["endpoint_hit"] = request.path
    my_log_data["http_status"] = status_code
    my_log_data["latency_ms"] = total_time_taken
    my_log_data["message"] = message_text
    my_log_data["experiment"] = current_scenario
    my_log_data["run_number"] = current_run_id

    # 5. Print to console
    # I print it so I can see what's happening in the terminal while I record my video
    json_string = json.dumps(my_log_data)
    print("LOG ENTRY: " + json_string)

    # 6. Write to the file
    # I am using 'a' for append so it doesn't overwrite the old logs
    my_file = open(MY_LOG_FILENAME, "a")
    my_file.write(json_string + "\n")
    my_file.close()
    
    # Done with logging
    return True

@app.before_request
def start_the_timer():
    """
    This function runs before every single request.
    I use it to mark the exact start time.
    """
    # Record the float time for math later
    g.start_time = time.time()

# --- ROUTES ---

@app.route("/")
def home_page():
    # This is the default page
    # calling my log function manually here
    msg = "User visited the home page"
    record_activity_to_file(msg, 200)
    return "Observability App is Running - Version 1.0"

@app.route("/health")
def health_check():
    # The demo script calls this to see if the server is awake
    # I return a 200 status code to show everything is okay
    record_activity_to_file("Health check requested", 200)
    return jsonify({"status": "healthy", "server": "active"}), 200

@app.route("/trigger-error")
def trigger_intentional_error():
    # This route is specifically for testing my error monitoring
    # It always returns a 500 error
    error_message = "This is a planned error for the experiment"
    
    # I log the error before returning it
    record_activity_to_file("ERROR_TRIGGERED: " + error_message, 500)
    
    # Create the error response
    response_data = {
        "status": "error",
        "details": error_message,
        "code": 500
    }
    return jsonify(response_data), 500

@app.route("/unstable")
def unstable_route():
    # This route fails sometimes (40% of the time)
    # I use it to test if my pipeline can detect 'flaky' behavior
    chance = random.random()
    
    if chance < 0.4:
        # FAILED
        record_activity_to_file("Unstable route failed randomly", 500)
        return jsonify({"result": "fail"}), 500
    else:
        # SUCCESS
        record_activity_to_file("Unstable route succeeded", 200)
        return jsonify({"result": "success"}), 200

@app.route("/slow")
def slow_route():
    # This route takes 2 seconds to respond
    # I use it to test latency monitoring
    print("Starting a slow request... waiting 2 seconds")
    time.sleep(2)
    
    record_activity_to_file("Slow route finished", 200)
    return jsonify({"note": "That was a slow response"}), 200

# --- MAIN BLOCK ---

if __name__ == "__main__":
    # Use argparse so I can change the port from the command line
    # My demo script uses this to avoid 'Port already in use' errors
    my_args_parser = argparse.ArgumentParser()
    my_args_parser.add_argument("--port", type=int, default=5000)
    
    # Get the arguments
    parsed_args = my_args_parser.parse_args()
    target_port = parsed_args.port

    print("****************************************")
    print("* FLASK SERVER STARTING UP             *")
    print("* Listening on Port: " + str(target_port))
    print("****************************************")
    
    # Start the Flask app
    # host 0.0.0.0 makes it accessible on the local network
    app.run(host="0.0.0.0", port=target_port, debug=False)
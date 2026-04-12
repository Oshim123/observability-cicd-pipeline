import argparse
import json
import os
import logging
import random
import time
from datetime import datetime
from flask import Flask, g, jsonify, request

# Selection of imports for Flask server execution, per-request data storage with g, and chaos test simulation using random/time modules.

# Application Start
# Initialization of the Flask web server to serve as the target for fault injection.
app = Flask(__name__)

# Logging level set to ERROR to minimize default console noise and prioritize custom JSON telemetry.
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 

# Filename for centralized logging to ensure a consistent data source for downstream analysis.
MY_LOG_FILENAME = "app_logs.json"

def record_activity_to_file(message_text, status_code):
    """
    Custom logging implementation to ensure a specific JSON schema is maintained for the final report.
    Manual formatting used instead of the standard library to guarantee the desired output structure.
    """
    
    # Retrieval of system time as a string to provide human-readable event tracking in the logs.
    now_obj = datetime.now()
    time_string = str(now_obj)
    
    # Calculation of request duration by comparing start and finish timestamps for performance analysis.
    finish_time = time.time()
    total_time_taken = 0
    
    if hasattr(g, 'start_time'):
        # Difference calculated in seconds then converted to milliseconds.
        # Latency value rounded to 2 decimal places to maintain data consistency.
        start_time = g.start_time
        difference = finish_time - start_time
        total_time_taken = round(difference * 1000, 2)

    # Extraction of scenario and run-id headers to correlate client-side load tests with server-side responses.
    # These headers are provided by the load test script for end-to-end traceability.
    current_scenario = request.headers.get("X-Scenario", "none")
    current_run_id = request.headers.get("X-Run-Id", "none")

    # Aggregation of telemetry into a dictionary before serialization to ensure a valid JSON structure.
    my_log_data = {
        "timestamp": time_string,
        "endpoint_hit": request.path,
        "http_status": status_code,
        "latency_ms": total_time_taken,
        "message": message_text,
        "experiment": current_scenario,
        "run_number": current_run_id
    }

    # Output of the log entry to the console for real-time monitoring during the demonstration.
    json_string = json.dumps(my_log_data)
    print("LOG ENTRY: " + json_string)

    # Utilization of append mode to ensure a continuous historical record across multiple experiments.
    # Manual file closure ensures data is flushed to the disk.
    my_file = open(MY_LOG_FILENAME, "a")
    my_file.write(json_string + "\n")
    my_file.close()
    
    return True

@app.before_request
def start_the_timer():
    """
    Pre-request hook to establish a baseline start time for subsequent latency calculations.
    Ensures every request is timed from the moment it reaches the server.
    """
    g.start_time = time.time()

# Application Routes

@app.route("/")
def home_page():
    # Default route for verifying service availability and recording baseline traffic.
    msg = "User visited the home page"
    record_activity_to_file(msg, 200)
    return "Observability App is Running - Version 1.0"

@app.route("/health")
def health_check():
    # Health check endpoint utilized as a safety gate by the demo runner to confirm server readiness.
    # Ensures no experiments begin before the server is fully initialized.
    record_activity_to_file("Health check requested", 200)
    return jsonify({"status": "healthy", "server": "active"}), 200

@app.route("/trigger-error")
def trigger_intentional_error():
    # Dedicated route for testing fault monitoring by returning a 500 status code.
    # Records the failure event before returning the error response.
    error_message = "This is a planned error for the experiment"
    
    record_activity_to_file("ERROR_TRIGGERED: " + error_message, 500)
    
    return jsonify({
        "status": "error",
        "details": error_message,
        "code": 500
    }), 500

@app.route("/unstable")
def unstable_route():
    # Route with a 40 percent failure rate to evaluate observability under flaky conditions.
    # Random probability logic determines the response outcome.
    chance = random.random()
    
    if chance < 0.4:
        # Scenario representing an intermittent failure.
        record_activity_to_file("Unstable route failed randomly", 500)
        return jsonify({"result": "fail"}), 500
    else:
        # Scenario representing a successful transaction.
        record_activity_to_file("Unstable route succeeded", 200)
        return jsonify({"result": "success"}), 200

@app.route("/slow")
def slow_route():
    # Implementation of an artificial 2 second delay to test latency detection capabilities.
    # Demonstrates the ability to detect service bottlenecks without total failure.
    print("Starting a slow request... waiting 2 seconds")
    time.sleep(2)
    
    record_activity_to_file("Slow route finished", 200)
    return jsonify({"note": "That was a slow response"}), 200

# Main execution block

if __name__ == "__main__":
    # Integration of argparse to allow dynamic port selection and prevent local port conflicts.
    # Used by the demo script to coordinate multiple test environments.
    my_args_parser = argparse.ArgumentParser()
    my_args_parser.add_argument("--port", type=int, default=5000)
    
    parsed_args = my_args_parser.parse_args()
    target_port = parsed_args.port

    print("****************************************")
    print("* FLASK SERVER STARTING UP             *")
    print("* Listening on Port: " + str(target_port))
    print("****************************************")
    
    # Host 0.0.0.0 enables network access while disabling debug mode mimics production behavior.
    app.run(host="0.0.0.0", port=target_port, debug=False)
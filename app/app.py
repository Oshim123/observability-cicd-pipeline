import argparse
import json
import os
import random
import time
from datetime import datetime
from flask import Flask, g, jsonify, request

# Create the Flask app
app = Flask(__name__)

# Simple log file in the same folder as the script
LOG_FILE = "app_logs.json"

def write_log(message, status_code=200, extra_info=None):
    """
    Helper function to manually create a JSON log entry.
    I use this instead of the complex logging library because 
    it's easier to control the format for my results.
    """
    # Calculate how long the request took (latency)
    latency = 0
    if hasattr(g, 'start_time'):
        latency = round((time.time() - g.start_time) * 1000, 2)

    # Build the log data manually
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": request.path,
        "status": status_code,
        "latency_ms": latency,
        "message": message
    }

    # Add extra stuff if provided (like the experiment ID)
    if extra_info:
        log_entry.update(extra_info)

    # Print to terminal and save to the JSON file
    print(json.dumps(log_entry))
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# This runs before every request
@app.before_request
def start_timer():
    g.start_time = time.time()
    # Grab headers if the experiment runner sent them
    g.scenario = request.headers.get("X-Scenario", "none")
    g.run_id = request.headers.get("X-Run-Id", "none")

# This runs after every request
@app.after_request
def log_request(response):
    write_log(
        "request_finished", 
        status_code=response.status_code,
        extra_info={"scenario": g.scenario, "run_id": g.run_id}
    )
    return response

@app.route("/")
def index():
    return "Observability App is Running"

@app.route("/health")
def health():
    # Simple check for the demo script to know we are awake
    return {"status": "ok"}, 200

@app.route("/trigger-error")
def trigger_error():
    # Manually trigger a 500 error for the monitoring test
    write_log("intentional_error_triggered", status_code=500)
    return jsonify({
        "status": "error",
        "message": "This is a simulated failure for the experiment."
    }), 500

@app.route("/unstable")
def unstable():
    # 40% chance of failing to test the 'error rate' monitoring
    if random.random() < 0.4:
        return jsonify({"status": "random_failure"}), 500
    return jsonify({"status": "success"}), 200

@app.route("/slow")
def slow():
    # Artificial delay to test latency spikes
    time.sleep(2)
    return jsonify({"status": "slow_response"}), 200

if __name__ == "__main__":
    # Setup argparse so demo.py can tell us which port to use
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    print(f"--- Starting Flask on Port {args.port} ---")
    app.run(host="0.0.0.0", port=args.port)
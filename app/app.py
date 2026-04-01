import argparse
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timezone
from flask import Flask, g, jsonify, request
#these imports all let us use the flask framework to create a web application, 
# handle requests, and manage logging and other utilities.
app = Flask(__name__)

log_file_path = "/var/log/observability-app/app.log"
log_handlers = [logging.StreamHandler()]
#the log file and handler are set up to write logs to both the console 
# and a file, with error handling to ensure the application continues running even if the log file cannot be created.
try:
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    log_handlers.append(logging.FileHandler(log_file_path))
except OSError:
    pass
#this try except block can handle the case where the log file cannot be created, 
# such as due to permissions issues, and ensures that the application continues to run without crashing.
logging.basicConfig(level=logging.INFO, handlers=log_handlers)
logger = logging.getLogger(__name__)
#logging and logger lets you log messages with different severity levels (e.g., INFO, ERROR) 
# and configure how those logs are handled (e.g., written to a file or displayed in the console).
SEED = int(os.getenv("UNSTABLE_SEED", "42"))
_rng = random.Random(SEED)
#seed is set for the random number generator to ensure reproducibility of the "unstable" endpoint's behavior across runs, 
# which is important for consistent testing and monitoring experiments.

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        } #payload is a dictionary that includes the timestamp, log level, and message. 
        #its used to structure log entries in a consistent JSON format, making it easier to parse and analyse logs in monitoring systems or log management tools.
        extra_fields = ("request_id", "endpoint", "status_code", "latency_ms", "scenario", "run_id")
        for field in extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload)
#extra_fields is a tuple of additional fields that may be included in log records. 
# it will check if these fields are present in the log record and include them in the JSON payload if they exist.
#if none of the extra fields are present, it will simply return the basic log information (timestamp, level, message) in JSON format.
for handler in logger.handlers:
    handler.setFormatter(JsonFormatter())
#for loop loops through all the handlers attached to the logger and sets their formatter to an instance of JsonFormatter 
# so that all log messages will be formatted as JSON when they are emitted.

@app.before_request
def _start_request_tracking():
    g.start = time.time()
    g.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    g.scenario = request.headers.get("X-Scenario")
    g.run_id = request.headers.get("X-Run-Id")
#the different fields being set in the g object (start, request_id, scenario, run_id) are used to track the request's start time, 
# so that latency can be calculated later, and to capture any relevant metadata about the request (like scenario and run ID) for logging purposes.

@app.after_request
def _log_response(response):
    latency_ms = round((time.time() - g.start) * 1000, 2)
    logger.info(
        "request_complete",
        extra={
            "request_id": g.request_id,
            "endpoint": request.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "scenario": g.scenario,
            "run_id": g.run_id,
        },
    )
    response.headers["X-Request-Id"] = g.request_id
    return response


@app.route("/")
def home():
    return "Observability Pipeline Running"


@app.route("/health")
def health():
    return {"status": "healthy"}, 200
    
    
    


@app.route("/trigger-error")
def trigger_error():
    logger.error(
        "intentional_error",
        extra={
            "request_id": g.request_id,
            "endpoint": request.path,
            "scenario": g.scenario,
            "run_id": g.run_id,
        },
    )
    return jsonify(
        {
            "status": "error",
            "message": "Intentional failure triggered for monitoring experiment.",
        }
    ), 500


@app.route("/unstable")
def unstable():
    if _rng.random() < 0.4:
        return jsonify({"status": "error"}), 500
    return jsonify({"status": "success"}), 200


@app.route("/slow")
def slow():
    time.sleep(5)
    return jsonify({"status": "delayed response"}), 200


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Flask app for observability experiments")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PORT", "5000")),
        help="Port to bind Flask on (default: PORT env var or 5000)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    logger.info(f"app_started seed={SEED}")
    args = parse_args()
    app.run(host="0.0.0.0", port=args.port)

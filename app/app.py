# Import Flask to create a lightweight web server
from flask import Flask, jsonify
#jsonify is used to return structured JSON responses (useful for monitoring + testing)

# Import logging module to enable structured logs
import logging

import random
#random is used to simulate intermittent failures for error-rate monitoring experiments

import time
#time is used to simulate slow responses (latency) for performance degradation experiments


# Create Flask application instance (name tells Flask where to look for resources)
app = Flask(__name__)

# Configure logging level to INFO 
# (this will log informational messages and above, but not debug messages)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
    #format asctime will show the time of the log entry, levelname will show the severity (INFO, ERROR, etc.),
    # and message will show the log message itself.
)

# Create logger object (this will be used to log messages in the application)
logger = logging.getLogger(__name__)

# Log application startup to demonstrate lifecycle observability
logger.info("Application initialised successfully")


# Define the root endpoint
@app.route("/")
def home():
    """
    Root endpoint used to confirm the application is running.
    Generates a log entry to demonstrate observability.
    Observability is about tracking the behaviour of the application,
    so we log when the endpoint is accessed.
    """
    logger.info("Root endpoint accessed successfully")
    return "Observability Pipeline Running"


# Define health check endpoint
@app.route("/health")
def health():
    """
    Health endpoint used by monitoring systems
    to verify application availability.

    A separate endpoint is used because dedicated health check
    endpoints are a common practice and allow monitoring tools
    to check the application's status without affecting
    the main functionality.
    """
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}, 200


# Define controlled error endpoint
@app.route("/trigger-error")
def trigger_error():
    """
    This endpoint deliberately returns a server error (HTTP 500)
    to simulate application failure.

    It is used during observability experiments to evaluate
    whether monitoring systems detect increased error rates.
    """
    logger.error("Intentional application error triggered for observability testing")
    #logging this at ERROR level ensures it appears clearly in monitoring systems

    return jsonify({
        "status": "error",
        "message": "Intentional failure triggered for monitoring experiment."
    }), 500


# Define unstable endpoint to simulate intermittent failures
@app.route("/unstable")
def unstable():
    """
    This endpoint simulates intermittent behaviour.
    It randomly returns either success (200) or failure (500).

    This helps test whether monitoring systems can detect
    error rate thresholds rather than only total failure.
    """
    if random.random() < 0.4:
        logger.error("Random failure occurred in unstable endpoint")
        return jsonify({"status": "error"}), 500
    else:
        logger.info("Unstable endpoint returned success")
        return jsonify({"status": "success"}), 200


# Define slow response endpoint
@app.route("/slow")
def slow():
    """
    This endpoint simulates performance degradation
    by deliberately delaying the response.

    It helps evaluate whether monitoring systems detect
    increased latency before total failure occurs.
    """
    logger.info("Slow endpoint triggered, introducing artificial delay")
    
    time.sleep(5)
    #sleep causes a 5 second delay to simulate slow processing
    
    return jsonify({"status": "delayed response"}), 200


# Entry point for running the application
if __name__ == "__main__":
    # host="0.0.0.0" allows external access when deployed to EC2
    # This lets the application listen on all network interfaces,
    # which is necessary when running in a container or on a cloud instance.
    app.run(host="0.0.0.0", port=5000)
#port 5000 is the default port for Flask applications, but it can be changed if needed.
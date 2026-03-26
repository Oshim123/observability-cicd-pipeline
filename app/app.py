from flask import Flask, jsonify
import argparse
import logging
import os
import random
import time

app = Flask(__name__)

log_file_path = "/var/log/observability-app/app.log"
log_handlers = [logging.StreamHandler()]

try:
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    log_handlers.append(logging.FileHandler(log_file_path))
except OSError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=log_handlers,
)

logger = logging.getLogger(__name__)
logger.info("Application initialised successfully")


@app.route("/")
def home():
    logger.info("Root endpoint accessed successfully")
    return "Observability Pipeline Running"


@app.route("/health")
def health():
    logger.info("Health check endpoint accessed")
    return {"status": "healthy"}, 200


@app.route("/trigger-error")
def trigger_error():
    logger.error("Intentional application error triggered for observability testing")
    return jsonify(
        {
            "status": "error",
            "message": "Intentional failure triggered for monitoring experiment.",
        }
    ), 500


@app.route("/unstable")
def unstable():
    if random.random() < 0.4:
        logger.error("Random failure occurred in unstable endpoint")
        return jsonify({"status": "error"}), 500
    logger.info("Unstable endpoint returned success")
    return jsonify({"status": "success"}), 200


@app.route("/slow")
def slow():
    logger.info("Slow endpoint triggered, introducing artificial delay")
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
    args = parse_args()
    app.run(host="0.0.0.0", port=args.port)

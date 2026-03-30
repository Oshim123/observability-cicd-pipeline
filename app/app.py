import argparse
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timezone

from flask import Flask, g, jsonify, request

app = Flask(__name__)

log_file_path = "/var/log/observability-app/app.log"
log_handlers = [logging.StreamHandler()]

try:
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    log_handlers.append(logging.FileHandler(log_file_path))
except OSError:
    pass

logging.basicConfig(level=logging.INFO, handlers=log_handlers)
logger = logging.getLogger(__name__)

SEED = int(os.getenv("UNSTABLE_SEED", "42"))
_rng = random.Random(SEED)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        extra_fields = ("request_id", "endpoint", "status_code", "latency_ms", "scenario", "run_id")
        for field in extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload)


for handler in logger.handlers:
    handler.setFormatter(JsonFormatter())


@app.before_request
def _start_request_tracking():
    g.start = time.time()
    g.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    g.scenario = request.headers.get("X-Scenario")
    g.run_id = request.headers.get("X-Run-Id")


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

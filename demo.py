import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

REQUIRED_FILES = [
    "app/app.py",
    "scripts/experiment_runner.py",
    "scripts/load_test.py",
    "scripts/cpu_stress.py",
    "scripts/memory_stress.py",
]


def section(title):
    print(f"\n=== {title} ===")


def validate_environment():
    section("Pre-flight Validation")

    if sys.version_info < (3, 10) or sys.version_info >= (3, 13):
        print("❌ Python 3.10-3.12 is required for this demo.")
        print(f"Detected: {sys.version.split()[0]}")
        return False

    missing = [path for path in REQUIRED_FILES if not Path(path).exists()]
    if missing:
        print("❌ Missing required files:")
        for item in missing:
            print(f" - {item}")
        return False

    has_aws = bool(os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"))
    if not has_aws:
        print("⚠️ AWS credentials not detected. This is fine for local demo mode.")

    print("✅ Environment checks passed")
    return True


def find_available_port(start=5000, end=5050):
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No free port found between {start} and {end}")


def wait_for_app(base_url, timeout_seconds=30):
    section("Waiting for Flask Server")
    deadline = time.time() + timeout_seconds
    attempt = 1

    while time.time() < deadline:
        print(f"Waiting for server... (attempt {attempt})")
        try:
            response = requests.get(f"{base_url}/health", timeout=2)
            if response.status_code == 200:
                print("Server ready")
                return True
        except requests.RequestException:
            pass
        attempt += 1
        time.sleep(1)

    print("❌ Flask server did not become healthy within 30 seconds.")
    print("Suggested fix: ensure selected port is free and try again.")
    return False


def terminate_process(proc):
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def print_results_summary(results_dir):
    summary_file = results_dir / "summary.json"
    if not summary_file.exists():
        print("⚠️ summary.json not found; cannot print run metrics.")
        return

    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    section("Results Summary")

    for phase in summary.get("phases", []):
        metrics_file = phase.get("metrics_file")
        if not metrics_file:
            continue
        metrics_path = Path(metrics_file)
        if not metrics_path.exists():
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        print(
            f"{phase['phase']}: avg latency={metrics['average_latency_ms']} ms, "
            f"error rate={metrics['error_rate_percent']}%"
        )

    print(f"Results saved to: {results_dir}")


def main():
    parser = argparse.ArgumentParser(description="Run local observability experiments")
    parser.add_argument("--requests", type=int, default=50, help="Requests per phase for demo run")
    parser.add_argument("--duration", type=int, default=20, help="Stress duration (seconds)")
    args = parser.parse_args()

    section("Starting Observability Demo")

    if not validate_environment():
        return 1

    selected_port = find_available_port(5000, 5050)
    if selected_port != 5000:
        print(f"⚠️ Port 5000 in use, using fallback port {selected_port}")

    base_url = f"http://127.0.0.1:{selected_port}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("results") / f"run_{timestamp}"

    section("Starting Flask Server")
    app_process = subprocess.Popen(
        [sys.executable, "app/app.py", "--port", str(selected_port)],
        stdout=None,
        stderr=None,
    )

    interrupted = {"value": False}

    def handle_interrupt(signum, frame):
        interrupted["value"] = True
        print("\n⚠️ Interrupted by user. Shutting down gracefully...")
        terminate_process(app_process)
        raise KeyboardInterrupt

    previous_sigint = signal.getsignal(signal.SIGINT)
    previous_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, handle_interrupt)
    signal.signal(signal.SIGTERM, handle_interrupt)

    try:
        if not wait_for_app(base_url):
            return 1

        section("Running Experiment Pipeline")
        cmd = [
            sys.executable,
            "scripts/experiment_runner.py",
            "--base-url",
            base_url,
            "--requests",
            str(args.requests),
            "--duration",
            str(args.duration),
            "--results-dir",
            str(results_dir),
        ]
        subprocess.run(cmd, check=True)

        print_results_summary(results_dir)
        print("✅ Demo finished successfully")
        return 0

    except subprocess.CalledProcessError as exc:
        print(f"❌ Experiment run failed with exit code {exc.returncode}")
        print(f"Results (partial or complete): {results_dir}")
        return 1
    except KeyboardInterrupt:
        return 1
    finally:
        section("Stopping Flask Server")
        terminate_process(app_process)
        signal.signal(signal.SIGINT, previous_sigint)
        signal.signal(signal.SIGTERM, previous_sigterm)
        if interrupted["value"]:
            print("Flask server stopped after interrupt")
        else:
            print("Flask server stopped")


if __name__ == "__main__":
    sys.exit(main())

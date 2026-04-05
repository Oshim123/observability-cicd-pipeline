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
    # Keep requirements explicit so marker failures are obvious and fast.
    if sys.version_info < (3, 10) or sys.version_info >= (3, 13):
        print("Python 3.10-3.12 is required.")
        print(f"Detected: {sys.version.split()[0]}")
        return False

    for file_path in REQUIRED_FILES:
        if not Path(file_path).exists():
            print(f"Missing required file: {file_path}")
            return False

    return True

def find_free_port():
    # Loop through ports 5000 to 5010 to find one that isn't busy
    # This is my workaround for the 'Address already in use' bug
    for p in range(5000, 5011):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # connect_ex returns a non-zero number if the port is FREE
        result = sock.connect_ex(('127.0.0.1', p))
        sock.close()
        
        if result != 0:
            return p
    return 5000 # Fallback to 5000 if none found (Fix #3)

def wait_for_server(base_url, timeout_seconds=30):
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

    print("Server did not become healthy within 30 seconds.")
    return False

def stop_server(proc):
    if proc is None:
        return
    if proc.poll() is not None:
        return

    print("Stopping Flask server...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)

def show_summary(results_dir):
    # Fix #2: Pathlib Insurance - convert results_dir to a Path object
    res_path = Path(results_dir)
    summary_file = res_path / "summary.json"
    
    if not summary_file.exists():
        print("summary.json not found.")
        return False

    data = json.loads(summary_file.read_text(encoding="utf-8"))
    summary = data.get("summary", {})

    def metric(scenario, phase, key):
        return summary.get(scenario, {}).get(phase, {}).get(key, "N/A")

    section("Results Summary")
    print(
        "CPU latency (baseline -> fault): "
        f"{metric('cpu', 'baseline', 'mean_latency_ms')}ms -> "
        f"{metric('cpu', 'fault', 'mean_latency_ms')}ms"
    )
    print(
        "Memory latency (baseline -> fault): "
        f"{metric('memory', 'baseline', 'mean_latency_ms')}ms -> "
        f"{metric('memory', 'fault', 'mean_latency_ms')}ms"
    )
    print(
        "Error rate (baseline -> fault): "
        f"{metric('error', 'baseline', 'error_rate_percent')}% -> "
        f"{metric('error', 'fault', 'error_rate_percent')}%"
    )

    return bool(data.get("success"))

def main():
    parser = argparse.ArgumentParser(description="Run local observability demo")
    parser.add_argument("--requests", type=int, default=10, help="Requests per phase")
    parser.add_argument("--duration", type=int, default=5, help="Stress duration in seconds")
    parser.add_argument("--repeats", type=int, default=1, help="Repeats per scenario")
    args = parser.parse_args()

    if args.requests <= 0 or args.duration <= 0 or args.repeats <= 0:
        print("--requests, --duration, and --repeats must all be > 0")
        return 1

    section("Observability Demo")
    print("This will:")
    print("- start a Flask server")
    print("- run baseline/fault scenarios (cpu, memory, error)")
    print("- write results to results/run_<timestamp>/")
    print("\nExpected runtime: ~30-60 seconds")

    if not validate_environment():
        return 1

    started_at = time.time()
    port = find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    run_id = datetime.now().strftime("run_%Y-%m-%d_%H-%M-%S")
    results_dir = Path("results") / run_id

    print(f"\nStarting Flask on port {port}...")
    app_proc = subprocess.Popen([sys.executable, "app/app.py", "--port", str(port)])

    try:
        if not wait_for_server(base_url):
            return 1

        cmd = [
            sys.executable,
            "scripts/experiment_runner.py",
            "--base-url",
            base_url,
            "--requests",
            str(args.requests),
            "--duration",
            str(args.duration),
            "--repeats",
            str(args.repeats),
            "--results-dir",
            str(results_dir),
        ]
        subprocess.run(cmd, check=True)

        success = show_summary(results_dir)
        elapsed = int(time.time() - started_at)
        print(f"\nResults saved to: {results_dir}/")
        print(f"Total runtime: {elapsed}s")
        return 0 if success else 1

    except subprocess.CalledProcessError as exc:
        print(f"Experiment runner failed with exit code {exc.returncode}")
        return 1
    except KeyboardInterrupt:
        print("\nStopped by user.")
        return 1
    finally:
        stop_server(app_proc)

if __name__ == "__main__":
    sys.exit(main())
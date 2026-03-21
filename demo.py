import subprocess
import time
import sys
import requests
import os
import glob

# this script provides a single-command demo of the observability pipeline.
# it starts the Flask application, waits until it is ready to accept requests,
# runs the full experiment suite using experiment_runner.py, and then shuts down.
# this ensures the demo is reproducible and does not require manual setup steps.

# the base URL used to check application health and pass to the experiment runner
BASE_URL = "http://127.0.0.1:5000"


def wait_for_app(url, timeout=10):
    # poll the /health endpoint until the Flask app responds or the timeout is reached.
    # this prevents the experiment runner from starting before the app is ready,
    # which would cause all requests to fail immediately.
    print("Waiting for Flask app to start...")
    for _ in range(timeout):
        try:
            r = requests.get(f"{url}/health")
            if r.status_code == 200:
                # include the URL so it is immediately visible during the demo
                print("Flask app is live at http://127.0.0.1:5000\n")
                return True
        except Exception:
            # connection refused means the app is not ready yet, so wait and retry
            pass
        time.sleep(1)
    return False


def main():
    print("Starting Observability Pipeline Demo\n")

    # start the Flask application as a background process
    # stdout and stderr are set to None so output appears in the terminal,
    # which makes it easier to see what the application is doing during the demo
    print("Launching Flask application...")
    app_process = subprocess.Popen(
        [sys.executable, "app/app.py"],
        stdout=None,
        stderr=None
    )

    # wait until the Flask application is accepting requests before proceeding
    if not wait_for_app(BASE_URL):
        print("Flask app failed to start within the timeout period")
        app_process.terminate()
        return

    # run the full experiment suite using the existing experiment runner.
    # --requests 50 and --duration 20 are used here for a shorter demo run.
    # for full experiments, increase these values to match the dissertation parameters.
    # timeout=120 prevents the demo freezing if the runner hangs unexpectedly
    print("Running full experiment pipeline...\n")

    try:
        subprocess.run([
            sys.executable,
            "scripts/experiment_runner.py",
            "--base-url", BASE_URL,
            "--requests", "50",
            "--duration", "20"
        ], timeout=120)

        # find and display the most recently created CSV results file
        # so the output location is immediately visible during the demo
        results = glob.glob("results/**/*.csv", recursive=True)
        if results:
            latest = max(results, key=os.path.getctime)
            print(f"\nLatest results file: {latest}")
        else:
            print("\nNo CSV results found in results/ directory")

        print("\nDemo complete.")

    # guarantee Flask is terminated even if the experiment runner crashes or times out
    finally:
        print("Stopping Flask application...")
        app_process.terminate()


if __name__ == "__main__":
    main()
    # run this script from the repository root directory with:
    # python demo.py
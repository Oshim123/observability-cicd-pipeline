OBSERVABILITY PIPELINE
Implementing and Evaluating a Monitored CI/CD Workflow on AWS Using CloudWatch and Grafana
==========================================================================================

Student:    Oshim Thakur
Module:     IN3007 — Individual Project
Institution: City, University of London
GitHub:     https://github.com/Oshim123/observability-cicd-pipeline


REQUIREMENTS
------------
- Python 3.10, 3.11, or 3.12 (required)
- pip
- Internet connection (required once for dependency installation)

---------------------
There are TWO ways to run this project:

1) LOCAL DEMO (RECOMMENDED — NO AWS REQUIRED)
2) FULL AWS DEPLOYMENT (OPTIONAL — REQUIRES CLOUD SETUP)


QUICK CHECK (OPTIONAL)


Start the app:

    python app/app.py --port 5000

In another terminal:

    curl http://127.0.0.1:5000/health

Expected response:

    {"status":"healthy"}

Stop the app (Ctrl+C) before running the demo.


===============================================================================
1) LOCAL DEMO (NO AWS REQUIRED) — RECOMMENDED
===============================================================================

Run this for a complete demonstration in ~30–60 seconds (default settings):

    python -m venv venv
    source venv/Scripts/activate  # On Windows use: venv\Scripts\activate
    pip install -r requirements.txt
    python demo.py

WHAT THIS DOES:
- Starts the Flask application locally
- Runs experiment scenarios in sequence:

    CPU:     baseline → fault
    MEMORY:  baseline → fault
    ERROR:   baseline → fault

- Saves results into the results/ folder as a new timestamped directory:

    results/run_<timestamp>/

EXPECTED OUTPUT:
- A new folder appears in results/
- summary.json is generated inside the run folder
- Terminal shows each scenario completing without errors

HOW TO VIEW RESULTS (BASH):

After the demo finishes:

    cd results
    ls

Find the latest run folder (example):

    run_2026-04-11_13-17-52

Enter it:

    cd run_2026-04-11_13-17-52
    ls

You should see:

    baseline/
    cpu/
    memory/
    error/
    summary.json
    app_logs_snapshot.json

To view the summary:

    cat summary.json

This file contains the final metrics used for evaluation.

NOTE:
This mode does NOT use CloudWatch or Grafana.
It exists to reproduce the experiment logic locally.


===============================================================================
2) FULL AWS DEPLOYMENT (OPTIONAL)
===============================================================================

This is the environment used for the dissertation evaluation.

It requires:
- AWS EC2 instance
- CloudWatch configured for logs and metrics
- Grafana dashboard connected to CloudWatch

Full setup instructions are in SETUP.txt.

Quick run steps (if already set up):

1. Connect to EC2:

        ssh -i observability-key.pem ubuntu@<EC2_PUBLIC_IP>
        (for myself ssh -i /c/Users/oshim/Downloads/observability-key.pem ubuntu@<IP> )
2. Pull latest code:

        cd ~/observability-cicd-pipeline
        git pull origin main

3. Set up environment:

        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt

4. Start application:

        nohup venv/bin/python app/app.py >> /var/log/observability-app/app.log 2>&1 &

5. Check health:

        curl http://localhost:5000/health

        Expected:
        {"status":"healthy"}

6. Run experiments:

        python scripts/experiment_runner.py \
          --base-url http://127.0.0.1:5000 \
          --requests 50 \
          --duration 15 \
          --repeats 1 \
          --results-dir results/run_marker

7. View results:

        cat results/run_marker/summary.json

In this mode:
- CloudWatch collects logs and system metrics
- Grafana visualises behaviour and anomalies

OBSERVING RESULTS (AWS)

CloudWatch Logs:
- Go to CloudWatch → Logs → Log groups
- Open the observability log group
- View live request logs during experiments

CloudWatch Metrics:
- Go to CloudWatch → Metrics → EC2
- Observe CPU and memory metrics during fault scenarios

Grafana:
- Open Grafana dashboard (http://<EC2_IP>:3000)
- View real-time visualisation of system behaviour
 


===============================================================================
PROJECT OVERVIEW
===============================================================================

Modern systems often detect failures only after users are affected.
This project investigates whether observability tools can detect issues earlier
through logs, metrics, and visualisation.

A Flask application is deployed via CI/CD (GitHub Actions) to AWS EC2.
CloudWatch collects logs and system metrics.
Grafana visualises them in real time.

Controlled fault injection experiments (CPU stress, memory pressure, and error
scenarios) are used to evaluate how clearly and quickly failures are detected.

The dissertation analysis and results are based on the AWS deployment.
The local demo exists only for reproducibility.


===============================================================================
EXPERIMENT OUTPUT
===============================================================================

Each run produces:

    results/run_<timestamp>/
        baseline/
        cpu/
        memory/
        error/
        summary.json
        metadata.json
        logs.txt

summary.json structure:

    summary["cpu"]["baseline"]
    summary["cpu"]["fault"]
    summary["memory"]["baseline"]
    summary["memory"]["fault"]
    summary["error"]["baseline"]
    summary["error"]["fault"]

Each block contains:
    - runs
    - mean_latency_ms
    - std_dev_latency_ms
    - p95_latency_ms
    - error_rate_percent


===============================================================================
FLASK ENDPOINTS
===============================================================================

    /              GET   Returns HTTP 200
    /health        GET   Returns {"status":"healthy"}
    /trigger-error GET   Returns HTTP 500
    /slow          GET   Delay controlled by SLOW_SECONDS (default ~5 seconds)
    /unstable      GET   Pseudo-random success/failure (seeded via UNSTABLE_SEED)


===============================================================================
REPOSITORY STRUCTURE
===============================================================================

    app/app.py                      Flask application
    scripts/cpu_stress.py           CPU fault injection
    scripts/memory_stress.py        Memory fault injection
    scripts/load_test.py            HTTP load tester
    scripts/experiment_runner.py    Automated experiment orchestration
    scripts/alert.py                CloudWatch alarm checks
    scripts/run_smoke_tests.sh      Endpoint smoke tests
    demo.py                         Local reproducibility runner
    requirements.txt                Python dependencies
    SETUP.txt                       Full AWS + CloudWatch + Grafana setup guide
    results/                        Experiment output artifacts
    docs/                           Architecture diagrams and screenshots



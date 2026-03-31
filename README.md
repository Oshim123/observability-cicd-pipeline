OBSERVABILITY PIPELINE
Implementing and Evaluating a Monitored CI/CD Workflow on AWS Using CloudWatch and Grafana
================================================================

Student:    Oshim Thakur
Module:     IN3007 — Individual Project
Institute:  City, University of London
GitHub:     https://github.com/Oshim123/observability-cicd-pipeline


OVERVIEW
--------
This project implements and evaluates a monitored CI/CD pipeline on AWS. A Flask
application is deployed automatically via GitHub Actions to an EC2 instance.
CloudWatch collects system metrics and logs. Grafana visualises them in real time.
Controlled fault injection experiments — CPU stress, memory stress, and error
injection — are then run to evaluate how quickly and clearly the observability
stack detects abnormal behaviour.

The dissertation results are based on the full AWS deployment. The local demo
exists only as a reproducibility aid for markers without AWS access.

Full setup instructions are in SETUP.txt.


RUNNING LOCALLY (NO AWS REQUIRED)
----------------------------------
To verify the project works without any AWS setup:

        pip install -r requirements.txt
        python demo.py

This runs all four experiment phases locally and writes results to results/.
It does not interact with CloudWatch or Grafana.


QUICK START (AWS ENVIRONMENT ALREADY RUNNING)
----------------------------------------------
If the EC2 instance is already provisioned and running:

    1. Connect to the instance:

            ssh -i observability-key.pem ubuntu@<EC2_PUBLIC_IP>

    2. Navigate to the project and pull the latest code:

            cd ~/observability-cicd-pipeline
            git pull origin main

    3. Activate the environment:

            python3 -m venv venv
            source venv/bin/activate
            pip install -r requirements.txt

    4. Start the Flask application:

            nohup venv/bin/python app/app.py >> /var/log/observability-app/app.log 2>&1 &

    5. Confirm the application is running:

            curl http://localhost:5000/health

            Expected response: {"status":"healthy"}

    6. Run all experiments:

            python scripts/experiment_runner.py \
              --base-url http://127.0.0.1:5000 \
              --requests 100 \
              --duration 60 \
              --results-dir results/run_marker

    7. View the results summary:

            cat results/run_marker/summary.json


EXPERIMENT OUTPUT
-----------------
Every run produces a timestamped folder:

    results/run_<timestamp>/
        baseline/         — baseline CSV files for each scenario/run
        cpu/              — CPU fault CSV files by run
        memory/           — memory fault CSV files by run
        error/            — trigger-error fault CSV files by run
        summary.json      — success flag + per-scenario baseline vs fault aggregates
        metadata.json     — run configuration (requests, duration, repeats, base URL)
        logs.txt          — phase markers + captured stdout/stderr

summary.json structure:
    summary["cpu"]["baseline"] and summary["cpu"]["fault"]
    summary["memory"]["baseline"] and summary["memory"]["fault"]
    summary["error"]["baseline"] and summary["error"]["fault"]

Each baseline/fault block contains:
    - runs
    - mean_latency_ms
    - std_dev_latency_ms
    - p95_latency_ms
    - error_rate_percent


FLASK ENDPOINTS
---------------
    /              GET   Returns HTTP 200
    /health        GET   Returns {"status":"healthy"}
    /trigger-error GET   Returns HTTP 500
    /slow          GET   Returns HTTP 200 after ~5 second delay
    /unstable      GET   Returns HTTP 200 or 500 at random


REPOSITORY STRUCTURE
--------------------
    app/app.py                      Flask application
    scripts/cpu_stress.py           CPU fault injection
    scripts/memory_stress.py        Memory fault injection
    scripts/load_test.py            HTTP load tester
    scripts/experiment_runner.py    Automated experiment orchestration
    scripts/alert.py                Programmatic CloudWatch alarm checks
    scripts/run_smoke_tests.sh      Endpoint smoke tests
    demo.py                         Local reproducibility runner
    requirements.txt                Python dependencies
    SETUP.txt                       Full AWS + CloudWatch + Grafana setup guide
    results/                        All experiment output artifacts
    docs/                           Architecture diagrams and screenshots


DISSERTATION MAPPING
--------------------
    Baseline         — Normal system behaviour       (Section 4.1)
    CPU fault        — Performance degradation        (Section 4.2)
    Memory fault     — Resource pressure              (Section 4.3)
    Error injection  — Failure detection              (Section 4.4)


LIMITATIONS
-----------
- CloudWatch metric ingestion operates on a one-minute polling interval, which
  introduces inherent delay between fault onset and alarm evaluation.
- All experiments were conducted on a t2.micro instance; resource constraints
  may amplify observed effects compared to production-grade hardware.
- Fault injection is synthetic and does not replicate all real-world failure modes.
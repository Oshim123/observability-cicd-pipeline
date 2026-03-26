# The Observability Pipeline: Implementing and Evaluating a Monitored CI/CD Workflow on AWS Using CloudWatch and Grafana

**Student:** Oshim Thakur | **Module:** IN3007 | **Institution:** City, University of London

---

## What This Project Does

Deploys a Flask web application to AWS EC2, monitors it using Amazon CloudWatch and Grafana, and runs controlled fault injection experiments to evaluate how effectively observability tools detect post-deployment failures.

**The full system requires AWS.** If you do not have AWS credentials, use the one-command local demo below.

---

## Repository Structure

```text
app/app.py                          Flask application
scripts/cpu_stress.py               CPU fault injection script
scripts/memory_stress.py            Memory fault injection script
scripts/load_test.py                HTTP load testing script
scripts/alert.py                    Programmatic CloudWatch alerting (AWS required)
scripts/experiment_runner.py        Automated experiment orchestration
demo.py                             Local experiment runner (server + experiments)
run_demo.py                         One-command bootstrap (creates venv, installs deps, runs demo)
run_demo.sh                         Shell wrapper for run_demo.py
requirements.txt                    Python dependencies
results/                            Experiment outputs
SETUP.txt                           Full AWS setup instructions
```

---

## Option A — One-command local demo (recommended)

From repository root:

```bash
./run_demo.sh
```

This command:

1. Creates `.venv` automatically if missing.
2. Installs dependencies from `requirements.txt`.
3. Starts Flask on port 5000 (or next free port automatically).
4. Waits for `/health` with retry logging (up to 30 seconds).
5. Runs baseline + CPU + memory + HTTP 500 tests.
6. Prints pass/fail status and exact results folder.
7. Stops Flask cleanly.

### Expected output example

```text
=== Starting Observability Demo ===
=== Pre-flight Validation ===
✅ Environment checks passed
=== Starting Flask Server ===
=== Waiting for Flask Server ===
Waiting for server... (attempt 1)
Server ready
=== Running Experiment Pipeline ===
=== Running Baseline Test ===
=== Running CPU Stress Test ===
=== Running Memory Stress Test ===
=== Running HTTP 500 Error Test ===
✅ All experiments completed successfully
=== Results Summary ===
baseline: avg latency=2.11 ms, error rate=0.0%
cpu: avg latency=4.82 ms, error rate=0.0%
memory: avg latency=6.15 ms, error rate=0.0%
trigger_error: avg latency=2.07 ms, error rate=100.0%
Results saved to: results/run_YYYYMMDD_HHMMSS
```

### Expected results folder structure

```text
results/run_<timestamp>/
  summary.json
  logs.txt
  baseline.csv
  cpu.csv
  memory.csv
  error.csv
  baseline_load_test.txt
  cpu_load_test.txt
  memory_load_test.txt
  trigger_error_load_test.txt
  cpu_stress_output.txt
  memory_stress_output.txt
```

---

## Option B — Full AWS system (requires AWS account)

For CloudWatch + Grafana + CI/CD deployment details, follow `SETUP.txt`.

---

## Flask Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Root endpoint — HTTP 200 |
| `/health` | Health check — returns `{"status":"healthy"}` |
| `/trigger-error` | Deliberately returns HTTP 500 |
| `/slow` | Responds after ~5 second delay |
| `/unstable` | Randomly returns 200 or 500 |

---

## Manual Experiment Commands (optional)

```bash
# Start app manually
python app/app.py --port 5000

# Run all experiments against running app
python scripts/experiment_runner.py --base-url http://127.0.0.1:5000 --requests 100 --duration 60
```

---

## GitHub Repository

https://github.com/Oshim123/observability-cicd-pipeline

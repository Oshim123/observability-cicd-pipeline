# The Observability Pipeline: Implementing and Evaluating a Monitored CI/CD Workflow on AWS Using CloudWatch and Grafana

**Student:** Oshim Thakur | **Module:** IN3007 | **Institution:** City, University of London

---

## Run the project (for markers)

```bash
python demo.py
```

This project tests how well monitoring tools detect system failures. It runs controlled experiments (CPU, memory, errors) and shows how observability reacts.

---

## Expected Outcome

After running:
- CSV files with experiment results
- A `summary.json` with metrics
- Logs showing system behaviour

You should see:
- Higher latency during CPU/memory stress
- Increased errors during fault injection

---

## Results Output (per run)

All outputs are written to one folder:

```
results/run_<timestamp>/
    baseline.csv
    cpu.csv
    memory.csv
    error.csv
    summary.json
    logs.txt
```

| File | Description |
|------|-------------|
| `baseline.csv` | Load test under normal conditions |
| `cpu.csv` | Load test while CPU stress is active |
| `memory.csv` | Load test while memory stress is active |
| `error.csv` | Load test against `/trigger-error` |
| `summary.json` | Aggregated metrics and overall success flag |
| `logs.txt` | Consolidated run logs and command outputs |

---

## Verifying Results

Open `summary.json` and check:
- CPU experiment has higher latency than baseline
- Error experiment shows non-zero error rate

---

## How this relates to the report

| Experiment | Dissertation section |
|------------|---------------------|
| Baseline | Normal system behaviour |
| CPU | Performance degradation |
| Memory | Resource pressure |
| Error | Application failure |

These are analysed in the Results and Evaluation chapters.

---

## Reproducibility

The local demo allows full reproduction of experiments without AWS. All results are generated automatically and saved per run.

---

## Limitations

- CloudWatch delays may affect detection timing
- Experiments run on t2.micro (limited resources)
- Synthetic faults may differ from real-world failures

---

## Repository Structure

```
app/app.py                          Flask application
scripts/cpu_stress.py               CPU fault injection script
scripts/memory_stress.py            Memory fault injection script
scripts/load_test.py                HTTP load testing script
scripts/alert.py                    Programmatic CloudWatch alerting (AWS required)
scripts/experiment_runner.py        Automated experiment orchestration
demo.py                             Local experiment runner (no AWS needed)
requirements.txt                    Python dependencies
results/                            Experiment outputs
SETUP.txt                           Full AWS setup instructions
```

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

## Manual Experiment Commands

```bash
# Start app manually
python app/app.py

# Run all experiments against running app
python scripts/experiment_runner.py --base-url http://127.0.0.1:5000 --requests 100 --duration 60 --results-dir results/run_manual
```

---

## GitHub Repository

https://github.com/Oshim123/observability-cicd-pipeline
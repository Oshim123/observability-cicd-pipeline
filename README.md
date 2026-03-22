# The Observability Pipeline: Implementing and Evaluating a Monitored CI/CD Workflow on AWS Using CloudWatch and Grafana

**Student:** Oshim Thakur | **Module:** IN3007 | **Institution:** City, University of London

---

## What This Project Does

Deploys a Flask web application to AWS EC2, monitors it using Amazon CloudWatch and Grafana, and runs controlled fault injection experiments to evaluate how effectively observability tools detect post-deployment failures.

**The full system requires an AWS account.** CloudWatch, Grafana, and the CI/CD pipeline all depend on AWS infrastructure. If you do not have AWS credentials, use `demo.py` (see below) to run the application and experiments locally — this demonstrates the core fault injection and load testing functionality without any cloud setup.

---

## Repository Structure

```
app/app.py                          Flask application with logging endpoints
scripts/cpu_stress.py               CPU fault injection script
scripts/memory_stress.py            Memory fault injection script
scripts/load_test.py                HTTP load testing script
scripts/alert.py                    Programmatic CloudWatch alerting (boto3) — requires AWS
scripts/experiment_runner.py        Automated experiment orchestration
demo.py                             Single-command local demo (no AWS needed)
.github/workflows/deploy.yml        GitHub Actions CI/CD pipeline — requires AWS
infrastructure/cloudwatch-agent-config.json   CloudWatch agent configuration — requires AWS
requirements.txt                    Python dependencies
results/                            Experiment CSV outputs and summary
SETUP.txt                           Full installation and deployment instructions
```

---

## Option A — Local Demo (no AWS required)

This runs the Flask application and all fault injection experiments locally. It does not connect to CloudWatch or Grafana, but demonstrates the core application and experiment pipeline working end to end.

```bash
git clone https://github.com/Oshim123/observability-cicd-pipeline.git
cd observability-cicd-pipeline
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python demo.py
```

This starts Flask, waits for it to be ready, runs all experiments automatically, prints results, and shuts down. CSV outputs are saved to `results/`.

---

## Option B — Full System on AWS (requires AWS account)

The complete observability pipeline including CloudWatch metrics, Grafana dashboards, and automated CI/CD deployment requires:

- AWS account (free tier is sufficient)
- EC2 t2.micro instance running Ubuntu 24.04 LTS
- IAM role with `CloudWatchAgentServerPolicy` and `CloudWatchReadOnlyAccess`
- Ports 22, 5000, and 3000 open in the EC2 security group

Full step-by-step instructions for the complete AWS setup are in **SETUP.txt**.

### CI/CD Pipeline

The GitHub Actions workflow deploys automatically on push to `main`. Three secrets must be added to the repository:

| Secret | Value |
|--------|-------|
| `EC2_HOST` | EC2 public IP address |
| `EC2_USERNAME` | `ubuntu` |
| `EC2_SSH_KEY` | Contents of `.pem` key file |

---

## Running Experiments Manually

```bash
# Baseline load test
python scripts/load_test.py http://localhost:5000/health 100

# CPU fault injection (60 seconds)
python scripts/cpu_stress.py 60

# Memory fault injection (60 seconds)
python scripts/memory_stress.py 60

# Run all experiments automatically
python scripts/experiment_runner.py --base-url http://localhost:5000 --requests 100 --duration 60

# Programmatic CloudWatch alerting (requires AWS credentials)
python scripts/alert.py
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

## Monitoring (AWS only)

- **CloudWatch metrics**: `cpu_usage_active` and `mem_used_percent` under namespace `ObservabilityPipeline`
- **CloudWatch logs**: Flask logs streamed to log group `observability-pipeline`
- **Grafana**: Running on port 3000, connected to CloudWatch via IAM role
- **Alarms**: `cpu-high` (>70% for 2 periods), `memory-high` (>75% for 2 periods)

---

## GitHub Repository

https://github.com/Oshim123/observability-cicd-pipeline
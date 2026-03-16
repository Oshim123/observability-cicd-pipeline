# Observability Pipeline: Monitored CI/CD on AWS

BSc Dissertation Project — City, University of London  
**Oshim Thakur | IN3007 | Supervisor: Panos Giannopoulos**

---

## What This Project Does

Deploys a Flask web application to AWS EC2, monitors it using Amazon CloudWatch and Grafana, and runs controlled fault injection experiments to evaluate how effectively observability tools detect post-deployment failures.

---

## Repository Structure

```
app/app.py                          Flask application with logging endpoints
scripts/cpu_stress.py               CPU fault injection script
scripts/memory_stress.py            Memory fault injection script
scripts/load_test.py                HTTP load testing script
scripts/alert.py                    Programmatic CloudWatch alerting (boto3)
scripts/experiment_runner.py        Automated experiment orchestration
.github/workflows/deploy.yml        GitHub Actions CI/CD pipeline
infrastructure/cloudwatch-agent-config.json   CloudWatch agent configuration
requirements.txt                    Python dependencies
results/                            Experiment CSV outputs
```

---

## Requirements

- Python 3.10+
- AWS EC2 t2.micro (Ubuntu 24.04 LTS)
- IAM role with `CloudWatchAgentServerPolicy` and `CloudWatchReadOnlyAccess`
- Ports 22, 5000, 3000 open in security group

---

## Local Setup

```bash
git clone https://github.com/Oshim123/observability-cicd-pipeline.git
cd observability-cicd-pipeline
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app/app.py
```

Test at `http://localhost:5000/health`

---

## EC2 Deployment

The GitHub Actions pipeline deploys automatically on push to `main`. Three secrets are required in the repository settings:

| Secret | Value |
|--------|-------|
| `EC2_HOST` | EC2 public IP address |
| `EC2_USERNAME` | `ubuntu` |
| `EC2_SSH_KEY` | Contents of `.pem` key file |

---

## Running Experiments

```bash
# Baseline
python scripts/load_test.py http://localhost:5000/health 100

# CPU fault injection (60 seconds)
python scripts/cpu_stress.py 60

# Memory fault injection (60 seconds)
python scripts/memory_stress.py 60

# Run all experiments automatically
python scripts/experiment_runner.py --base-url http://localhost:5000 --requests 100 --duration 60

# Programmatic CloudWatch alerting
python scripts/alert.py
```

---

## Flask Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Root endpoint |
| `/health` | Health check — returns `{"status":"healthy"}` |
| `/trigger-error` | Deliberately returns HTTP 500 |
| `/slow` | Responds after ~5 second delay |
| `/unstable` | Randomly returns 200 or 500 |

---

## Monitoring

- **CloudWatch metrics**: `cpu_usage_active` and `mem_used_percent` under namespace `ObservabilityPipeline`
- **CloudWatch logs**: Flask logs streamed to log group `observability-pipeline`
- **Grafana**: Running on port 3000, connected to CloudWatch via IAM role
- **Alarms**: `cpu-high` (>70% for 2 periods), `memory-high` (>75% for 2 periods)

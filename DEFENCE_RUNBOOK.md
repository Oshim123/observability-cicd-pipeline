# Defence Runbook (Copy/Paste)

This file is intentionally command-focused so you can run the full flow during viva/defence without memorising steps.

---

## A) EC2 + App + Experiments (Core Demo)

```bash
# SSH
ssh -i observability-key.pem ubuntu@<EC2_PUBLIC_IP>

# Project
cd ~/observability-cicd-pipeline
git pull origin main

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start app
nohup venv/bin/python app/app.py >> /var/log/observability-app/app.log 2>&1 &

# Health check
curl http://localhost:5000/health

# Run reproducible experiments
python scripts/experiment_runner.py --base-url http://127.0.0.1:5000 --requests 100 --duration 60 --results-dir results/run_defence

# Show headline outputs
cat results/run_defence/summary.json
ls -lah results/run_defence
```

---

## B) CloudWatch Agent (if not already active)

```bash
# Install agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i amazon-cloudwatch-agent.deb

# Place config (copy repo config file contents into target path)
sudo nano /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

# Start agent with config
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Verify
sudo systemctl status amazon-cloudwatch-agent
```

---

## C) Grafana (if not already installed)

```bash
sudo apt-get install -y apt-transport-https software-properties-common
sudo wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key
echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install grafana -y
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

Open:
- `http://<EC2_PUBLIC_IP>:3000`
- login: `admin / admin`

Then configure CloudWatch datasource in region `eu-west-2`.

---

## D) CI/CD Trigger (optional during defence)

```bash
# On your local machine with repo checked out
git add .
git commit -m "defence pipeline trigger"
git push origin main
```

Then show Actions tab and deployment logs.

---

## E) Common Recovery Commands

```bash
# If app appears down
fuser -k 5000/tcp 2>/dev/null || true
nohup venv/bin/python app/app.py >> /var/log/observability-app/app.log 2>&1 &

# Check app logs
tail -n 100 /var/log/observability-app/app.log

# Re-check health
curl http://localhost:5000/health
```

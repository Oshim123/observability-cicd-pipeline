# Observability-Driven CI/CD Pipeline

Dissertation project: Deploy Flask app to EC2, monitor with CloudWatch, measure detection latency.

## Quick Start (6 Hours)

### 1. Launch EC2
- AMI: Ubuntu 22.04 LTS, t2.micro
- Security: Allow SSH (22) and Flask (5000) from your IP
- Copy public IP

### 2. Deploy App
```bash
ssh -i key.pem ubuntu@<IP>
sudo apt update && sudo apt install -y python3 python3-pip git
git clone https://github.com/Oshim123/observability-cicd-pipeline.git
cd observability-cicd-pipeline/app
pip3 install flask && python3 app.py
```
Test: `http://<IP>:5000/` and `http://<IP>:5000/health`

### 3. Install CloudWatch Agent
```bash
sudo apt install -y amazon-cloudwatch-agent
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
# Select: CPU, Memory, /var/log/syslog
sudo systemctl enable amazon-cloudwatch-agent && sudo systemctl start amazon-cloudwatch-agent
```

### 4. Create Alarm
CloudWatch console:
- Metric: CPUUtilization > 70%
- Period: 1 minute, Evaluation: 2 periods

### 5. Test Fault Injection
```bash
cd ~/observability-cicd-pipeline/scripts
python3 cpu_stress.py 30
```
Note CPU spike time and alarm trigger time in CloudWatch. Calculate detection delay.

### 6. Screenshot & Document
- Baseline CPU graph
- CPU graph during stress
- Alarm configuration and triggered state
- Write: "During CPU stress, utilization rose from X% to Y%, alarm triggered after Z seconds."

## Troubleshooting
- App not reachable: Check security group allows TCP 5000
- No metrics: Confirm agent running (`sudo systemctl status amazon-cloudwatch-agent`)
- Alarm won't trigger: Lower threshold to 50% to test wiring

## Done When
✅ Flask accessible at EC2 IP:5000  
✅ CloudWatch shows metrics  
✅ Alarm triggers during CPU stress

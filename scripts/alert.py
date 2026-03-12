import boto3
from datetime import datetime, timezone, timedelta
import time

# Connect to CloudWatch in the correct region using the EC2 instance IAM role.
# boto3 automatically picks up credentials from the instance metadata,
# so no access keys are needed.
client = boto3.client('cloudwatch', region_name='eu-west-2')

# Define the thresholds that will trigger an alert.
# These mirror the CloudWatch alarm thresholds configured in the console,
# allowing programmatic alerting without relying solely on the AWS alarm system.
CPU_THRESHOLD = 70.0
MEMORY_THRESHOLD = 75.0

# Define how far back to look when querying metrics.
# 10 minutes ensures at least one CloudWatch data point is captured,
# since the agent collects metrics every 60 seconds.
LOOKBACK_MINUTES = 10

# The CPU metric requires two dimensions to match exactly how the
# CloudWatch agent registers it: host and cpu.
# The memory metric only requires the host dimension.
CPU_DIMENSIONS = [
    {'Name': 'host', 'Value': 'ip-172-31-35-161'},
    {'Name': 'cpu', 'Value': 'cpu-total'}
]

MEMORY_DIMENSIONS = [
    {'Name': 'host', 'Value': 'ip-172-31-35-161'}
]


def get_latest_metric(metric_name, dimensions, namespace='ObservabilityPipeline'):
    """
    Query CloudWatch for the most recent average value of a given metric.
    Returns the latest datapoint value, or None if no data is available.
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=LOOKBACK_MINUTES)

    response = client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=dimensions,
        StartTime=start_time,
        EndTime=end_time,
        Period=300,
        Statistics=['Average']
    )

    datapoints = response.get('Datapoints', [])

    if not datapoints:
        return None

    latest = sorted(datapoints, key=lambda x: x['Timestamp'])[-1]
    return latest['Average']


def check_and_alert():
    """
    Check both CPU and memory metrics against their thresholds.
    Log an alert message if either metric exceeds its threshold.
    """
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    cpu_value = get_latest_metric('cpu_usage_active', CPU_DIMENSIONS)
    memory_value = get_latest_metric('mem_used_percent', MEMORY_DIMENSIONS)

    print(f"\n[{timestamp}] Checking metrics...")

    if cpu_value is not None:
        print(f"  CPU usage:    {cpu_value:.2f}% (threshold: {CPU_THRESHOLD}%)")
        if cpu_value > CPU_THRESHOLD:
            print(f"  *** ALERT: CPU usage {cpu_value:.2f}% exceeds threshold {CPU_THRESHOLD}% ***")
    else:
        print(f"  CPU usage:    No data available in last {LOOKBACK_MINUTES} minutes")

    if memory_value is not None:
        print(f"  Memory usage: {memory_value:.2f}% (threshold: {MEMORY_THRESHOLD}%)")
        if memory_value > MEMORY_THRESHOLD:
            print(f"  *** ALERT: Memory usage {memory_value:.2f}% exceeds threshold {MEMORY_THRESHOLD}% ***")
    else:
        print(f"  Memory usage: No data available in last {LOOKBACK_MINUTES} minutes")

    if cpu_value is not None and memory_value is not None:
        if cpu_value <= CPU_THRESHOLD and memory_value <= MEMORY_THRESHOLD:
            print("  Status: All metrics within normal range.")


def run_alerting_loop(interval_seconds=60, cycles=5):
    """
    Run the alerting check repeatedly at a fixed interval.
    """
    print(f"Starting observability alerting script.")
    print(f"Polling every {interval_seconds}s for {cycles} cycles.")
    print(f"Thresholds — CPU: {CPU_THRESHOLD}%, Memory: {MEMORY_THRESHOLD}%")
    print("-" * 60)

    for i in range(cycles):
        check_and_alert()

        if i < cycles - 1:
            print(f"  Next check in {interval_seconds} seconds...")
            time.sleep(interval_seconds)

    print("\nAlerting script complete.")


if __name__ == '__main__':
    run_alerting_loop()
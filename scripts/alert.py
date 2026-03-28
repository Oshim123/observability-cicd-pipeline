import argparse
import boto3
import os
from datetime import datetime, timezone, timedelta
import time

# the alerting script queries CloudWatch metrics programmatically using boto3.
# environment-specific values are configurable via CLI arguments or environment
# variables so the script is portable across different EC2 instances and regions.

def parse_args():
    parser = argparse.ArgumentParser(description="Poll CloudWatch metrics and alert on threshold breaches")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "eu-west-2"), help="AWS region")
    parser.add_argument("--namespace", default=os.getenv("CW_NAMESPACE", "ObservabilityPipeline"), help="CloudWatch namespace")
    parser.add_argument("--host", default=os.getenv("CW_HOST_DIMENSION", "ip-172-31-35-161"), help="Host dimension value")
    parser.add_argument("--cpu-threshold", type=float, default=70.0, help="CPU alert threshold percent")
    parser.add_argument("--memory-threshold", type=float, default=75.0, help="Memory alert threshold percent")
    parser.add_argument("--cycles", type=int, default=5, help="Number of polling cycles")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between cycles")
    parser.add_argument("--lookback", type=int, default=10, help="Minutes of metric history to query")
    return parser.parse_args()


def get_latest_metric(client, metric_name, dimensions, namespace, lookback_minutes):
    # query CloudWatch for the most recent average value of a given metric.
    # returns the latest datapoint value, or None if no data is available.
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=lookback_minutes)

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


def check_and_alert(client, args):
    # check both CPU and memory metrics against their thresholds.
    # the CPU metric requires both host and cpu dimensions to match how
    # the CloudWatch agent registers it. memory only needs host.
    cpu_dimensions = [
        {'Name': 'host', 'Value': args.host},
        {'Name': 'cpu', 'Value': 'cpu-total'}
    ]

    memory_dimensions = [
        {'Name': 'host', 'Value': args.host}
    ]

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    cpu_value = get_latest_metric(client, 'cpu_usage_active', cpu_dimensions, args.namespace, args.lookback)
    memory_value = get_latest_metric(client, 'mem_used_percent', memory_dimensions, args.namespace, args.lookback)

    print(f"\n[{timestamp}] Checking metrics...")

    if cpu_value is not None:
        print(f"  CPU usage:    {cpu_value:.2f}% (threshold: {args.cpu_threshold}%)")
        if cpu_value > args.cpu_threshold:
            print(f"  *** ALERT: CPU usage {cpu_value:.2f}% exceeds threshold {args.cpu_threshold}% ***")
    else:
        print(f"  CPU usage:    No data available in last {args.lookback} minutes")

    if memory_value is not None:
        print(f"  Memory usage: {memory_value:.2f}% (threshold: {args.memory_threshold}%)")
        if memory_value > args.memory_threshold:
            print(f"  *** ALERT: Memory usage {memory_value:.2f}% exceeds threshold {args.memory_threshold}% ***")
    else:
        print(f"  Memory usage: No data available in last {args.lookback} minutes")

    if cpu_value is not None and memory_value is not None:
        if cpu_value <= args.cpu_threshold and memory_value <= args.memory_threshold:
            print("  Status: All metrics within normal range.")


def run_alerting_loop(args):
    # boto3 picks up credentials from the EC2 instance IAM role automatically
    # so no access keys are needed when running on EC2
    client = boto3.client('cloudwatch', region_name=args.region)

    print(f"Starting observability alerting script.")
    print(f"Region: {args.region} | Namespace: {args.namespace} | Host: {args.host}")
    print(f"Polling every {args.interval}s for {args.cycles} cycles.")
    print(f"Thresholds — CPU: {args.cpu_threshold}%, Memory: {args.memory_threshold}%")
    print("-" * 60)

    for i in range(args.cycles):
        check_and_alert(client, args)

        if i < args.cycles - 1:
            print(f"  Next check in {args.interval} seconds...")
            time.sleep(args.interval)

    print("\nAlerting script complete.")


if __name__ == '__main__':
    run_alerting_loop(parse_args())
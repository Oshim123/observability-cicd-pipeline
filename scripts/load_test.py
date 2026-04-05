import argparse
import csv
import json
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
#these imports lets us see warnings from requests library, such as InsecureRequestWarning when making requests to HTTPS endpoints without proper certificates

def parse_args():
    parser = argparse.ArgumentParser(description="Run HTTP load test and save detailed CSV results")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("number_of_requests", type=int, help="Number of HTTP requests to send")
    parser.add_argument("--output-csv", default=None, help="Destination CSV file")
    parser.add_argument("--summary-json", default=None, help="Optional destination JSON file")
    parser.add_argument("--scenario", default="unknown", help="Scenario label for traceability")#decided to use this argument to allow users to specify a scenario label for traceability, which can be helpful when analyzing results from multiple load tests or comparing different scenarios.
    parser.add_argument("--run-id", default="run0", help="Run identifier for traceability")
    parser.add_argument("--pace-ms", type=int, default=50, help="Delay between requests")
    parser.add_argument("--timeout", type=float, default=5.0, help="Request timeout in seconds")
    return parser.parse_args()
#this parser allows us to specify the target URL, number of requests, output CSV file, optional summary JSON file, scenario 
# and run identifiers for traceability, pacing between requests, and request timeout. 
# It provides a flexible way to configure the load test parameters when running the script from the command line.

def percentile(values, pct):
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0] #function to calculate the specified percentile from a list of values.
    #It basically sorts the values and then uses a weighted average to find the percentile value based on the index calculated from the percentage.
    values_sorted = sorted(values)
    idx = (len(values_sorted) - 1) * pct
    low = int(idx)
    high = min(low + 1, len(values_sorted) - 1)
    weight = idx - low
    return values_sorted[low] * (1 - weight) + values_sorted[high] * weight
    #This function is used to calculate the 95th percentile latency in the load test results, which is a common metric for understanding the performance of a system under load. 
    # It handles edge cases such as an empty list of values or a single value, ensuring that it returns meaningful results in those scenarios.

def main():
    args = parse_args()
    if args.number_of_requests <= 0:
        raise ValueError("number_of_requests must be > 0")
#this check ensures that the number of requests specified is a positive integer, If the value is zero or negative,
# it raises a ValueError with a clear message, preventing the script from executing with invalid parameters.
    if args.output_csv:
        csv_path = Path(args.output_csv)
    else:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        csv_path = Path(f"load_test_results_{timestamp}.csv")
#this args.output_csv allows users to specify a custom path for the output CSV file.
# If not provided, it generates a default filename based on the current UTC timestamp, 
# so basically ensures that the results are saved in a structured way.
    csv_path.parent.mkdir(parents=True, exist_ok=True) #lets you create the parent directories for the CSV file if they don't already exist

    latencies = []
    status_counts = {}
    error_count = 0

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = [
            "timestamp_utc",
            "request_number",
            "request_id",
            "scenario",
            "run_id",
            "latency_ms",
            "status_code",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(args.number_of_requests):
            request_id = str(uuid.uuid4())
            start_time = time.time()
            timestamp_utc = datetime.now(timezone.utc).isoformat()
            headers = {
                "X-Request-Id": request_id,
                "X-Scenario": args.scenario,
                "X-Run-Id": args.run_id,
            }
            try:
                response = requests.get(args.url, timeout=args.timeout, headers=headers)
                status_code = response.status_code
            except requests.exceptions.RequestException as exc:
                status_code = "ERROR"
                print(f"Request {i + 1} failed: {exc}")

            latency = (time.time() - start_time) * 1000
            latencies.append(latency)
            status_counts[str(status_code)] = status_counts.get(str(status_code), 0) + 1
            if str(status_code).startswith("5") or status_code == "ERROR":
                error_count += 1

            writer.writerow(
                {
                    "timestamp_utc": timestamp_utc,
                    "request_number": i + 1,
                    "request_id": request_id,
                    "scenario": args.scenario,
                    "run_id": args.run_id,
                    "latency_ms": round(latency, 3),
                    "status_code": status_code,
                }
            )
            time.sleep(args.pace_ms / 1000.0)

    summary = {
        "url": args.url,
        "scenario": args.scenario,
        "run_id": args.run_id,
        "requests": args.number_of_requests,
        "mean_latency_ms": round(statistics.mean(latencies), 3),
        "median_latency_ms": round(statistics.median(latencies), 3),
        "std_dev_latency_ms": round(statistics.pstdev(latencies), 3),
        "minimum_latency_ms": round(min(latencies), 3),
        "maximum_latency_ms": round(max(latencies), 3),
        "p95_latency_ms": round(percentile(latencies, 0.95), 3),
        "status_code_distribution": status_counts,
        "error_rate_percent": round((error_count / args.number_of_requests) * 100, 3),
        "csv_file": str(csv_path),
    }

    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

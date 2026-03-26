import argparse
import csv
import json
import statistics
import time
from datetime import datetime
from pathlib import Path

import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Run HTTP load test and save detailed CSV results")
    parser.add_argument("url", help="Target URL")
    parser.add_argument("number_of_requests", type=int, help="Number of HTTP requests to send")
    parser.add_argument(
        "--output-csv",
        default=None,
        help="Destination CSV file. If omitted, creates load_test_results_<timestamp>.csv in CWD.",
    )
    parser.add_argument(
        "--summary-json",
        default=None,
        help="Optional destination JSON file for summary metrics.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.output_csv:
        csv_path = Path(args.output_csv)
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        csv_path = Path(f"load_test_results_{timestamp}.csv")

    csv_path.parent.mkdir(parents=True, exist_ok=True)

    latencies = []
    status_counts = {}

    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        fieldnames = ["Request Number", "Latency (ms)", "Status Code"]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(args.number_of_requests):
            start_time = time.time()
            try:
                response = requests.get(args.url, timeout=5)
                status_code = response.status_code
            except requests.exceptions.RequestException as exc:
                status_code = "ERROR"
                print(f"Request {i + 1} failed: {exc}")

            end_time = time.time()
            latency = (end_time - start_time) * 1000
            latencies.append(latency)
            status_counts[status_code] = status_counts.get(status_code, 0) + 1

            writer.writerow(
                {
                    "Request Number": i + 1,
                    "Latency (ms)": latency,
                    "Status Code": status_code,
                }
            )
            time.sleep(0.05)

    avg_latency = statistics.mean(latencies) if latencies else 0.0
    min_latency = min(latencies) if latencies else 0.0
    max_latency = max(latencies) if latencies else 0.0

    total_errors = sum(
        count for code, count in status_counts.items() if str(code).startswith("5") or code == "ERROR"
    )
    error_rate = (total_errors / args.number_of_requests * 100) if args.number_of_requests else 0.0

    summary = {
        "url": args.url,
        "requests": args.number_of_requests,
        "average_latency_ms": round(avg_latency, 2),
        "minimum_latency_ms": round(min_latency, 2),
        "maximum_latency_ms": round(max_latency, 2),
        "status_code_distribution": status_counts,
        "error_rate_percent": round(error_rate, 2),
        "csv_file": str(csv_path),
    }

    if args.summary_json:
        summary_path = Path(args.summary_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n--- Load Test Summary ---")
    print(f"Total Requests: {args.number_of_requests}")
    print(f"Average Latency: {avg_latency:.2f} ms")
    print(f"Minimum Latency: {min_latency:.2f} ms")
    print(f"Maximum Latency: {max_latency:.2f} ms")
    print(f"Error Rate: {error_rate:.2f}%")
    print(f"Status Code Distribution: {status_counts}")
    print(f"CSV Output: {csv_path}")


if __name__ == "__main__":
    main()

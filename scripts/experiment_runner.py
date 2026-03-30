import argparse
import json
import os
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "2.1"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def run_command(command):
    return subprocess.run(command, capture_output=True, text=True)


def aggregate_run_metrics(metrics_list):
    if not metrics_list:
        return {}

    def metric_mean(key):
        values = [m.get(key) for m in metrics_list if m.get(key) is not None]
        return round(statistics.mean(values), 3) if values else None

    return {
        "runs": len(metrics_list),
        "mean_latency_ms": metric_mean("mean_latency_ms"),
        "std_dev_latency_ms": metric_mean("std_dev_latency_ms"),
        "p95_latency_ms": metric_mean("p95_latency_ms"),
        "error_rate_percent": metric_mean("error_rate_percent"),
    }


def run_load_phase(base_url, endpoint, request_count, csv_file, scenario, run_id):
    summary_json_file = csv_file.with_name(f"{csv_file.stem}_summary.json")
    cmd = [
        sys.executable,
        "scripts/load_test.py",
        f"{base_url}{endpoint}",
        str(request_count),
        "--output-csv",
        str(csv_file),
        "--summary-json",
        str(summary_json_file),
        "--scenario",
        scenario,
        "--run-id",
        run_id,
    ]

    result = run_command(cmd)
    metrics = {}
    if summary_json_file.exists():
        metrics = json.loads(summary_json_file.read_text(encoding="utf-8"))
        summary_json_file.unlink()

    return result, metrics


def run_scenario_experiment(base_url, request_count, duration, results_dir, scenario, run_idx, stress_script):
    run_id = f"run{run_idx:02d}"
    baseline_csv = results_dir / "baseline" / f"baseline_{scenario}_{run_id}.csv"
    fault_csv = results_dir / scenario / f"{scenario}_{run_id}.csv"

    baseline_csv.parent.mkdir(parents=True, exist_ok=True)
    fault_csv.parent.mkdir(parents=True, exist_ok=True)

    markers = [f"[START {scenario.upper()} {run_id} BASELINE] {utc_now()}"]
    baseline_result, baseline_metrics = run_load_phase(
        base_url, "/", request_count, baseline_csv, f"{scenario}_baseline", run_id
    )
    markers.append(f"[END {scenario.upper()} {run_id} BASELINE] {utc_now()}")

    markers.append(f"[START {scenario.upper()} {run_id} FAULT] {utc_now()}")
    stress_process = None
    stress_stdout = ""

    if stress_script:
        stress_process = subprocess.Popen(
            [sys.executable, stress_script, str(duration), "--scenario", scenario, "--run-id", run_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    endpoint = "/trigger-error" if scenario == "error" else "/"
    fault_result, fault_metrics = run_load_phase(base_url, endpoint, request_count, fault_csv, scenario, run_id)

    stress_rc = 0
    if stress_process:
        stress_stdout, _ = stress_process.communicate()
        stress_rc = stress_process.returncode

    markers.append(f"[END {scenario.upper()} {run_id} FAULT] {utc_now()}")

    return {
        "run_id": run_id,
        "scenario": scenario,
        "markers": markers,
        "baseline": {"returncode": baseline_result.returncode, "metrics": baseline_metrics, "csv": str(baseline_csv)},
        "fault": {
            "returncode": fault_result.returncode,
            "metrics": fault_metrics,
            "csv": str(fault_csv),
            "stress_returncode": stress_rc,
            "stress_stdout": stress_stdout,
        },
        "load_stdout": {
            "baseline": baseline_result.stdout,
            "baseline_err": baseline_result.stderr,
            "fault": fault_result.stdout,
            "fault_err": fault_result.stderr,
        },
    }


def parse_args():
    parser = argparse.ArgumentParser(description="Run reproducible observability experiments")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Flask base URL")
    parser.add_argument("--requests", type=int, default=100, help="Requests per load test")
    parser.add_argument("--duration", type=int, default=30, help="Stress duration in seconds")
    parser.add_argument("--repeats", type=int, default=5, help="Repeats per scenario")
    parser.add_argument("--results-dir", required=True, help="Explicit results directory")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.requests <= 0 or args.duration <= 0 or args.repeats <= 0:
        raise ValueError("--requests, --duration, and --repeats must all be > 0")

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    all_runs = []
    logs = []

    scenarios = [
        ("cpu", "scripts/cpu_stress.py"),
        ("memory", "scripts/memory_stress.py"),
        ("error", None),
    ]

    for scenario, script in scenarios:
        for run_idx in range(1, args.repeats + 1):
            print(f"Running {scenario} {run_idx}/{args.repeats}")
            run_result = run_scenario_experiment(
                args.base_url,
                args.requests,
                args.duration,
                results_dir,
                scenario,
                run_idx,
                script,
            )
            all_runs.append(run_result)
            logs.extend(run_result["markers"])
            logs.extend(
                [
                    run_result["load_stdout"]["baseline"],
                    run_result["load_stdout"]["baseline_err"],
                    run_result["load_stdout"]["fault"],
                    run_result["load_stdout"]["fault_err"],
                    run_result["fault"]["stress_stdout"],
                ]
            )

    summary = {}
    all_success = True

    for scenario, _ in scenarios:
        scenario_runs = [r for r in all_runs if r["scenario"] == scenario]
        baseline_metrics = [r["baseline"]["metrics"] for r in scenario_runs]
        fault_metrics = [r["fault"]["metrics"] for r in scenario_runs]
        summary[scenario] = {
            "baseline": aggregate_run_metrics(baseline_metrics),
            "fault": aggregate_run_metrics(fault_metrics),
            "detection_latency_seconds": "not_measured",
        }

        for run in scenario_runs:
            if (
                run["baseline"]["returncode"] != 0
                or run["fault"]["returncode"] != 0
                or run["fault"]["stress_returncode"] != 0
            ):
                all_success = False

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": utc_now(),
        "base_url": args.base_url,
        "requests_per_run": args.requests,
        "stress_duration_seconds": args.duration,
        "repeats": args.repeats,
        "instance_type": os.getenv("INSTANCE_TYPE", "unknown"),
    }

    (results_dir / "summary.json").write_text(
        json.dumps({"success": all_success, "summary": summary, "runs": all_runs}, indent=2),
        encoding="utf-8",
    )
    (results_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (results_dir / "logs.txt").write_text("\n".join(logs), encoding="utf-8")

    app_log = Path("/var/log/observability-app/app.log")
    if app_log.exists():
        (results_dir / "app_logs_snapshot.txt").write_text(app_log.read_text(encoding="utf-8"), encoding="utf-8")

    if not all_success:
        print("One or more experiment runs failed. See logs.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()

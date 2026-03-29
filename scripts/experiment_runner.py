import argparse
import json
import subprocess
import sys
from pathlib import Path

SCHEMA_VERSION = "1.0"


def run_command(command):
    return subprocess.run(command, capture_output=True, text=True)


def run_load_phase(target_url, request_count, csv_file):
    summary_json_file = csv_file.with_name(f"{csv_file.stem}_summary.json")
    result = run_command(
        [
            sys.executable,
            "scripts/load_test.py",
            target_url,
            str(request_count),
            "--output-csv",
            str(csv_file),
            "--summary-json",
            str(summary_json_file),
        ]
    )

    metrics = {
        "avg_latency_ms": None,
        "error_rate_percent": None,
        "status_code_distribution": {},
    }

    if result.returncode == 0:
        try:
            summary_payload = json.loads(summary_json_file.read_text(encoding="utf-8"))
            metrics["avg_latency_ms"] = summary_payload.get("average_latency_ms")
            metrics["error_rate_percent"] = summary_payload.get("error_rate_percent")
            metrics["status_code_distribution"] = summary_payload.get("status_code_distribution", {})
        except (OSError, json.JSONDecodeError):
            pass
        finally:
            if summary_json_file.exists():
                summary_json_file.unlink()

    return result, metrics


def run_baseline(base_url, request_count, results_dir):
    csv_file = results_dir / "baseline.csv"
    return run_load_phase(f"{base_url}/", request_count, csv_file), csv_file


def run_fault_experiment(name, stress_script, base_url, request_count, duration_seconds, results_dir):
    csv_file = results_dir / f"{name}.csv"
    stress_process = subprocess.Popen(
        [sys.executable, stress_script, str(duration_seconds)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    load_result, metrics = run_load_phase(f"{base_url}/", request_count, csv_file)
    stress_stdout, _ = stress_process.communicate()

    return {
        "load_result": load_result,
        "stress_return_code": stress_process.returncode,
        "stress_stdout": stress_stdout,
        "metrics": metrics,
        "csv_file": csv_file,
    }


def run_trigger_error_experiment(base_url, request_count, results_dir):
    csv_file = results_dir / "error.csv"
    return run_load_phase(f"{base_url}/trigger-error", request_count, csv_file), csv_file


def main():
    parser = argparse.ArgumentParser(description="Run reproducible observability experiments")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Flask base URL")
    parser.add_argument("--requests", type=int, default=200, help="Requests per load test")
    parser.add_argument("--duration", type=int, default=60, help="Stress duration in seconds")
    parser.add_argument("--results-dir", required=True, help="Explicit results directory")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    logs = []

    print("[2/5] Running baseline test...")
    (baseline_payload, baseline_csv) = run_baseline(args.base_url, args.requests, results_dir)
    baseline_result, baseline_metrics = baseline_payload
    logs.append("=== BASELINE ===")
    logs.append(baseline_result.stdout)
    logs.append(baseline_result.stderr)

    print("[3/5] Running CPU stress test...")
    cpu = run_fault_experiment(
        "cpu", "scripts/cpu_stress.py", args.base_url, args.requests, args.duration, results_dir
    )
    logs.append("=== CPU LOAD ===")
    logs.append(cpu["load_result"].stdout)
    logs.append(cpu["load_result"].stderr)
    logs.append("=== CPU STRESS ===")
    logs.append(cpu["stress_stdout"] or "")

    print("[4/5] Running memory stress test...")
    memory = run_fault_experiment(
        "memory", "scripts/memory_stress.py", args.base_url, args.requests, args.duration, results_dir
    )
    logs.append("=== MEMORY LOAD ===")
    logs.append(memory["load_result"].stdout)
    logs.append(memory["load_result"].stderr)
    logs.append("=== MEMORY STRESS ===")
    logs.append(memory["stress_stdout"] or "")

    print("[5/5] Running error test...")
    (error_payload, error_csv) = run_trigger_error_experiment(args.base_url, args.requests, results_dir)
    error_result, error_metrics = error_payload
    logs.append("=== ERROR LOAD ===")
    logs.append(error_result.stdout)
    logs.append(error_result.stderr)

    summary = {
        "schema_version": "1.0",
        "success": False,
        "summary": {
            "baseline": baseline_metrics,
            "cpu": cpu["metrics"],
            "memory": memory["metrics"],
            "error": error_metrics,
        },
    }

    return_codes_ok = all(
        [
            baseline_result.returncode == 0,
            cpu["load_result"].returncode == 0,
            cpu["stress_return_code"] == 0,
            memory["load_result"].returncode == 0,
            memory["stress_return_code"] == 0,
            error_result.returncode == 0,
        ]
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "success": return_codes_ok,
        "error": None if return_codes_ok else "One or more phases failed. Check logs.txt for details.",
        "base_url": args.base_url,
        "requests_per_phase": args.requests,
        "stress_duration_seconds": args.duration,
        "summary": {
            "baseline": baseline_metrics,
            "cpu": cpu["metrics"],
            "memory": memory["metrics"],
            "error": error_metrics,
        },
    }

    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (results_dir / "logs.txt").write_text("\n".join(logs), encoding="utf-8")

    required_csv = [baseline_csv, cpu["csv_file"], memory["csv_file"], error_csv]
    if not all(path.exists() for path in required_csv):
        print("Required CSV artifact missing")
        sys.exit(1)

    if not return_codes_ok:
        print("Experiment failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

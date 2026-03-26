import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(command, output_file):
    result = subprocess.run(command, capture_output=True, text=True)
    with output_file.open("w", encoding="utf-8") as file_handle:
        file_handle.write(f"$ {' '.join(command)}\n")
        file_handle.write(f"return_code: {result.returncode}\n\n")
        file_handle.write("--- STDOUT ---\n")
        file_handle.write(result.stdout)
        file_handle.write("\n--- STDERR ---\n")
        file_handle.write(result.stderr)
    return result


def run_baseline(base_url, request_count, results_dir):
    print("=== Running Baseline Test ===")
    output_file = results_dir / "baseline_load_test.txt"
    summary_json = results_dir / "baseline_metrics.json"
    csv_file = results_dir / "baseline.csv"

    start_time = datetime.now()
    result = run_command(
        [
            sys.executable,
            "scripts/load_test.py",
            f"{base_url}/",
            str(request_count),
            "--output-csv",
            str(csv_file),
            "--summary-json",
            str(summary_json),
        ],
        output_file,
    )
    end_time = datetime.now()

    return {
        "phase": "baseline",
        "success": result.returncode == 0,
        "error": None if result.returncode == 0 else "Baseline load test failed",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "return_code": result.returncode,
        "csv_file": str(csv_file),
        "metrics_file": str(summary_json),
        "output_file": str(output_file),
    }


def run_fault_experiment(name, stress_script, base_url, request_count, duration_seconds, results_dir):
    label = "CPU" if name == "cpu" else "Memory"
    print(f"=== Running {label} Stress Test ===")

    stress_output = results_dir / f"{name}_stress_output.txt"
    load_output = results_dir / f"{name}_load_test.txt"
    summary_json = results_dir / f"{name}_metrics.json"
    csv_file = results_dir / f"{name}.csv"

    start_time = datetime.now()

    with stress_output.open("w", encoding="utf-8") as stress_log:
        stress_process = subprocess.Popen(
            [sys.executable, stress_script, str(duration_seconds)],
            stdout=stress_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        load_result = run_command(
            [
                sys.executable,
                "scripts/load_test.py",
                f"{base_url}/",
                str(request_count),
                "--output-csv",
                str(csv_file),
                "--summary-json",
                str(summary_json),
            ],
            load_output,
        )
        stress_process.wait()

    end_time = datetime.now()
    success = load_result.returncode == 0 and stress_process.returncode == 0

    return {
        "phase": name,
        "success": success,
        "error": None if success else f"{label} stress phase failed",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "load_test_return_code": load_result.returncode,
        "stress_return_code": stress_process.returncode,
        "csv_file": str(csv_file),
        "metrics_file": str(summary_json),
        "stress_output_file": str(stress_output),
        "load_output_file": str(load_output),
    }


def run_trigger_error_experiment(base_url, request_count, results_dir):
    print("=== Running HTTP 500 Error Test ===")

    output_file = results_dir / "trigger_error_load_test.txt"
    summary_json = results_dir / "error_metrics.json"
    csv_file = results_dir / "error.csv"

    start_time = datetime.now()
    result = run_command(
        [
            sys.executable,
            "scripts/load_test.py",
            f"{base_url}/trigger-error",
            str(request_count),
            "--output-csv",
            str(csv_file),
            "--summary-json",
            str(summary_json),
        ],
        output_file,
    )
    end_time = datetime.now()

    return {
        "phase": "trigger_error",
        "success": result.returncode == 0,
        "error": None if result.returncode == 0 else "Trigger error phase failed",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "return_code": result.returncode,
        "csv_file": str(csv_file),
        "metrics_file": str(summary_json),
        "output_file": str(output_file),
    }


def build_logs_file(results_dir, phases):
    lines = ["Observability Demo Execution Log", ""]
    for phase in phases:
        lines.append(f"phase={phase['phase']} success={phase['success']} error={phase['error']}")
    (results_dir / "logs.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run reproducible observability experiments")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Flask base URL")
    parser.add_argument("--requests", type=int, default=200, help="Requests per load test")
    parser.add_argument("--duration", type=int, default=60, help="Stress duration in seconds")
    parser.add_argument(
        "--results-dir",
        default=None,
        help="Optional explicit results directory. If omitted, uses results/run_<timestamp>",
    )
    args = parser.parse_args()

    if args.results_dir:
        results_dir = Path(args.results_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = Path("results") / f"run_{timestamp}"
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"[runner] Results directory: {results_dir}")

    phases = [
        run_baseline(args.base_url, args.requests, results_dir),
        run_fault_experiment("cpu", "scripts/cpu_stress.py", args.base_url, args.requests, args.duration, results_dir),
        run_fault_experiment("memory", "scripts/memory_stress.py", args.base_url, args.requests, args.duration, results_dir),
        run_trigger_error_experiment(args.base_url, args.requests, results_dir),
    ]

    overall_success = all(phase["success"] for phase in phases)
    failing = [phase["phase"] for phase in phases if not phase["success"]]

    summary = {
        "success": overall_success,
        "error": None if overall_success else f"Failed phases: {', '.join(failing)}",
        "base_url": args.base_url,
        "requests": args.requests,
        "duration_seconds": args.duration,
        "results_dir": str(results_dir),
        "phases": phases,
    }

    summary_file = results_dir / "summary.json"
    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    build_logs_file(results_dir, phases)

    if overall_success:
        print("✅ All experiments completed successfully")
    else:
        print(f"❌ Experiment failed: {', '.join(failing)}")

    print(f"[runner] Summary saved to {summary_file}")
    print(f"[runner] Results saved to: {results_dir}")

    if not overall_success:
        sys.exit(1)


if __name__ == "__main__":
    main()

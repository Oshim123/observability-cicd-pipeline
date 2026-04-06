import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Simplified the aggregate function. 
# Using a manual loop instead of the 'statistics' library and nested functions.
def get_average_metrics(run_list):
    if not run_list:
        return {}

    total_latency = 0
    total_error = 0
    count = 0

    for m in run_list:
        if m.get("mean_latency_ms") is not None:
            total_latency += m.get("mean_latency_ms")
            total_error += m.get("error_rate_percent", 0)
            count += 1
            #this for loop calculates the average latency and error rate across multiple runs of the same scenario.
            # It iterates through each run's metrics, sums up the mean latency and error rates, and counts how many valid runs there are.
    if count == 0:
        return {"runs": 0}
    #if the counts 0 it returns a dict with 0 so we avoid division by zero. Otherwise, it calculates the average latency and error rate by dividing the totals by the count of valid runs
    
    return {
        "runs": count,
        "mean_latency_ms": round(total_latency / count, 3),
        "error_rate_percent": round(total_error / count, 2)
    } #chose to round the latency to 3 decimal places and error rate to 2 decimal places for better readability in the final summary.

def run_load_test(url, requests, csv_file, scenario, run_id):
    # We save a temporary summary file to read the numbers back
    temp_summary = csv_file.with_name("temp_stats.json")
    
    cmd = [
        sys.executable, "scripts/load_test.py", #sys.executable ensures  we use the same Python interpreter to run the load_test script,important for consistency, in virtual environments.
        url, str(requests),
        "--output-csv", str(csv_file),
        "--summary-json", str(temp_summary),
        "--scenario", scenario,
        "--run-id", run_id
    ]
    #this command in short will execute the load_test.py script with the specified parameters, including the target URL, number of requests, output CSV file, summary JSON file, scenario name, and run ID.
    # The load_test.py script is responsible for performing the actual load testing and writing the results to the specified files.
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    metrics = {}
    if temp_summary.exists():
        metrics = json.loads(temp_summary.read_text())
        temp_summary.unlink() # Delete temp file after reading

    return result, metrics

def run_single_experiment(base_url, requests, duration, folder, scenario, idx, stress_script):
    run_id = f"run_{idx}"
    
    # Create folders for baseline and the actual fault test
    base_path = Path(folder) / "baseline"
    fault_path = Path(folder) / scenario
    base_path.mkdir(parents=True, exist_ok=True)
    fault_path.mkdir(parents=True, exist_ok=True)

    baseline_csv = base_path / f"base_{scenario}_{run_id}.csv"
    fault_csv = fault_path / f"fault_{scenario}_{run_id}.csv"

    # 1. Run Baseline (No stress)
    print(f"   -> Running Baseline...")
    base_res, base_metrics = run_load_test(
        base_url + "/", requests, baseline_csv, f"{scenario}_baseline", run_id
    )

    # 2. Start the stress script (CPU or Memory)
    stress_proc = None
    if stress_script:
        print(f"   -> Starting Stress: {scenario}")
        stress_proc = subprocess.Popen([
            sys.executable, stress_script, str(duration), 
            "--scenario", scenario, "--run-id", run_id
        ])

    # 3. Run the test during the stress
    endpoint = "/trigger-error" if scenario == "error" else "/"
    fault_res, fault_metrics = run_load_test(
        base_url + endpoint, requests, fault_csv, scenario, run_id
    )

    # Clean up the stress process if it's running
    if stress_proc:
        stress_proc.wait()

    return {
        "scenario": scenario,
        "baseline": {"metrics": base_metrics, "code": base_res.returncode},
        "fault": {"metrics": fault_metrics, "code": fault_res.returncode}
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--results-dir", required=True)
    args = parser.parse_args()

    out_dir = Path(args.results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    scenarios = [
        ("cpu", "scripts/cpu_stress.py"),
        ("memory", "scripts/memory_stress.py"),
        ("error", None)
    ]

    all_results = []

    for name, script in scenarios:
        for i in range(1, args.repeats + 1):
            print(f"--- Experiment: {name} (Round {i}) ---")
            res = run_single_experiment(
                args.base_url, args.requests, args.duration, out_dir, name, i, script
            )
            all_results.append(res)

    # Group the data to create a final summary
    final_summary = {}
    for name, _ in scenarios:
        s_baseline = [r["baseline"]["metrics"] for r in all_results if r["scenario"] == name]
        s_fault = [r["fault"]["metrics"] for r in all_results if r["scenario"] == name]
        
        final_summary[name] = {
            "baseline": get_average_metrics(s_baseline),
            "fault": get_average_metrics(s_fault)
        }

    # Save final JSON files
    (out_dir / "summary.json").write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "success": True,
        "summary": final_summary,
        "details": all_results
    }, indent=4))

    # Snapshot of our app logs (the file we created in app.py)
    app_log_src = Path("app_logs.json")
    if app_log_src.exists():
        (out_dir / "app_logs_snapshot.json").write_text(app_log_src.read_text())

    print("\nExperiments Finished!")

if __name__ == "__main__":
    main()
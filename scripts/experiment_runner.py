import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Manual loop here to get the average. 
# Avoided the statistics library because it was overkill for just two numbers.
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
            
    if count == 0:
        return {"runs": 0}
    
    # Rounding to 3 decimals so the final JSON report looks clean
    return {
        "runs": count,
        "mean_latency_ms": round(total_latency / count, 3),
        "error_rate_percent": round(total_error / count, 2)
    }

def run_load_test(url, requests, csv_file, scenario, run_id):
    # Using a temp file to pass data between the load test and this script
    temp_summary = csv_file.with_name("temp_stats.json")
    
    cmd = [
        sys.executable, "scripts/load_test.py", 
        url, str(requests),
        "--output-csv", str(csv_file),
        "--summary-json", str(temp_summary),
        "--scenario", scenario,
        "--run-id", run_id
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    metrics = {}
    if temp_summary.exists():
        metrics = json.loads(temp_summary.read_text())
        # Delete temp file after reading so it doesn't clutter the folder
        os.remove(str(temp_summary)) 

    return result, metrics

def run_single_experiment(base_url, requests, duration, folder, scenario, idx, stress_script):
    run_id = "run_" + str(idx) 
    
    # Setting up the subfolders for the results
    base_path = Path(folder) / "baseline"
    fault_path = Path(folder) / scenario
    base_path.mkdir(parents=True, exist_ok=True)
    fault_path.mkdir(parents=True, exist_ok=True)

    baseline_csv = base_path / ("base_" + str(scenario) + "_" + str(run_id) + ".csv")
    fault_csv = fault_path / ("fault_" + str(scenario) + "_" + str(run_id) + ".csv")

    # Step 1: Baseline. This shows how the app performs normally.
    print("Running Baseline test...")
    base_res, base_metrics = run_load_test(
        base_url + "/", requests, baseline_csv, str(scenario) + "_baseline", run_id
    )

    # Step 2: Injection. Launching the stress script in the background.
    stress_proc = None
    if stress_script:
        print("Injecting fault: " + str(scenario))
        stress_proc = subprocess.Popen([
            sys.executable, stress_script, str(duration), 
            "--scenario", scenario, "--run-id", run_id
        ])

    # Step 3: Fault Test. Running load while the system is stressed.
    # The /trigger-error endpoint is only used for the error scenario.
    endpoint = "/trigger-error" if scenario == "error" else "/"
    fault_res, fault_metrics = run_load_test(
        base_url + endpoint, requests, fault_csv, scenario, run_id
    )

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
            print("Running " + str(name) + " experiment round " + str(i))
            res = run_single_experiment(
                args.base_url, args.requests, args.duration, out_dir, name, i, script
            )
            all_results.append(res)

    final_summary = {}
    
    # Manual grouping of results to build the final report
    for name, _ in scenarios:
        s_baseline = []
        s_fault = []
        
        for r in all_results:
            if r["scenario"] == name:
                s_baseline.append(r["baseline"]["metrics"])
                s_fault.append(r["fault"]["metrics"])
        
        final_summary[name] = {
            "baseline": get_average_metrics(s_baseline),
            "fault": get_average_metrics(s_fault)
        }

    # Saving everything to one big JSON file for the project report
    summary_file = out_dir / "summary.json"
    summary_file.write_text(json.dumps({
        "timestamp": str(datetime.now()),
        "success": True,
        "summary": final_summary,
        "details": all_results
    }, indent=4))

    # Taking a copy of the app logs to keep them with this experiment run
    app_log_src = Path("app_logs.json")
    if app_log_src.exists():
        log_dest = out_dir / "app_logs_snapshot.json"
        log_dest.write_text(app_log_src.read_text())

    print("All experiments are finished. Results saved.")

if __name__ == "__main__":
    main()
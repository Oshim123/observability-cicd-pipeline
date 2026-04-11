import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
#chose these imports because I need to run subprocesses for the load test and stress scripts,
# and I need to handle file paths for saving results, and I need to work with JSON for the final report.
# I also need argparse to handle command line arguments when running this experiment runner script.

# Manual loop here to get the average. 
# Avoided the statistics library because it was overkill for just two numbers.
def get_average_metrics(run_list):
    if not run_list:
        return {}
    #set all these numbers to 0 since I will be adding to them in the loop 
    # and I want to avoid errors if the list is empty or if some metrics are missing
    total_latency = 0
    total_error = 0
    count = 0

    #this loop goes through each run in the list and adds up the latency and error rates, while also counting how many runs there are
    for m in run_list:
        if m.get("avg_ms") is not None:
            #the total latency is the sum of all the average latencies from each run, and I will divide it by the count at the end to get the mean
            total_latency += m.get("avg_ms")
            
            # Convert "0.0%" → 0.0
            error_str = m.get("error_rate", "0%").replace("%", "")
            # the total error is the sum of all the error rates from each run, and I will divide it by the count at the end to get the mean
            total_error += float(error_str)
            
            count += 1
            
    if count == 0:
        return {"runs": 0} # if there are no runs, I return 0 to avoid division by zero errors later on when calculating the mean latency and error rate
    
    #these are the final average metrics that I return. 
    # I round them to 3 decimal places for latency and 2 decimal places for error rate to make them easier to read in the final report
    return {
        "runs": count,
        "mean_latency_ms": round(total_latency / count, 3),
        "error_rate_percent": round(total_error / count, 2)
    }

#this function runs the load test by calling the load_test.py script with the appropriate arguments, 
# and then it reads the metrics from a temporary JSON file that the load test script creates.
def run_load_test(url, requests, csv_file, scenario, run_id):
    # Using a temp file to pass data between the load test and this script
    temp_summary = csv_file.with_name("temp_stats.json")
    
    # Building the command to run the load test script with the appropriate arguments.
    cmd = [
        sys.executable, "scripts/load_test.py", # the Python executable to run the load_test.py script
        url, str(requests), # number of requests to send
        "--output-csv", str(csv_file), # the CSV file where the load test results will be saved
        "--summary-json", str(temp_summary), # the temporary JSON file where the load test will write the summary metrics
        "--scenario", scenario, # the scenario name to pass to the load test script for logging purposes
        "--run-id", run_id # the run ID to pass to the load test script for logging purposes
    ]
    
    # Using subprocess allows me to isolate the load test logic
    # from this orchestration script, making the system modular.
    result = subprocess.run(cmd, capture_output=True, text=True) #this runs the command and captures the output and error messages as text.
    
    # After the load test finishes, I read the metrics from the temp JSON file.
    metrics = {}
    if temp_summary.exists():
        metrics = json.loads(temp_summary.read_text())
        # Delete temp file after reading so it doesn't clutter the folder
        os.remove(str(temp_summary)) 

    return result, metrics
# This function runs a single experiment by first running a baseline load test,
# then launching the stress script in the background, 
# and finally running another load test while the system is under stress.

# Running baseline first ensures we have a control measurement
# to compare against the system under fault conditions.
def run_single_experiment(base_url, requests, duration, folder, scenario, idx, stress_script):
    run_id = "run_" + str(idx) 
    # It saves the results to CSV files and returns a dictionary with the metrics.
    
    # Setting up the subfolders for the results
    base_path = Path(folder) / "baseline"
    fault_path = Path(folder) / scenario
    base_path.mkdir(parents=True, exist_ok=True)
    fault_path.mkdir(parents=True, exist_ok=True)

    # Setting up the file paths for the CSV files where the load test results will be saved
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
    # Step 4: Cleanup. Make sure to wait for the stress script to finish before moving on to the next experiment.
    if stress_proc:
        stress_proc.wait()
    # Step 5: Return the results as a dictionary.
    return {
        "scenario": scenario,
        "baseline": {"metrics": base_metrics, "code": base_res.returncode},
        "fault": {"metrics": fault_metrics, "code": fault_res.returncode}
    }#chose these 3 metrics to return because they give a good overview of how the system performed under normal conditions and under stress,
    #and they also allow me to check if the load test script ran successfully or if there were any errors.

# This is the main function that runs all the experiments in sequence and saves the final summary report.
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--results-dir", required=True)
    args = parser.parse_args()
    #args.base_url is the URL of the app that I am testing, args.requests is the number of requests to send in each load test,
    # args.duration is how long to run the stress scripts for, args.repeats is how many times to repeat each experiment, 
    # and args.results_dir is the directory where I will save all the results.
    

    out_dir = Path(args.results_dir) #main output directory for this experiment run
    out_dir.mkdir(parents=True, exist_ok=True)#this creates the output directory if it doesn't already exist, and it also creates any parent directories if needed.

    #scearios is a list of tuples where each tuple contains the name of the scenario and the path to the corresponding stress script.
    scenarios = [
        ("cpu", "scripts/cpu_stress.py"),
        ("memory", "scripts/memory_stress.py"),
        ("error", None)
    ]

    all_results = []
    #nested for loop needed since I want to run each scenario multiple times, 
    # and I want to keep track of the results for each run separately so I can calculate averages later on.
    for name, script in scenarios:
        for i in range(1, args.repeats + 1):
            print("Running " + str(name) + " experiment round " + str(i))
            res = run_single_experiment(
                args.base_url, args.requests, args.duration, out_dir, name, i, script #this runs a single experiment with the given parameters and returns the results as a dictionary,
                #which I then append to the all_results list to keep track of everything.
            )
            all_results.append(res)

    final_summary = {}
    
    # Manual grouping of results to build the final report
    #for loop goes through each scenario and collects the baseline and fault metrics for all the runs of that scenario,
    for name, _ in scenarios:
        s_baseline = []
        s_fault = []
        #for loop goes through all the results and checks if the scenario matches the current scenario name, 
        # and if it does, it adds the baseline metrics to the s_baseline list and the fault metrics to the s_fault list.
        for r in all_results:
            if r["scenario"] == name:
                s_baseline.append(r["baseline"]["metrics"])
                s_fault.append(r["fault"]["metrics"])
        #        
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
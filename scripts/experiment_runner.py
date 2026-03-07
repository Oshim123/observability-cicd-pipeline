import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

#these imports are used for handling command-line arguments,
#running other scripts from Python, recording timestamps,
#and saving experiment results to files.


#this function runs a command (like load_test.py or cpu_stress.py)
#and captures its output so we can store experiment evidence

def run_command(command, output_file):
    result = subprocess.run(command, capture_output=True, text=True)
    #subprocess.run executes another script and captures its output

    with output_file.open("w", encoding="utf-8") as file_handle:
        #this creates the output file and writes the results of the command

        file_handle.write(f"$ {' '.join(command)}\n")
        #record the exact command that was executed

        file_handle.write(f"return_code: {result.returncode}\n\n")
        #store the return code which tells us if the command succeeded or failed

        file_handle.write("--- STDOUT ---\n")
        file_handle.write(result.stdout)
        #store standard output (normal printed output from the script)

        file_handle.write("\n--- STDERR ---\n")
        file_handle.write(result.stderr)
        #store standard error output in case something went wrong

    return result.returncode
    #return the command exit code so the experiment runner can record it


#this function runs the baseline experiment with no faults
#it simply sends requests to the application and measures behaviour

def run_baseline(base_url, request_count, results_dir):
    print("[runner] Running baseline experiment...")
    output_file = results_dir / "baseline_load_test.txt"
    #this is where the load test results will be saved

    start_time = datetime.now()
    #record when the experiment started

    return_code = run_command(
        [sys.executable, "scripts/load_test.py", f"{base_url}/", str(request_count)],
        output_file,
    )
    #this runs the load_test.py script against the normal application endpoint

    end_time = datetime.now()
    #record when the experiment finished

    return {
        "experiment": "baseline",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "return_code": return_code,
        "output_file": str(output_file),
    }
    #this dictionary stores experiment metadata which will later be written into summary.json


#this function runs a fault experiment
#it starts a stress script first, then runs the load test while the stress is active

def run_fault_experiment(name, stress_script, base_url, request_count, duration_seconds, results_dir):
    print(f"[runner] Running {name} experiment...")

    stress_output = results_dir / f"{name}_stress_output.txt"
    load_output = results_dir / f"{name}_load_test.txt"
    #these files store logs for both the stress script and the load test

    start_time = datetime.now()
    #record experiment start time

    with stress_output.open("w", encoding="utf-8") as stress_log:

        stress_process = subprocess.Popen(
            [sys.executable, stress_script, str(duration_seconds)],
            stdout=stress_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        #Popen starts the stress script (CPU or memory) as a background process
        #its output is written directly into the stress_output log file

        load_return_code = run_command(
            [sys.executable, "scripts/load_test.py", f"{base_url}/", str(request_count)],
            load_output,
        )
        #while the stress script is running, we run the load test to observe system behaviour

        stress_process.wait()
        #wait for the stress script to finish before ending the experiment

    end_time = datetime.now()
    #record when the experiment finished

    return {
        "experiment": name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "load_test_return_code": load_return_code,
        "stress_return_code": stress_process.returncode,
        "stress_output_file": str(stress_output),
        "load_output_file": str(load_output),
    }
    #this information is returned so it can be recorded in summary.json


#this function runs an experiment that intentionally triggers application errors
#it sends requests directly to the /trigger-error endpoint

def run_trigger_error_experiment(base_url, request_count, results_dir):
    print("[runner] Running trigger-error experiment...")

    output_file = results_dir / "trigger_error_load_test.txt"
    #this file stores the output of the load test

    start_time = datetime.now()

    return_code = run_command(
        [sys.executable, "scripts/load_test.py", f"{base_url}/trigger-error", str(request_count)],
        output_file,
    )
    #this sends requests to the /trigger-error endpoint to simulate application failures

    end_time = datetime.now()

    return {
        "experiment": "trigger_error",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "return_code": return_code,
        "output_file": str(output_file),
    }
    #this metadata will be included in the experiment summary


def main():

    parser = argparse.ArgumentParser(description="Run reproducible observability experiments")
    #argparse is used to allow configuration from the command line

    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Flask base URL")
    parser.add_argument("--requests", type=int, default=200, help="Requests per load test")
    parser.add_argument("--duration", type=int, default=60, help="Stress duration in seconds")
    #these arguments allow us to control the experiment parameters

    args = parser.parse_args()

    results_root = Path("results")
    #this folder will contain all experiment outputs

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #create a timestamp so each experiment run has its own directory

    results_dir = results_root / f"run_{timestamp}"
    results_dir.mkdir(parents=True, exist_ok=True)
    #create the results directory if it doesn't exist

    print(f"[runner] Results directory: {results_dir}")

    summary = []
    #this list will collect metadata about each experiment

    summary.append(run_baseline(args.base_url, args.requests, results_dir))
    #run the baseline experiment first

    summary.append(
        run_fault_experiment(
            "cpu",
            "scripts/cpu_stress.py",
            args.base_url,
            args.requests,
            args.duration,
            results_dir,
        )
    )
    #run the CPU stress experiment

    summary.append(
        run_fault_experiment(
            "memory",
            "scripts/memory_stress.py",
            args.base_url,
            args.requests,
            args.duration,
            results_dir,
        )
    )
    #run the memory stress experiment

    summary.append(run_trigger_error_experiment(args.base_url, args.requests, results_dir))
    #run the application error experiment

    summary_file = results_dir / "summary.json"

    summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    #write the experiment results and metadata into a structured JSON file

    print("[runner] Experiments complete.")
    print(f"[runner] Summary saved to {summary_file}")
    #print confirmation that the experiments finished successfully


if __name__ == "__main__":
    main()
    #this ensures the script runs only when executed directly
    #this script orchestrates reproducible observability experiments.
    #it runs baseline, CPU stress, memory stress, and application error tests
    #while capturing logs and saving results for later analysis.
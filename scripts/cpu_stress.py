import argparse
import multiprocessing
import time
import os
import sys

# Function designed to generate a continuous computational load.
def my_burn_function():
    # Utilises an infinite loop to ensure the process remains active 
    # until it is explicitly terminated by the parent script.
    while True:
        # Executes repetitive arithmetic operations to maintain high 
        # processor utilisation on the assigned core.
        res = 100 * 100
        res = res + 1 

if __name__ == "__main__":
    # Configuration of command-line arguments to receive test duration 
    # and metadata from the orchestration script.
    parser = argparse.ArgumentParser()
    parser.add_argument("duration", type=int, default=30)
    parser.add_argument("--scenario", default="cpu")
    parser.add_argument("--run-id", default="run_1")
    args = parser.parse_args()

    # Extraction of values from the arguments for use in the script.
    time_to_run = args.duration
    experiment_name = args.scenario
    id_of_run = args.run_id

    print("CPU STRESS STARTING")
    print("Scenario: " + str(experiment_name))
    print("Run ID: " + str(id_of_run))

    # Identification of the available processor cores to ensure the 
    # stress test covers the entire system.
    number_of_cores = multiprocessing.cpu_count()
    print("Detected " + str(number_of_cores) + " cores on this machine.")

    # Initialisation of a list to manage and track all active worker processes.
    all_my_workers = []

    print("[CPU_STRESS_STARTED] Now starting the loops...")
    
    # Spawning an individual worker process for every detected core 
    # to ensure maximum resource usage across the CPU.
    for i in range(number_of_cores):
        # Creation of a separate process dedicated to the burn function.
        p = multiprocessing.Process(target=my_burn_function)
        # Activation of the background process.
        p.start()
        # Storage of the process object for later termination.
        all_my_workers.append(p)
        print("Started worker number: " + str(i))

    # Suspension of the main script to allow the worker processes 
    # to maintain the system load for the required duration.
    print("Waiting for " + str(time_to_run) + " seconds...")
    time.sleep(time_to_run)

    # Systematic shutdown of every worker process to release system resources.
    print("Now stopping the workers...")
    for worker in all_my_workers:
        # Instruction to stop the specific process.
        worker.terminate()
        # Confirmation that the process has fully finished before proceeding.
        worker.join()
    
    print("[CPU_STRESS_FINISHED]")
    # Exit with code 0 to signal that the script completed as expected.
    sys.exit(0)
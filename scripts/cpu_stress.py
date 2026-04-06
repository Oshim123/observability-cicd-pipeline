import argparse
import multiprocessing
import time
import os
import sys

# This is the function that actually does the work to spike the CPU
def my_burn_function():
    # I use a while True loop so it never stops until the main script kills it
    while True:
        # Just doing some random math over and over
        # This makes the CPU core stay busy
        res = 100 * 100
        res = res + 1 

if __name__ == "__main__":
    # --- Part 1: Setting up the arguments ---
    # I'm using argparse to get the duration from the demo script
    parser = argparse.ArgumentParser()
    parser.add_argument("duration", type=int, default=30)
    parser.add_argument("--scenario", default="cpu")
    parser.add_argument("--run-id", default="run_1")
    args = parser.parse_args()

    # Get the values out of the args
    time_to_run = args.duration
    experiment_name = args.scenario
    id_of_run = args.run_id

    print("--- CPU STRESS STARTING ---")
    print("Scenario: " + str(experiment_name))
    print("Run ID: " + str(id_of_run))

    # --- Part 2: Finding the cores ---
    # I need to know how many cores the laptop has so I can stress all of them
    number_of_cores = multiprocessing.cpu_count()
    print("Detected " + str(number_of_cores) + " cores on this machine.")

    # --- Part 3: Starting the work ---
    # I'm making a list to keep track of all the processes I start
    all_my_workers = []

    print("[CPU_STRESS_STARTED] Now starting the loops...")
    
    # Manually looping through the number of cores to start a worker for each one
    for i in range(number_of_cores):
        # Create a new process for the core
        p = multiprocessing.Process(target=my_burn_function)
        # Start the process
        p.start()
        # Put it in my list so I can stop it later
        all_my_workers.append(p)
        print("Started worker number: " + str(i))

    # --- Part 4: Waiting ---
    # Now we just wait while the CPU stays at 100%
    print("Waiting for " + str(time_to_run) + " seconds...")
    time.sleep(time_to_run)

    # --- Part 5: Cleaning up ---
    # Now I have to loop through my list and kill every process I started
    print("Now stopping the workers...")
    for worker in all_my_workers:
        # Stop the worker
        worker.terminate()
        # Make sure it's actually finished
        worker.join()
    
    print("[CPU_STRESS_FINISHED]")
    # Exit with code 0 to show success
    sys.exit(0)
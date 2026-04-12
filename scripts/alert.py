import argparse
import time
import os
import sys
import random
from datetime import datetime

# Global variable used to ensure memory data remains in scope.
# This prevents the Python garbage collector from clearing the list until the test is complete.
MEMORY_HOG_LIST = []

if __name__ == "__main__":
    # --- Part 1: Configuration and Inputs ---
    # Setting up command-line arguments to allow the orchestration script to pass in parameters.
    my_parser = argparse.ArgumentParser(description="Manual Memory Stresser")
    
    # Definition of arguments required for the test duration and intensity.
    my_parser.add_argument("duration", type=int, help="Execution time in seconds")
    my_parser.add_argument("--scenario", default="memory", help="Scenario label for logging")
    my_parser.add_argument("--run-id", default="run_1", help="Unique identifier for the current run")
    my_parser.add_argument("--size", type=int, default=256, help="Target memory usage in MB")
    
    # Processing arguments into an object.
    my_args = my_parser.parse_args()
    
    # Extracting values for use throughout the script.
    run_duration = my_args.duration
    target_megabytes = my_args.size
    test_name = my_args.scenario
    current_run_id = my_args.run_id

    # --- Part 2: Execution Logging ---
    print("****************************************")
    print("* MEMORY STRESS SCRIPT STARTING   *")
    print("****************************************")
    print("Start Time: " + str(datetime.now()))
    print("Scenario Name: " + str(test_name))
    print("Run Identifier: " + str(current_run_id))
    print("Target Memory to Fill: " + str(target_megabytes) + " MB")
    print("[MEMORY_STRESS_STARTED]")

    # --- Part 3: Data Structure Generation ---
    # Calculation of bytes needed for a 1MB block. 
    # Repeating a character 1,024 times creates 1KB; repeating that block 1,024 times creates 1MB.
    print("Generating 1MB data blocks...")
    
    one_kb = "X" * 1024
    one_mb_block = one_kb * 1024
    
    # Displaying the size of the generated block for verification.
    block_size_bytes = sys.getsizeof(one_mb_block)
    print("Approximate size of 1MB block: " + str(block_size_bytes) + " bytes")

    # --- Part 4: Memory Allocation Sequence ---
    # Logic to occupy the system RAM by appending blocks to the global list.
    print("Beginning the allocation process...")
    
    i = 0
    while i < target_megabytes:
        # Adding the 1MB string to the list to increase total memory usage.
        MEMORY_HOG_LIST.append(one_mb_block)
        i = i + 1
        
        # Providing real-time progress updates to the terminal.
        print("Progress: Allocated " + str(i) + " MB...")
        
        # Periodic status checks for visibility during larger tests.
        if i % 50 == 0:
            print("--- CHECKPOINT: " + str(i) + " MB in memory ---")

    print("Allocation successful. Total items stored: " + str(len(MEMORY_HOG_LIST)))

    # --- Part 5: Holding State ---
    # The script must stay running to keep the RAM occupied. 
    # If the process terminates, the operating system will reclaim the memory immediately.
    print("The system is currently under memory pressure.")
    print("Holding for " + str(run_duration) + " seconds...")
    
    # Countdown timer to monitor the remaining time for the test round.
    seconds_passed = 0
    while seconds_passed < run_duration:
        time.sleep(1)
        seconds_passed = seconds_passed + 1
        
        # Updates provided every 10 seconds.
        if seconds_passed % 10 == 0:
            print("Test active... " + str(run_duration - seconds_passed) + "s remaining.")

    # --- Part 6: Cleanup Sequence ---
    print("Target duration reached. Initialising cleanup...")
    
    # Systematic removal of data from the list.
    # This returns the system to its baseline state before the process finishes.
    print("Emptying memory list...")
    while len(MEMORY_HOG_LIST) > 0:
        MEMORY_HOG_LIST.pop()
        
    # Setting the variable to None to ensure Python marks the data for deletion.
    MEMORY_HOG_LIST = None
    
    print("[MEMORY_STRESS_FINISHED]")
    print("End Time: " + str(datetime.now()))
    print("****************************************")

    # Returning exit code 0 to signal a successful completion.
    sys.exit(0)
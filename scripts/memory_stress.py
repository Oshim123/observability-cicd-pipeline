import argparse
import time
import os
import sys
from datetime import datetime

# I am making a global list to hold the data. 
# If I don't keep it in a list, Python's garbage collector might delete it
# and then the RAM won't actually stay full.
LIST_TO_HOLD_DATA = []

if __name__ == "__main__":
    # --- Part 1: Setting up the Inputs ---
    # I am using argparse because the demo script needs to pass in the duration
    my_parser = argparse.ArgumentParser(description="My Memory Stress Script")
    my_parser.add_argument("duration", type=int, nargs="?", default=30)
    my_parser.add_argument("--scenario", default="memory")
    my_parser.add_argument("--run-id", default="run_1")
    my_parser.add_argument("--max-mb", type=int, default=200)
    
    # Get the arguments out
    args = my_parser.parse_args()
    
    # Re-assigning them to easy names I can use
    time_limit = args.duration
    mb_limit = args.max_mb
    test_name = args.scenario
    run_idx = args.run_id

    # --- Part 2: Starting the script ---
    print("****************************************")
    print("MEMORY STRESS STARTING")
    # I'm using string concatenation because it's easier to see what is happening
    print("Scenario: " + str(test_name))
    print("Run ID: " + str(run_idx))
    print("Start Time: " + str(datetime.now()))
    print("[MEMORY_STRESS_STARTED]")

    # Calculating the end time manually
    start_time_float = time.time()
    end_time_float = start_time_float + time_limit

    # --- Part 3: Memory Filling Loop ---
    # I want to add 10MB at a time so I don't crash the laptop too fast
    chunk_size = 10
    
    # I'll keep track of how many MB I've added so far
    total_added_mb = 0

    print("Now starting to fill up to " + str(mb_limit) + " MB...")

    # I'm using a while True loop and checking conditions inside
    while True:
        # Check 1: Have we run out of time?
        if time.time() >= end_time_float:
            print("Time limit reached during allocation phase.")
            break
            
        # Check 2: Have we hit the MB limit?
        if total_added_mb >= mb_limit:
            print("Target MB limit reached.")
            break
            
        try:
            # Create a chunk of data in memory. This is just a bunch of zeros.
            ten_mb_chunk = bytearray(chunk_size * 1024 * 1024)
            
            # Put it in the list to "hog" the memory
            LIST_TO_HOLD_DATA.append(ten_mb_chunk)
            
            # Update our manual counter
            total_added_mb = total_added_mb + chunk_size
            
            # Print an update so I can see it working in the terminal
            print("Added " + str(chunk_size) + "MB. Total in RAM: " + str(total_added_mb) + "MB")
            
            # Sleep for a tiny bit so we don't freeze the whole computer
            time.sleep(0.1)
            
        except MemoryError:
            print("!!! ERROR: The system ran out of RAM early !!!")
            break

    # --- Part 4: Holding Phase ---
    # Now that we've filled the RAM, we need to stay alive until the timer is up
    print("Allocation finished. Holding memory for the rest of the duration...")
    
    while time.time() < end_time_float:
        # We just wait here
        # This keeps the 'LIST_TO_HOLD_DATA' in memory
        time.sleep(1)
        
        # Calculate how many seconds are left for my own information
        seconds_remaining = int(end_time_float - time.time())
        if seconds_remaining % 10 == 0:
            print("Still holding memory... " + str(seconds_remaining) + "s left.")

    # --- Part 5: Clean up ---
    print("Time is up! Clearing the memory list...")
    
    # Manually clearing and setting to None
    LIST_TO_HOLD_DATA.clear()
    
    
    print("Final End Time: " + str(datetime.now()))
    print("[MEMORY_STRESS_FINISHED]")
    print("****************************************")
    
    # Exit with code 0 for success
    sys.exit(0)
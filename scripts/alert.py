import argparse
import time
import os
import sys
import random
from datetime import datetime

# --- Global Variables ---
# I am using a global list to hold the data so it doesn't get 
# cleared by the Python garbage collector by accident.
MEMORY_HOG_LIST = []

if __name__ == "__main__":
    # --- Part 1: Setup and Inputs ---
    # I am setting up the argparse here to take commands from the demo script
    my_parser = argparse.ArgumentParser(description="Manual Memory Stresser")
    
    # Adding each argument one by one
    my_parser.add_argument("duration", type=int, help="How long to stay running")
    my_parser.add_argument("--scenario", default="memory", help="The name of this test")
    my_parser.add_argument("--run-id", default="run_1", help="The ID for this specific run")
    my_parser.add_argument("--size", type=int, default=256, help="Amount of MB to fill")
    
    # Parsing the arguments into a variable called 'my_args'
    my_args = my_parser.parse_args()
    
    # Manually re-assigning them to local variables 
    # This makes it easier for me to use them later in the script
    run_duration = my_args.duration
    target_megabytes = my_args.size
    test_name = my_args.scenario
    current_run_id = my_args.run_id

    # --- Part 2: Starting the Log ---
    print("****************************************")
    print("* MEMORY STRESS SCRIPT STARTING   *")
    print("****************************************")
    print("Start Time: " + str(datetime.now()))
    print("Scenario Name: " + str(test_name))
    print("Run Identifier: " + str(current_run_id))
    print("Target Memory to Fill: " + str(target_megabytes) + " MB")
    print("[MEMORY_STRESS_STARTED]")

    # --- Part 3: Creating the Data Block ---
    # To fill 1MB, I need 1,048,576 bytes. 
    # I am creating a string of 'X' characters to represent this.
    print("Creating the 1MB data blocks...")
    
    # I'll build it in steps to be safe
    one_kb = "X" * 1024
    one_mb_block = one_kb * 1024
    
    # Verify the size (optional check for debugging)
    block_size_bytes = sys.getsizeof(one_mb_block)
    print("Confirmed 1MB block size is roughly: " + str(block_size_bytes) + " bytes")

    # --- Part 4: The Allocation Loop ---
    # This is the main loop that actually fills the RAM
    print("Now starting the allocation loop. This might take a second...")
    
    # I am using a manual counter 'i' to track how many MB I have added
    i = 0
    while i < target_megabytes:
        # Append the 1MB block to my global list
        MEMORY_HOG_LIST.append(one_mb_block)
        
        # Increase the counter by 1
        i = i + 1
        
        # I want to see exactly how much is being used while it runs
        # So I print a message for every single MB added
        print("Progress: Added " + str(i) + " MB to the list...")
        
        # Every 50MB I'll print a special status update
        if i % 50 == 0:
            print("--- STATUS CHECK: " + str(i) + " MB allocated so far ---")

    print("Allocation Complete. Total in list: " + str(len(MEMORY_HOG_LIST)) + " units.")

    # --- Part 5: Holding the Memory ---
    # If the script finishes, the memory is freed. 
    # I need to keep the script 'alive' so the RAM stays full for the demo.
    print("The system is now under memory stress.")
    print("Waiting for " + str(run_duration) + " seconds before stopping...")
    
    # I'll use a countdown loop so it looks cool in the terminal
    seconds_passed = 0
    while seconds_passed < run_duration:
        # Wait 1 second
        time.sleep(1)
        # Add to our counter
        seconds_passed = seconds_passed + 1
        # Print a small tick every 10 seconds
        if seconds_passed % 10 == 0:
            print("Stress still running... " + str(run_duration - seconds_passed) + "s left.")

    # --- Part 6: Cleanup Phase ---
    print("Duration reached. Starting cleanup...")
    
    # Manually deleting the items from the list one by one
    # This is probably slower but it feels more 'thorough'
    print("Clearing the list...")
    while len(MEMORY_HOG_LIST) > 0:
        MEMORY_HOG_LIST.pop()
        
    # Set the list to None to make sure Python knows it's empty
    MEMORY_HOG_LIST = None
    
    print("[MEMORY_STRESS_FINISHED]")
    print("End Time: " + str(datetime.now()))
    print("****************************************")

    # Exit the script with code 0 for success
    sys.exit(0)
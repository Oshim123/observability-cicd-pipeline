import time
import sys
from datetime import datetime
#these imports are used for measuring time, handling command-line arguments,
# and recording timestamps for when the fault is injected.

if len(sys.argv) != 2:
    #this checks if the user has provided the duration (in seconds).
    print("Usage: python cpu_stress.py <duration_in_seconds>")
    sys.exit(1)
    #exit if incorrect input

duration = int(sys.argv[1])
#this converts the duration argument into an integer representing how long the CPU stress should run.

print("\n--- CPU Stress Test Starting ---")
start_timestamp = datetime.now()
print(f"Start Time: {start_timestamp}")
print(f"Running CPU stress for {duration} seconds...\n")
#these print what the test is doing and when it started, which is useful for tracking and logging purposes.
end_time = time.time() + duration
#calculate when the stress should stop

#this loop performs continuous mathematical operations to consume CPU cycles
#it is intentionally simple and deterministic to make the experiment repeatable
while time.time() < end_time:
    x = 0
    for i in range(1000000): #using a large number to ensure significant CPU usage, but not so large that it causes memory issues
        x += i * i #just a simple operation to keep the CPU busy. 

#once duration is complete, exit cleanly
end_timestamp = datetime.now()
print("\n--- CPU Stress Test Completed ---")
print(f"End Time: {end_timestamp}")
print("CPU stress simulation finished successfully.")
#the print statements just show when the test completed, which is useful for tracking and logging purposes.
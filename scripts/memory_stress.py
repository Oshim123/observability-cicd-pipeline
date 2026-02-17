import sys
import time
from datetime import datetime
#these imports are used for handling command-line arguments,
# measuring experiment duration, and recording timestamps.

if len(sys.argv) != 2: #sys.argv in short is a list of command-line arguments passed to the script.
    #this checks if the user has provided the duration (in seconds).
    print("Usage: python memory_stress.py <duration_in_seconds>")
    sys.exit(1)
    #exit if incorrect input

duration = int(sys.argv[1])
#this converts the duration argument into an integer representing how long memory stress should run.

print("\n--- Memory Stress Test Starting ---")
start_timestamp = datetime.now()
print(f"Start Time: {start_timestamp}")
print(f"Running memory stress for {duration} seconds...\n")
#different print statements just show what the test is doing and when it started, which is useful for tracking and logging purposes.
end_time = time.time() + duration
#calculate when the experiment should stop

memory_blocks = []
#this list will store allocated memory blocks so they remain in memory

try:
    while time.time() < end_time:
        #allocate approximately 10MB per iteration
        memory_blocks.append(" " * (10 * 1024 * 1024))
        #this gradually increases memory usage rather than exhausting it instantly
        
        print(f"Allocated ~{len(memory_blocks) * 10}MB so far...")
        
        time.sleep(0.5)
        #small delay so memory pressure increases gradually and can be observed in CloudWatch

except MemoryError:
    #this prevents the script from crashing abruptly if memory limit is reached
    print("Memory limit reached during stress test.")

print("\nHolding allocated memory until duration completes...\n")

while time.time() < end_time:
    time.sleep(1)
    #this ensures the allocated memory remains in use for the full experiment duration

#release memory cleanly
memory_blocks.clear()

end_timestamp = datetime.now()
print("\n--- Memory Stress Test Completed ---")
print(f"End Time: {end_timestamp}")
print("Memory stress simulation finished successfully.")
#the print statements just show when the test completed, which is useful for tracking and logging purposes.
#overall this script simulates memory stress by allocating blocks of memory over time, 
# which allows us to observe how the application behaves under increasing memory pressure.
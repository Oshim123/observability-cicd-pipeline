# Import multiprocessing to spawn CPU-intensive worker processes
import multiprocessing
# Import time to control how long the stress test runs
import time
# Import sys to read command-line arguments (stress duration in seconds)
import sys


def cpu_burn():
    """
    Runs an infinite loop of arithmetic operations to saturate a CPU core.

    A tight loop is used because it keeps the CPU constantly busy
    without waiting for I/O, which maximises utilisation on a single core.
    This is the simplest and most reliable way to simulate CPU exhaustion
    for observability experiments.
    """
    while True:
        # Perform a meaningless calculation to keep the CPU occupied
        # the result is discarded because the goal is CPU load, not computation
        _ = 9999 * 9999


def run_cpu_stress(duration_seconds):
    """
    Spawns one worker process per CPU core and runs them for a fixed duration.

    Using one process per core ensures all available CPU capacity is consumed,
    which is necessary to push CPUUtilization above the CloudWatch alarm threshold.
    After the duration expires, all worker processes are terminated cleanly.
    """
    # Detect how many CPU cores are available on the EC2 instance
    # so we can spawn exactly enough workers to saturate all of them
    core_count = multiprocessing.cpu_count()
    print(f"Starting CPU stress across {core_count} core(s) for {duration_seconds} second(s)...")

    # Spawn one worker process per core, each running the cpu_burn loop
    workers = []
    for _ in range(core_count):
        process = multiprocessing.Process(target=cpu_burn)
        process.start()
        workers.append(process)

    # Allow stress to run for the specified duration before stopping
    # this window is what CloudWatch observes and alarms on
    time.sleep(duration_seconds)

    # Terminate all worker processes after the stress window closes
    for process in workers:
        process.terminate()

    print("CPU stress test complete. Workers terminated.")


# Entry point — reads duration from command-line argument
if __name__ == "__main__":
    # Default to 30 seconds if no argument is provided
    # 30 seconds is enough to exceed a 1-minute CloudWatch evaluation period
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    run_cpu_stress(duration)
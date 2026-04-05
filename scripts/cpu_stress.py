import argparse
import multiprocessing
import time
def cpu_burn():
    while True:
        _ = 9999 * 9999


def run_cpu_stress(duration_seconds):
    core_count = multiprocessing.cpu_count()
    print(f"[CPU_STRESS_STARTED] cores={core_count} duration={duration_seconds}s")
    workers = []
    
    
    for _ in range(core_count):
        process = multiprocessing.Process(target=cpu_burn)
        process.start()
        workers.append(process)
    time.sleep(duration_seconds)

    for process in workers:
        process.terminate()
        process.join(timeout=1)

print("[CPU_STRESS_FINISHED]")


def parse_args():
    parser = argparse.ArgumentParser(description="CPU stress workload")
    parser.add_argument("duration", type=int, nargs="?", default=30, help="Stress duration in seconds")
    parser.add_argument("--scenario", default="cpu")
    parser.add_argument("--run-id", default="run0")
    return parser.parse_args()
if __name__ == "__main__":
    args = parse_args()
    if args.duration <= 0:
        raise ValueError("duration must be > 0")
    print(f"scenario={args.scenario} run_id={args.run_id}")
    run_cpu_stress(args.duration)

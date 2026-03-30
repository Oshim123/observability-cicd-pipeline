import argparse
import time
from datetime import datetime, timezone

DEFAULT_CHUNK_MB = 10


def parse_args():
    parser = argparse.ArgumentParser(description="Memory stress workload")
    parser.add_argument("duration", type=int, nargs="?", default=30, help="Stress duration in seconds")
    parser.add_argument("--scenario", default="memory")
    parser.add_argument("--run-id", default="run0")
    parser.add_argument("--max-mb", type=int, default=512, help="Max memory to allocate")
    return parser.parse_args()


def run_memory_stress(duration, max_mb):
    print(
        f"[MEMORY_STRESS_STARTED] start={datetime.now(timezone.utc).isoformat()} duration={duration}s chunk_mb={DEFAULT_CHUNK_MB} max_mb={max_mb}"
    )
    end_time = time.time() + duration
    memory_blocks = []

    try:
        while time.time() < end_time and (len(memory_blocks) * DEFAULT_CHUNK_MB) < max_mb:
            memory_blocks.append(" " * (DEFAULT_CHUNK_MB * 1024 * 1024))
            print(f"allocated_mb={len(memory_blocks) * DEFAULT_CHUNK_MB}")
            time.sleep(0.5)
    except MemoryError:
        print("memory_limit_reached")

    while time.time() < end_time:
        time.sleep(0.2)

    memory_blocks.clear()
    print(f"[MEMORY_STRESS_FINISHED] end={datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    args = parse_args()
    if args.duration <= 0 or args.max_mb <= 0:
        raise ValueError("duration and max-mb must be > 0")
    print(f"scenario={args.scenario} run_id={args.run_id}")
    run_memory_stress(args.duration, args.max_mb)

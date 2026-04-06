"""print aas thread pool sizing; run: python -m qltoq3.bench_aas_plan"""

import os
import threading

from .aas import aas_exec_plan
from .cli import pool_workers


def _max_w_unlimited(n_jobs: int) -> int:
    return min(n_jobs, max(32, (os.cpu_count() or 4) * 4))


def main() -> None:
    cpu = os.cpu_count() or 4
    scenarios = [
        ("313 pk3, coworkers=14, bc=0", 500, 14, 0),
        ("313 pk3, coworkers=14, bc=4", 500, 14, 4),
        ("313 pk3, coworkers=14, bc=32", 500, 14, 32),
        ("1 pk3, coworkers=1, bc=0", 40, 1, 0),
    ]
    print(f"cpu_count={cpu}")
    print(
        "scenario | n_jobs | nw | bc | max_w | exec_workers | pool_sz (tqdm slots if <=nw)"
    )
    print("-" * 88)
    for label, n_jobs, coworkers, bc in scenarios:
        nw = pool_workers(313, coworkers, bc)
        max_w = bc if bc > 0 else _max_w_unlimited(n_jobs)
        max_w = max(1, min(max_w, n_jobs))
        sem = threading.Semaphore(bc) if bc > 0 else None
        ew, psz, _ = aas_exec_plan(n_jobs, max_w, nw, sem)
        print(
            f"{label[:34]:<34} | {n_jobs:6d} | {nw:2d} | {bc:2d} | {max_w:5d} | {ew:12d} | {psz:25d}"
        )


if __name__ == "__main__":
    main()

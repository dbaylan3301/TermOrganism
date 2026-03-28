from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Any

def run_experts_parallel(tasks: list[tuple[str, Callable[[], Any]]], max_workers: int = 4) -> list[tuple[str, Any]]:
    results: list[tuple[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {ex.submit(fn): name for name, fn in tasks}
        for fut in as_completed(future_map):
            name = future_map[fut]
            try:
                results.append((name, fut.result()))
            except Exception as exc:
                results.append((name, exc))
    return results

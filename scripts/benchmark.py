# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pslr",
#   "publicsuffixlist",
# ]
# ///
"""
Benchmark pslr against the publicsuffixlist package.

Run with uv, which installs the latest releases of both packages:

    uv run scripts/benchmark.py

Or run in a virtual environment with both publicsuffixlist and
pslr installed:

    python scripts/benchmark.py
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import timeit

UPSTREAM_SETUP = "import publicsuffixlist; obj = publicsuffixlist.PublicSuffixList()"
REWRITE_SETUP = "import pslr as obj"


def benchmark_first_call(setup: str) -> float:
    """Median time to import, load, and make one call, in a fresh process."""
    times = []
    for _ in range(10):
        code = (
            "import sys, time; t = time.perf_counter(); "
            f"{setup}; obj.publicsuffix('www.example.com'); "
            "print(time.perf_counter() - t)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )
        times.append(float(result.stdout))
    return statistics.median(times)


def benchmark_calls(setup: str, statement: str) -> float:
    """Best-of-five per-call time, in seconds."""
    timer = timeit.Timer(statement, setup=setup, globals=globals())
    number, _ = timer.autorange()
    return min(timer.repeat(repeat=5, number=number)) / number


def main() -> None:
    rows: list[tuple[str, float, float]] = []

    upstream = benchmark_first_call(UPSTREAM_SETUP)
    rewrite = benchmark_first_call(REWRITE_SETUP)
    rows.append(("import + first publicsuffix()", upstream, rewrite))

    for name, statement in [
        ("publicsuffix()", "obj.publicsuffix('www.example.co.uk')"),
        ("publicsuffix() unknown TLD", "obj.publicsuffix('www.example.unknowntld')"),
        ("privatesuffix()", "obj.privatesuffix('www.example.co.uk')"),
        ("privatesuffix() wildcard", "obj.privatesuffix('a.b.test.ck')"),
        ("is_private()", "obj.is_private('www.example.co.uk')"),
        ("privateparts()", "obj.privateparts('aaa.www.example.com')"),
        ("subdomain()", "obj.subdomain('aaa.www.example.com', 1)"),
    ]:
        upstream = benchmark_calls(UPSTREAM_SETUP, statement)
        rewrite = benchmark_calls(REWRITE_SETUP, statement)
        rows.append((name, upstream, rewrite))

    width = max(len(row[0]) for row in rows)
    print(f"{'benchmark':<{width}}   {'publicsuffixlist':>16}   {'pslr':>15}   speedup")
    for name, upstream, rewrite in rows:
        print(
            f"{name:<{width}}   {format_time(upstream):>16}   "
            f"{format_time(rewrite):>15}   {upstream / rewrite:>6.1f}x"
        )


def format_time(seconds: float) -> str:
    if seconds >= 1e-3:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds * 1e6:.2f} µs"


if __name__ == "__main__":
    main()

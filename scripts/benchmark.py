# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "countryry",
#   "pycountry",
# ]
# ///
"""
Benchmark countryry against pycountry.

Run with uv, which installs the latest releases of both packages:

    uv run scripts/benchmark.py

Or run in a virtual environment with both pycountry and countryry installed:

    python scripts/benchmark.py
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import timeit


def benchmark_import(module: str) -> float:
    """Median time to import a module in a fresh process, in seconds."""
    times = []
    for _ in range(10):
        code = (
            "import sys, time; t = time.perf_counter(); "
            f"import {module}; "
            "print(time.perf_counter() - t)"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )
        times.append(float(result.stdout))
    return statistics.median(times)


def benchmark_first_call(module: str, call: str) -> float:
    """Median time to import and make one call, in a fresh process."""
    times = []
    for _ in range(10):
        code = (
            "import sys, time; t = time.perf_counter(); "
            f"import {module}; {module}.{call}; "
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

    upstream = benchmark_import("pycountry")
    ry = benchmark_import("countryry")
    rows.append(("import", upstream, ry))

    upstream = benchmark_first_call("pycountry", "countries.get(alpha_2='DE')")
    ry = benchmark_first_call("countryry", "countries.get(alpha_2='DE')")
    rows.append(("import + first get()", upstream, ry))

    for name, statement in [
        ("countries.get()", "mod.countries.get(alpha_2='DE')"),
        ("subdivisions.get()", "mod.subdivisions.get(code='US-CA')"),
        ("subdivisions.get(country_code=)", "mod.subdivisions.get(country_code='US')"),
        ("languages.get()", "mod.languages.get(alpha_3='deu')"),
        ("countries.lookup()", "mod.countries.lookup('germany')"),
        ("languages.lookup()", "mod.languages.lookup('azerbaijani, north')"),
        ("countries.search_fuzzy()", "mod.countries.search_fuzzy('berlin')"),
        ("iterate countries", "[c.alpha_2 for c in mod.countries]"),
        ("len(subdivisions)", "len(mod.subdivisions)"),
    ]:
        upstream = benchmark_calls(
            "import pycountry as mod; mod.countries.get(alpha_2='DE'); "
            "mod.subdivisions.get(code='US-CA'); mod.languages.get(alpha_3='deu')",
            statement,
        )
        ry = benchmark_calls(
            "import countryry as mod; mod.countries.get(alpha_2='DE')", statement
        )
        rows.append((name, upstream, ry))

    width = max(len(row[0]) for row in rows)
    print(f"{'benchmark':<{width}}   {'pycountry':>10}   {'countryry':>10}   speedup")
    for name, upstream, ry in rows:
        print(
            f"{name:<{width}}   {format_time(upstream):>10}   {format_time(ry):>10}   "
            f"{upstream / ry:>6.1f}x"
        )


def format_time(seconds: float) -> str:
    if seconds >= 1e-3:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds * 1e6:.2f} µs"


if __name__ == "__main__":
    main()

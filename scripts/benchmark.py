# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "emoji",
#   "emojet",
# ]
# ///
"""
Benchmark emojet against the emoji package.

Run with uv, which installs the latest releases of both packages:

    uv run scripts/benchmark.py

Or run in a virtual environment with both emoji and emojet installed:

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


TEXT = (
    "Hi 😁, Python is fun 👍 and fast 🚀! "
    "The family 👨‍👩‍👧‍👦 went to the beach 🏖️ with a dog 🐕. "
    "No emoji in this sentence at all, just plain text to scan. "
    "Flags: 🇫🇷 🇯🇵 🇺🇸, skin tones: 👋🏻 👋🏿, and a keycap: 1️⃣. "
) * 5

NAMED = None  # set in main()


def benchmark_calls(setup: str, statement: str) -> float:
    """Best-of-five per-call time, in seconds."""
    timer = timeit.Timer(statement, setup=setup, globals=globals())
    number, _ = timer.autorange()
    return min(timer.repeat(repeat=5, number=number)) / number


def main() -> None:
    global NAMED
    import emoji

    NAMED = emoji.demojize(TEXT)

    rows: list[tuple[str, float, float]] = []

    upstream = benchmark_import("emoji")
    jet = benchmark_import("emojet")
    rows.append(("import", upstream, jet))

    upstream = benchmark_first_call("emoji", "demojize('Hi 😁!')")
    jet = benchmark_first_call("emojet", "demojize('Hi 😁!')")
    rows.append(("import + first demojize()", upstream, jet))

    for name, statement in [
        ("demojize()", "mod.demojize(TEXT)"),
        ("emojize()", "mod.emojize(NAMED)"),
        ("emoji_list()", "mod.emoji_list(TEXT)"),
        ("emoji_count()", "mod.emoji_count(TEXT)"),
        ("replace_emoji()", "mod.replace_emoji(TEXT, '')"),
        ("is_emoji()", "mod.is_emoji('😁')"),
        ("purely_emoji()", "mod.purely_emoji('😁👍🚀')"),
        ("demojize(language='fr')", "mod.demojize(TEXT, language='fr')"),
        ("version()", "mod.version(TEXT)"),
    ]:
        upstream = benchmark_calls("import emoji as mod; mod.demojize('😁')", statement)
        jet = benchmark_calls("import emojet as mod; mod.demojize('😁')", statement)
        rows.append((name, upstream, jet))

    width = max(len(row[0]) for row in rows)
    print(f"{'benchmark':<{width}}   {'emoji':>10}   {'emojet':>10}   speedup")
    for name, upstream, jet in rows:
        print(
            f"{name:<{width}}   {format_time(upstream):>10}   {format_time(jet):>10}   "
            f"{upstream / jet:>6.1f}x"
        )


def format_time(seconds: float) -> str:
    if seconds >= 1e-3:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds * 1e6:.2f} µs"


if __name__ == "__main__":
    main()

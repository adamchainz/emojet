# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "schwifty",
#   "swifter",
# ]
# ///
"""
Benchmark swifter against the schwifty package.

Run with uv, which installs the latest releases of both packages:

    uv run scripts/benchmark.py

Or run in a virtual environment with both schwifty and swifter installed:

    python scripts/benchmark.py
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import timeit
from collections.abc import Callable

IBANS = [
    "AD1200012030200359100100",
    "AT611904300234573201",
    "BE68539007547034",
    "CH9300762011623852957",
    "DE89370400440532013000",
    "ES9121000418450200051332",
    "FR1420041010050500013M02606",
    "GB29NWBK60161331926819",
    "GR1601101250000000012300695",
    "IT60X0542811101000000123456",
    "NL91ABNA0417164300",
    "NO9386011117947",
    "PL61109010140000071219812874",
    "PT50000201231234567890154",
    "SA0380000000608010167519",
    "SE4550000000058398257466",
    "TR330006100519786457841326",
]
BICS = ["GENODEM1GLS", "BNPAFRPPXXX", "GENODEFF", "NWBKGB2LXXX"]


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
    example = IBANS[4]
    benchmarks: list[tuple[str, Callable[[str], float]]] = [
        ("import", lambda mod: benchmark_import(mod)),
        (
            "import + first IBAN()",
            lambda mod: benchmark_first_call(mod, f"IBAN({example!r})"),
        ),
        (
            "IBAN()",
            lambda mod: benchmark_calls(
                f"import {mod}; IBAN = {mod}.IBAN",
                "[IBAN(value) for value in IBANS]",
            ),
        ),
        (
            "IBAN() + components",
            lambda mod: benchmark_calls(
                f"import {mod}; IBAN = {mod}.IBAN",
                "[(i.bank_code, i.branch_code, i.account_code)"
                " for i in (IBAN(value) for value in IBANS)]",
            ),
        ),
        (
            "IBAN(allow_invalid=True).is_valid",
            lambda mod: benchmark_calls(
                f"import {mod}; IBAN = {mod}.IBAN",
                "[IBAN(value, allow_invalid=True).is_valid for value in IBANS]",
            ),
        ),
        (
            "IBAN.generate()",
            lambda mod: benchmark_calls(
                f"import {mod}; generate = {mod}.IBAN.generate",
                "generate('DE', bank_code='37040044', account_code='532013000')",
            ),
        ),
        (
            "BIC()",
            lambda mod: benchmark_calls(
                f"import {mod}; BIC = {mod}.BIC",
                "[BIC(value) for value in BICS]",
            ),
        ),
    ]

    print("| Benchmark | schwifty | swifter | Speedup |")
    print("|---|---|---|---|")
    for name, run in benchmarks:
        theirs = run("schwifty")
        ours = run("swifter")
        print(
            f"| `{name}` | {format_time(theirs)} | {format_time(ours)}"
            f" | {theirs / ours:.1f}x |"
        )


def format_time(seconds: float) -> str:
    if seconds >= 1e-3:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds * 1e6:.2f} µs"


if __name__ == "__main__":
    main()

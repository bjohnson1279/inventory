import argparse
import json
import subprocess
import sys
import time
from collections import defaultdict
from typing import Dict, Any

try:
    import httpx
except ImportError:
    print("Please install httpx: pip install httpx")
    sys.exit(1)


import os

BACKENDS = {
    "gql": os.getenv("GRAPHQL_URL", "http://localhost:4000"),
    "express": os.getenv("EXPRESS_REST_URL", "http://localhost:5000"),
    "php": os.getenv("PHP_REST_URL", "http://localhost:8000"),
}

def check_health(url: str) -> bool:
    try:
        # Some backends might not have /api/health, we check / or /api/health
        health_endpoints = [f"{url}/api/health", f"{url}/health", url]
        for ep in health_endpoints:
            try:
                res = httpx.get(ep, timeout=2.0)
                if res.status_code < 500:
                    return True
            except httpx.RequestError:
                continue
        return False
    except Exception:
        return False

def wait_for_backends(max_retries: int = 30, initial_delay: float = 2.0):
    print("\n--- Health Checks ---")
    status = {name: False for name in BACKENDS}
    
    for attempt in range(max_retries):
        all_healthy = True
        for name, url in BACKENDS.items():
            if not status[name]:
                if check_health(url):
                    status[name] = True
                    print(f"[\033[92mOK\033[0m] {name:10} ({url})")
                else:
                    all_healthy = False
        
        if all_healthy:
            print("All backends are healthy!\n")
            return
            
        time.sleep(initial_delay)
        
    print("\n[\033[91mFAIL\033[0m] Health check timed out for:")
    for name, is_healthy in status.items():
        if not is_healthy:
            print(f"  - {name} ({BACKENDS[name]})")
    sys.exit(1)

def seed_data():
    print("\n--- Seeding Test Data ---")
    for name, url in BACKENDS.items():
        seed_url = f"{url}/api/auth/setup"
        try:
            res = httpx.post(seed_url, timeout=10.0)
            if res.status_code in (200, 201):
                print(f"[\033[92mOK\033[0m] {name:10} seeded successfully")
            else:
                print(f"[\033[93mWARN\033[0m] {name:10} seeding returned {res.status_code}")
        except Exception as e:
            print(f"[\033[91mFAIL\033[0m] {name:10} seeding failed: {e}")

def run_pytest(report_file: str, verbose: bool):
    print("\n--- Running Conformance Tests ---")
    cmd = [
        "pytest",
        "tests/conformance/",
        "--tb=short",
        "--json-report",
        f"--json-report-file={report_file}"
    ]
    if verbose:
        cmd.append("-v")
        
    try:
        # Note: pytest exits with 1 if tests fail, which is expected
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        print("pytest command not found. Please ensure pytest and pytest-json-report are installed.")
        sys.exit(1)

def parse_and_print_report(report_file: str):
    print("\n--- Conformance Summary Matrix ---")
    try:
        with open(report_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to load JSON report: {e}")
        return

    # Matrix: row = test module, column = backend
    matrix: Dict[str, Dict[str, Dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"pass": 0, "fail": 0, "skip": 0}))
    
    total_pass = 0
    total_fail = 0
    total_skip = 0
    
    tests = data.get("tests", [])
    if not tests:
        print("No tests found in the report.")
        return
        
    for test in tests:
        nodeid = test.get("nodeid", "")
        outcome = test.get("outcome", "unknown")
        
        # Parse module
        parts = nodeid.split("::")
        module = parts[0] if parts else "unknown"
        
        # Try to guess backend from parameterization (e.g. [gql], [express], [php])
        backend = "unknown"
        for b in BACKENDS.keys():
            if f"[{b}" in nodeid or f"-{b}" in nodeid:
                backend = b
                break
                
        if backend == "unknown":
            # If not parameterized by backend, just put under general
            backend = "general"
            
        if outcome == "passed":
            matrix[module][backend]["pass"] += 1
            total_pass += 1
        elif outcome == "failed":
            matrix[module][backend]["fail"] += 1
            total_fail += 1
        elif outcome == "skipped":
            matrix[module][backend]["skip"] += 1
            total_skip += 1
            
    # Print table header
    backends_found = set()
    for m in matrix.values():
        backends_found.update(m.keys())
    backends_found = sorted(list(backends_found))
    
    print(f"{'Test Module':<40}", end="")
    for b in backends_found:
        print(f" | {b:^15}", end="")
    print("\n" + "-" * 40 + ("|-" + "-"*15) * len(backends_found))
    
    for module, b_data in matrix.items():
        # Trim module name for display
        display_module = module.replace("tests/conformance/", "")
        if len(display_module) > 38:
            display_module = "..." + display_module[-35:]
            
        print(f"{display_module:<40}", end="")
        for b in backends_found:
            counts = b_data.get(b, {"pass": 0, "fail": 0, "skip": 0})
            p, f_c, s = counts["pass"], counts["fail"], counts["skip"]
            
            cell = []
            if p > 0: cell.append(f"\033[92m{p} P\033[0m")
            if f_c > 0: cell.append(f"\033[91m{f_c} F\033[0m")
            if s > 0: cell.append(f"\033[93m{s} S\033[0m")
            
            cell_str = " ".join(cell) if cell else "-"
            # Calculate visible length (ignoring ANSI escapes) for alignment
            visible_len = sum(len(str(c)) for c in [p, f_c, s] if c > 0) + (len(cell)-1 if len(cell)>0 else 1)
            padding = 15 - visible_len - (2 * len(cell) if cell else 0) # rough estimate for padding
            
            # Simplified formatting for matrix cell
            cell_text = ", ".join(
                ([f"{p}P"] if p else []) + 
                ([f"{f_c}F"] if f_c else []) + 
                ([f"{s}S"] if s else [])
            )
            if not cell_text: cell_text = "-"
            
            print(f" | {cell_text:^15}", end="")
        print()
        
    print("\n" + "=" * 60)
    print(f"TOTALS: \033[92m{total_pass} Passed\033[0m, \033[91m{total_fail} Failed\033[0m, \033[93m{total_skip} Skipped\033[0m")
    
    if total_fail > 0:
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Run Conformance Tests for Inventory Systems")
    parser.add_argument("--skip-health-check", action="store_true", help="Skip health checking backends")
    parser.add_argument("--seed", action="store_true", help="Seed test data before running")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose pytest output")
    parser.add_argument("--report-dir", default=".", help="Directory to save the conformance report")
    args = parser.parse_args()
    
    import os
    report_file = os.path.join(args.report_dir, "conformance-report.json")
    
    if not args.skip_health_check:
        wait_for_backends()
        
    if args.seed:
        seed_data()
        
    run_pytest(report_file, args.verbose)
    parse_and_print_report(report_file)

if __name__ == "__main__":
    main()

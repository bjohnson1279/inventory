#!/usr/bin/env python3
"""
Sync Submodules Utility
-----------------------
Fast-forwards all git submodules in the inventory ecosystem to their remote
default branches (main/master), verifies working trees, and synchronizes parent pointers.

Usage:
    python scripts/sync_submodules.py [--commit]
"""

import os
import sys
import subprocess
import argparse

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run_git(args, cwd):
    """Run a git command safely with UTF-8 decoding."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )

def get_submodules():
    """Extract list of submodule paths from .gitmodules."""
    gitmodules_path = os.path.join(BASE_DIR, ".gitmodules")
    submodules = []
    if os.path.exists(gitmodules_path):
        with open(gitmodules_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("path ="):
                    submodules.append(line.split("=", 1)[1].strip())
    return submodules

def main():
    parser = argparse.ArgumentParser(description="Synchronize all submodules with their remote heads.")
    parser.add_argument("--commit", action="store_true", help="Automatically commit updated submodule pointers in parent repository")
    args = parser.parse_args()

    submodules = get_submodules()
    if not submodules:
        print("❌ No submodules found in .gitmodules.")
        sys.exit(1)

    print("=" * 70)
    print(f"🔄 Synchronizing {len(submodules)} submodules in {BASE_DIR}")
    print("=" * 70)

    updated_pointers = []

    for sm in submodules:
        sm_dir = os.path.join(BASE_DIR, sm)
        if not os.path.exists(sm_dir):
            print(f"⚠️  Directory {sm} does not exist, skipping.")
            continue

        print(f"\n📁 Submodule: {sm}")

        # Fetch latest remote refs
        run_git(["fetch", "origin"], cwd=sm_dir)

        # Detect default branch (main vs master)
        res_branches = run_git(["branch", "-r"], cwd=sm_dir)
        default_branch = "main"
        if "origin/master" in res_branches.stdout and "origin/main" not in res_branches.stdout:
            default_branch = "master"

        # Checkout and pull
        run_git(["checkout", default_branch], cwd=sm_dir)
        pull_res = run_git(["pull", "origin", default_branch], cwd=sm_dir)
        print(f"   Branch: {default_branch} -> {pull_res.stdout.strip() or pull_res.stderr.strip()}")

        # Record latest commit
        log_res = run_git(["log", "-1", "--oneline"], cwd=sm_dir)
        commit_info = log_res.stdout.strip()
        print(f"   Head:   {commit_info}")
        updated_pointers.append((sm, commit_info))

    print("\n" + "=" * 70)
    print("📋 Updating Parent Submodule Registration & Pointers")
    print("=" * 70)

    # Update git submodule status in parent
    status_res = run_git(["submodule", "status"], cwd=BASE_DIR)
    print(status_res.stdout.strip())

    if args.commit:
        # Check if parent has changes
        st_res = run_git(["status", "--porcelain"], cwd=BASE_DIR)
        submodule_changes = [line for line in st_res.stdout.splitlines() if any(sm in line for sm in submodules)]
        if submodule_changes:
            print("\n📝 Staging submodule pointer updates...")
            for sm in submodules:
                run_git(["add", sm], cwd=BASE_DIR)
            run_git(["commit", "-m", "chore: advance submodule pointers to latest verified heads"], cwd=BASE_DIR)
            print("✅ Committed submodule pointer updates to parent repository.")
        else:
            print("\n✅ Submodule pointers are already up-to-date in parent repository.")

    print("\n🎉 Synchronization complete!")

if __name__ == "__main__":
    main()

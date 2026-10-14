#!/usr/bin/env python3
"""
Batch PR Merger & Submodule Synchronizer
----------------------------------------
Executes the approved batch operations for Jules, Bolt, Sentinel, and Palette PRs:
1. Closes superseded PRs with descriptive audit explanations.
2. Squash-merges approved Group A PRs across all submodules.
3. Synchronizes submodule gitlinks and commits updated tree pointers in parent.

Usage:
    python scripts/batch_merge_prs.py [--dry-run] [--skip-sync]
"""

import os
import sys
import subprocess
import argparse
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# PRs to close (Superseded / Redundant)
SUPERSEDED_PRS = [
    {
        "repo": "inventory-python-sidecar",
        "pr": 67,
        "comment": "Closing as duplicate: RateLimitMiddleware memory leak fix is superseded by PR #69 which includes this fix plus missing HTTP security response headers.",
    },
    {
        "repo": "react-ddd-inventory-client",
        "pr": 375,
        "comment": "Closing as duplicate: SupplierCollaborationPortal unit tests are superseded by more comprehensive test coverage in PR #376.",
    },
    {
        "repo": "react-ddd-inventory-client",
        "pr": 372,
        "comment": "Closing as duplicate: PredictiveScheduling unit tests are superseded by broader test suite and mock isolation in PR #378.",
    },
    {
        "repo": "react-ddd-inventory-client",
        "pr": 364,
        "comment": "Closing as duplicate: URL injection fix in ESG Emissions Panel is superseded by complete parameter encoding in PR #367.",
    },
]

# PRs to merge (Group A: High Value)
MERGE_BATCHES = [
    {
        "repo": "gql-ddd-inventory",
        "prs": [768, 767],
    },
    {
        "repo": "js-ddd-inventory",
        "prs": [874, 873, 872],
    },
    {
        "repo": "inventory-python-sidecar",
        "prs": [69, 68],
    },
    {
        "repo": "python-ddd-inventory",
        "prs": [158, 155, 153, 151, 146],
    },
    {
        "repo": "react-ddd-inventory-client",
        "prs": [
            389, 388, 387, 386, 385, 384, 383, 382,
            381, 380, 379, 378, 377, 376, 374, 373,
            371, 370, 369, 368, 367, 366
        ],
    },
]


def run_cmd(cmd, cwd=None, check=False):
    env = os.environ.copy()
    env["GH_NO_PAGER"] = "1"
    env["GH_PROMPT_DISABLED"] = "1"
    env["NO_COLOR"] = "1"
    res = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    if check and res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {cmd}\nStderr: {res.stderr.strip()}")
    return res


def close_superseded(dry_run=False):
    print("\n" + "=" * 70)
    print("🚫 STEP 1: Closing Duplicate & Superseded PRs")
    print("=" * 70)

    for item in SUPERSEDED_PRS:
        repo = item["repo"]
        pr = item["pr"]
        comment = item["comment"]
        repo_dir = os.path.join(BASE_DIR, repo)

        print(f"\nClosing {repo} PR #{pr}...")
        if dry_run:
            print(f"  [DRY-RUN] Would close PR #{pr} with comment: {comment[:60]}...")
            continue

        cmd = f'gh pr close {pr} --comment "{comment}" --delete-branch'
        res = run_cmd(cmd, cwd=repo_dir)
        if res.returncode == 0:
            print(f"  ✅ Closed PR #{pr} successfully.")
        else:
            print(f"  ⚠️ Failed to close PR #{pr}: {res.stderr.strip() or res.stdout.strip()}")


def merge_group_a(dry_run=False):
    print("\n" + "=" * 70)
    print("🚀 STEP 2: Squash-Merging Group A PRs")
    print("=" * 70)

    merged_count = 0
    failed_prs = []

    for batch in MERGE_BATCHES:
        repo = batch["repo"]
        prs = batch["prs"]
        repo_dir = os.path.join(BASE_DIR, repo)

        print(f"\n📦 Submodule: {repo} ({len(prs)} PRs to merge)")

        for pr in prs:
            print(f"  Merging PR #{pr}...", end=" ", flush=True)
            if dry_run:
                print(f"[DRY-RUN] gh pr merge {pr} --squash --admin --delete-branch")
                merged_count += 1
                continue

            cmd = f"gh pr merge {pr} --squash --admin --delete-branch"
            res = run_cmd(cmd, cwd=repo_dir)
            if res.returncode == 0:
                print("✅ Merged")
                merged_count += 1
            else:
                # Retry with basic squash without --admin in case repo has no branch protection
                retry_cmd = f"gh pr merge {pr} --squash --delete-branch"
                res_retry = run_cmd(retry_cmd, cwd=repo_dir)
                if res_retry.returncode == 0:
                    print("✅ Merged (standard)")
                    merged_count += 1
                else:
                    err = res.stderr.strip() or res.stdout.strip()
                    print(f"❌ Failed: {err}")
                    failed_prs.append((repo, pr, err))
            time.sleep(0.5)

    print(f"\nMerge summary: {merged_count} PRs merged, {len(failed_prs)} failed.")
    return failed_prs


def sync_submodules(dry_run=False):
    print("\n" + "=" * 70)
    print("🔄 STEP 3: Synchronizing Submodules & Updating Parent Gitlinks")
    print("=" * 70)

    if dry_run:
        print("  [DRY-RUN] Would run python scripts/sync_submodules.py --commit")
        return

    sync_script = os.path.join(BASE_DIR, "scripts", "sync_submodules.py")
    res = run_cmd(f"{sys.executable} \"{sync_script}\" --commit", cwd=BASE_DIR)
    print(res.stdout)
    if res.stderr:
        print(res.stderr, file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Batch merge and close Jules PRs")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without executing merges/closes")
    parser.add_argument("--skip-sync", action="store_true", help="Skip parent gitlink synchronization")
    args = parser.parse_args()

    print("=" * 70)
    print("🤖 Jules / Bolt / Sentinel PR Batch Automation Runner")
    print(f"Working Directory: {BASE_DIR}")
    if args.dry_run:
        print("Mode: DRY RUN (no state changes will be made)")
    print("=" * 70)

    close_superseded(dry_run=args.dry_run)
    failed = merge_group_a(dry_run=args.dry_run)
    if not args.skip_sync:
        sync_submodules(dry_run=args.dry_run)

    if failed:
        print("\n⚠️ The following PRs encountered errors during merge:")
        for repo, pr, err in failed:
            print(f"  • {repo} PR #{pr}: {err}")
    else:
        print("\n🎉 All PR batch operations completed successfully!")


if __name__ == "__main__":
    main()

import subprocess
import json
import re
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

repo_dir = r"c:\Users\johns\DEV\inventory\php-ddd-inventory"

def run(cmd, cwd=repo_dir):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    return res.returncode, res.stdout, res.stderr

code, stdout, stderr = run("gh pr list --state open --json number,title,headRefName")
if code != 0:
    print("Error getting PRs:", stderr)
    sys.exit(1)

prs = json.loads(stdout)
print(f"Processing {len(prs)} open PRs...")

def resolve_conflict_file(filepath):
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    if "<<<<<<<" not in content:
        return False

    # Resolution strategy:
    # 1. For imports (use statements): combine both sides, deduplicate.
    # 2. For methods / body: keep both sides if distinct, or prefer the master/PR combination cleanly.
    
    lines = content.splitlines()
    new_lines = []
    in_conflict = False
    side_a = []
    side_b = []
    current_side = None

    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("<<<<<<<"):
            in_conflict = True
            current_side = "a"
            side_a = []
            side_b = []
            i += 1
            continue
        elif line.startswith("======="):
            current_side = "b"
            i += 1
            continue
        elif line.startswith(">>>>>>>"):
            in_conflict = False
            # Resolve conflict block
            combined_a = "\n".join(side_a)
            combined_b = "\n".join(side_b)

            # If it's imports (use statements)
            all_lines = side_a + side_b
            use_lines = [l for l in all_lines if l.strip().startswith("use ")]
            other_a = [l for l in side_a if not l.strip().startswith("use ")]
            other_b = [l for l in side_b if not l.strip().startswith("use ")]

            if use_lines and len(use_lines) == len(all_lines):
                # Only use statements: deduplicate preserving order
                seen = set()
                dedup_uses = []
                for u in use_lines:
                    if u not in seen:
                        seen.add(u)
                        dedup_uses.append(u)
                new_lines.extend(dedup_uses)
            else:
                # Deduplicate exact line blocks or combine both
                res_block = []
                seen = set()
                for l in side_a + side_b:
                    if l not in seen or l.strip() == "" or l.strip() in ["{", "}"]:
                        if l.strip() not in ["{", "}"]:
                            seen.add(l)
                        res_block.append(l)
                new_lines.extend(res_block)

            i += 1
            continue

        if in_conflict:
            if current_side == "a":
                side_a.append(line)
            else:
                side_b.append(line)
        else:
            new_lines.append(line)
        i += 1

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines) + "\n")
    return True

results = []

for pr in prs:
    branch = pr["headRefName"]
    num = pr["number"]
    title = pr["title"]
    print(f"\n--- PR #{num}: {branch} ---")

    # Fetch branch
    run(f"git fetch origin {branch}:{branch}")
    run(f"git checkout {branch}")
    
    # Try merging master
    code, stdout, stderr = run("git merge master --no-edit")
    if code == 0:
        print(f"  Merged master cleanly into #{num}")
        run(f"git push origin {branch}")
        results.append((num, branch, "Clean"))
        continue

    print(f"  Conflicts detected in #{num}, resolving...")
    # Find conflicted files
    c_code, c_out, _ = run("git status --porcelain")
    conflicted_files = []
    for l in c_out.splitlines():
        if l.startswith("UU ") or l.startswith("AA ") or l.startswith("UD ") or l.startswith("DU "):
            conflicted_files.append(l[3:].strip())

    for cf in conflicted_files:
        full_path = os.path.join(repo_dir, cf)
        if os.path.exists(full_path):
            resolve_conflict_file(full_path)
            run(f"git add \"{cf}\"")

    # Check if conflicts resolved
    run("git commit -m \"Merge branch 'master' into " + branch + "\"")
    
    # Push branch
    p_code, p_out, p_err = run(f"git push origin {branch}")
    if p_code == 0:
        print(f"  Successfully merged master into #{num} and pushed!")
        results.append((num, branch, "Resolved & Pushed"))
    else:
        print(f"  Push failed for #{num}: {p_err}")
        results.append((num, branch, f"Push Failed: {p_err[:100]}"))

# Return to master
run("git checkout master")

print("\n================ FINAL STATUS ================")
for r in results:
    print(f"PR #{r[0]} ({r[1]}): {r[2]}")

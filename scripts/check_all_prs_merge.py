import subprocess
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    return res.returncode, res.stdout, res.stderr

repo_dir = r"c:\Users\johns\DEV\inventory\php-ddd-inventory"

code, stdout, stderr = run("gh pr list --state open --json number,title,headRefName", cwd=repo_dir)
if code != 0:
    print("Error getting PRs:", stderr)
    sys.exit(1)

prs = json.loads(stdout)
print(f"Checking {len(prs)} open PRs...")

conflicts = []
clean = []

for pr in prs:
    branch = pr["headRefName"]
    num = pr["number"]
    title = pr["title"]
    
    # Use git merge-tree to test if master merges cleanly into the PR branch
    # git merge-tree --write-tree master branch
    code_m, out_m, err_m = run(f"git merge-tree master {branch}", cwd=repo_dir)
    
    if code_m != 0 or "CONFLICT" in out_m or "conflict" in out_m.lower():
        conflicts.append({
            "number": num,
            "branch": branch,
            "title": title,
            "output": out_m[:300]
        })
    else:
        clean.append({
            "number": num,
            "branch": branch,
            "title": title
        })

print("\n================ SUMMARY ================")
print(f"Total PRs: {len(prs)}")
print(f"Clean merges ({len(clean)}):")
for cl in clean:
    print(f"  PR #{cl['number']} ({cl['branch']}): {cl['title']}")

print(f"\nConflicts ({len(conflicts)}):")
for c in conflicts:
    print(f"  PR #{c['number']} ({c['branch']}): {c['title']}")

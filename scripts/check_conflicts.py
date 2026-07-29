import subprocess
import json
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=cwd)
    return res.returncode, res.stdout, res.stderr

repo_dir = r"c:\Users\johns\DEV\inventory\php-ddd-inventory"

code, stdout, stderr = run("gh pr list --base master --state open --json number,title,headRefName", cwd=repo_dir)
if code != 0:
    print("Error getting PRs:", stderr)
    sys.exit(1)

prs = json.loads(stdout)
print(f"Checking {len(prs)} open PRs with git merge-tree...")

conflicts = []
clean = []

for pr in prs:
    branch = pr["headRefName"]
    num = pr["number"]
    title = pr["title"]
    
    code_m, out_m, err_m = run(f"git merge-tree origin/master origin/{branch}", cwd=repo_dir)
    
    # Check if output contains conflict markers (like +<<<<<<< or CONFLICT)
    if "CONFLICT" in out_m or "CONFLICT" in err_m or "+<<<<<<<" in out_m or code_m != 0:
        print(f"[CONFLICT] PR #{num} ({branch}): {title}")
        conflicts.append({
            "number": num,
            "branch": branch,
            "title": title,
            "out": out_m[:500]
        })
    else:
        print(f"[CLEAN] PR #{num} ({branch})")
        clean.append({
            "number": num,
            "branch": branch,
            "title": title
        })

print("\n================ SUMMARY ================")
print(f"Total PRs: {len(prs)}")
print(f"Conflicts ({len(conflicts)}):")
for c in conflicts:
    print(f"  PR #{c['number']} ({c['branch']}): {c['title']}")

print(f"\nClean merges ({len(clean)}):")
for cl in clean:
    print(f"  PR #{cl['number']} ({cl['branch']})")

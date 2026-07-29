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
print(f"Found {len(prs)} open PRs.")

conflicts = []
clean = []

for pr in prs:
    branch = pr["headRefName"]
    num = pr["number"]
    title = pr["title"]
    
    run("git merge --abort", cwd=repo_dir)
    run("git rebase --abort", cwd=repo_dir)
    run("git checkout master -f", cwd=repo_dir)
    
    code_co, out_co, err_co = run(f"git checkout \"{branch}\" -f", cwd=repo_dir)
    if code_co != 0:
        code_co, out_co, err_co = run(f"git checkout -b \"{branch}\" \"origin/{branch}\" -f", cwd=repo_dir)
        if code_co != 0:
            print(f"Could not checkout branch {branch}: {err_co}")
            continue

    code_m, out_m, err_m = run("git merge origin/master --no-edit", cwd=repo_dir)
    if code_m != 0:
        print(f"[CONFLICT] PR #{num} ({branch}): {title}")
        # find conflict files
        _, c_out, _ = run("git status --porcelain", cwd=repo_dir)
        conflict_files = [line[3:] for line in c_out.splitlines() if line.startswith("UU ") or line.startswith("AA ") or line.startswith("DD ") or line.startswith("UA ") or line.startswith("AU ")]
        conflicts.append({
            "number": num,
            "branch": branch,
            "title": title,
            "files": conflict_files
        })
        run("git merge --abort", cwd=repo_dir)
    else:
        print(f"[CLEAN] PR #{num} ({branch})")
        clean.append({
            "number": num,
            "branch": branch,
            "title": title
        })

run("git checkout master -f", cwd=repo_dir)

print("\n\n================ SUMMARY ================")
print(f"Total PRs: {len(prs)}")
print(f"Conflicts ({len(conflicts)}):")
for c in conflicts:
    print(f"  PR #{c['number']} ({c['branch']}): files={c['files']}")

print(f"\nClean merges ({len(clean)}):")
for cl in clean:
    print(f"  PR #{cl['number']} ({cl['branch']})")

with open(r"C:\Users\johns\.gemini\antigravity-ide\brain\9cf1cc11-b731-4071-8ca6-d0c321ef3d27\scratch\pr_status.json", "w", encoding="utf-8") as f:
    json.dump({"conflicts": conflicts, "clean": clean}, f, indent=2)

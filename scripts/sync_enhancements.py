import os
import subprocess

BASE_DIR = r"c:\Users\johns\DEV\inventory"

INVARIANTS = """
## 2026-10-07 - Process Streamlining, Sibling Coalescence & Autoloading Invariants
**Learning:**
1. Fragmenting stub methods across multiple micro-PRs on the same class causes unavoidable sibling merge collisions and wasted CI cycles.
2. Placing multiple domain services into a single file breaks Composer PSR-4 autoloader discovery in PHP, triggering fatal `Class not found` errors.
3. Writing service calls against unverified entity methods causes fatal runtime errors.
4. String-escaping markdown journal updates corrupts rendered formatting.

**Action:**
- **Coalesce Micro-PRs**: When implementing or scaffolding related controller endpoints, stub methods, or repository queries on a single class, consolidate all changes into a single coherent pull request. Never create separate fragmented PRs for each individual method of the same class.
- **Strict PSR-4 Isolation in PHP**: In PHP codebases, place every class, interface, and enum in its own file named `<ClassName>.php` matching its namespace path. Never combine multiple domain classes into a single file.
- **Domain Contract Verification**: Always inspect entity and aggregate root definitions to verify exact method and property names before writing service logic or test fixtures.
- **Clean Markdown Formatting**: Always append journal entries using actual newline characters, never literal string escape sequences.
"""

SUBMODULES = [
    ("gql-ddd-inventory", "main"),
    ("js-ddd-inventory", "main"),
    ("php-ddd-inventory", "master"),
    ("python-ddd-inventory", "master"),
    ("react-ddd-inventory-client", "main"),
    ("inventory-python-sidecar", "main"),
]

def run(cmd, cwd=BASE_DIR):
    res = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print(f"Error [{cwd}]: {cmd}\n{res.stderr}")
    else:
        print(f"Success [{cwd}]: {cmd} -> {res.stdout.strip()}")
    return res.returncode == 0

for sub, default_branch in SUBMODULES:
    sub_dir = os.path.join(BASE_DIR, sub)
    print(f"\n=== Processing {sub} ({default_branch}) ===")
    
    # 1. Checkout default branch and pull latest
    run(f"git checkout {default_branch} -f", cwd=sub_dir)
    run(f"git pull origin {default_branch}", cwd=sub_dir)
    
    # 2. Update .jules/*.md
    jdir = os.path.join(sub_dir, ".jules")
    if os.path.isdir(jdir):
        for fname in ["bolt.md", "sentinel.md", "palette.md"]:
            fpath = os.path.join(jdir, fname)
            if os.path.isfile(fpath):
                with open(fpath, "r", encoding="utf-8") as f:
                    c = f.read()
                # Clean escaped strings
                c = c.replace(r"\n\n## Important Process Rules\n- **Do NOT perform whole-file code formatting.** Only apply necessary changes specifically related to the task. Formatting existing, untouched code creates massive PR diffs that are hard to review.\n- **Only write your journal to your matching file (`.jules/bolt.md`).** Do not edit or create journal files for other personas.\n\n\n## Important Process Rules\n- **Only write your journal to your matching file (`.jules/bolt.md`).** Do not edit or create journal files for other personas.\n", "")
                c = c.replace(r"\n\n## Important Process Rules\n- **Do NOT perform whole-file code formatting.** Only apply necessary changes specifically related to the task. Formatting existing, untouched code creates massive PR diffs that are hard to review.\n- **Only write your journal to your matching file (`.jules/sentinel.md`).** Do not edit or create journal files for other personas.\n", "")
                c = c.replace(r"\n\n## Important Process Rules\n- **Do NOT perform whole-file code formatting.** Only apply necessary changes specifically related to the task. Formatting existing, untouched code creates massive PR diffs that are hard to review.\n- **Only write your journal to your matching file (`.jules/bolt.md`).** Do not edit or create journal files for other personas.\n", "")
                if "Process Streamlining, Sibling Coalescence" not in c:
                    c = c.strip() + "\n\n" + INVARIANTS.strip() + "\n"
                with open(fpath, "w", encoding="utf-8", newline="\n") as f:
                    f.write(c)

    # 3. Update bot-guard.yml
    bg_path = os.path.join(sub_dir, ".github", "workflows", "bot-guard.yml")
    if os.path.isfile(bg_path):
        with open(bg_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if "# 4. Reject Destructive Line Deletions in Critical Entrypoints & Schemas" in line:
                new_lines.append(line)
                new_lines.append("          NEW_FILES=$(git diff --name-only --diff-filter=A origin/${{ github.base_ref }}...HEAD | grep -v '^\\.jules/' || true)\n")
                i += 1
                if i < len(lines):
                    new_lines.append(lines[i]) # DELETED_LINES
                    i += 1
                while i < len(lines) and "done" not in lines[i]:
                    i += 1
                if i < len(lines) and "done" in lines[i]:
                    i += 1
                replacement = """          for count in $DELETED_LINES; do
            num=$(echo "$count" | tr -d '-')
            THRESHOLD=15
            # If accompanying modular abstractions/files are introduced in the same PR, allow up to 60 lines for extraction refactors
            if [ -n "$NEW_FILES" ]; then
              THRESHOLD=60
            fi
            if [ "$num" -gt "$THRESHOLD" ]; then
              echo "❌ ERROR: PR deletes $num lines from a core schema or entrypoint file, exceeding safety threshold (max $THRESHOLD)."
              exit 1
            fi
          done
"""
                new_lines.append(replacement)
            else:
                new_lines.append(line)
                i += 1
        with open(bg_path, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(new_lines)

    # 4. Special check for phpunit.yml
    if sub == "php-ddd-inventory":
        pu_path = os.path.join(sub_dir, ".github", "workflows", "phpunit.yml")
        if os.path.isfile(pu_path):
            with open(pu_path, "r", encoding="utf-8") as f:
                pu_content = f.read()
            pu_content = pu_content.replace(
                "composer install --no-interaction --prefer-dist --no-scripts\n",
                "composer install --no-interaction --prefer-dist --no-scripts --optimize-autoloader\n"
            )
            with open(pu_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(pu_content)

    # 5. Commit and push
    run("git add -A", cwd=sub_dir)
    res_diff = subprocess.run("git diff --cached --quiet", cwd=sub_dir, shell=True)
    if res_diff.returncode != 0:
        run('git commit -m "ci: enhance bot guardrail with modular extraction whitelist and update Jules directives"', cwd=sub_dir)
        run(f"git push origin {default_branch}", cwd=sub_dir)
    else:
        print(f"No changes to commit in {sub}")

# Update root repository .jules and bot-guard
print("\n=== Processing Parent Repository ===")
root_jdir = os.path.join(BASE_DIR, ".jules")
for fname in ["bolt.md", "sentinel.md"]:
    fpath = os.path.join(root_jdir, fname)
    if os.path.isfile(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            c = f.read()
        c = c.replace(r"\n\n## Important Process Rules\n- **Do NOT perform whole-file code formatting.** Only apply necessary changes specifically related to the task. Formatting existing, untouched code creates massive PR diffs that are hard to review.\n- **Only write your journal to your matching file (`.jules/bolt.md`).** Do not edit or create journal files for other personas.\n\n\n## Important Process Rules\n- **Only write your journal to your matching file (`.jules/bolt.md`).** Do not edit or create journal files for other personas.\n", "")
        c = c.replace(r"\n\n## Important Process Rules\n- **Do NOT perform whole-file code formatting.** Only apply necessary changes specifically related to the task. Formatting existing, untouched code creates massive PR diffs that are hard to review.\n- **Only write your journal to your matching file (`.jules/sentinel.md`).** Do not edit or create journal files for other personas.\n", "")
        if "Process Streamlining, Sibling Coalescence" not in c:
            c = c.strip() + "\n\n" + INVARIANTS.strip() + "\n"
        with open(fpath, "w", encoding="utf-8", newline="\n") as f:
            f.write(c)

bg_path = os.path.join(BASE_DIR, ".github", "workflows", "bot-guard.yml")
if os.path.isfile(bg_path):
    with open(bg_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "# 4. Reject Destructive Line Deletions in Critical Entrypoints & Schemas" in line:
            new_lines.append(line)
            new_lines.append("          NEW_FILES=$(git diff --name-only --diff-filter=A origin/${{ github.base_ref }}...HEAD | grep -v '^\\.jules/' || true)\n")
            i += 1
            if i < len(lines):
                new_lines.append(lines[i])
                i += 1
            while i < len(lines) and "done" not in lines[i]:
                i += 1
            if i < len(lines) and "done" in lines[i]:
                i += 1
            replacement = """          for count in $DELETED_LINES; do
            num=$(echo "$count" | tr -d '-')
            THRESHOLD=15
            # If accompanying modular abstractions/files are introduced in the same PR, allow up to 60 lines for extraction refactors
            if [ -n "$NEW_FILES" ]; then
              THRESHOLD=60
            fi
            if [ "$num" -gt "$THRESHOLD" ]; then
              echo "❌ ERROR: PR deletes $num lines from a core schema or entrypoint file, exceeding safety threshold (max $THRESHOLD)."
              exit 1
            fi
          done
"""
            new_lines.append(replacement)
        else:
            new_lines.append(line)
            i += 1
    with open(bg_path, "w", encoding="utf-8", newline="\n") as f:
        f.writelines(new_lines)

run("git add -A", cwd=BASE_DIR)
res_diff = subprocess.run("git diff --cached --quiet", cwd=BASE_DIR, shell=True)
if res_diff.returncode != 0:
    run('git commit -m "ci: enhance bot guardrails, streamline Jules directives, and sync submodule pointers"', cwd=BASE_DIR)
    run("git push origin main", cwd=BASE_DIR)

print("\nAll submodules and parent repo synchronized!")

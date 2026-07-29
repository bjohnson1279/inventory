import os
import subprocess

dirs_to_check = [
    r"c:\Users\johns\DEV\inventory\php-ddd-inventory\src",
    r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests",
    r"c:\Users\johns\DEV\inventory\php-ddd-inventory\scripts"
]

for d in dirs_to_check:
    for root, dirs, files in os.walk(d):
        for f in files:
            if f.endswith(".php"):
                path = os.path.join(root, f)
                res = subprocess.run(["php", "-l", path], capture_output=True, text=True)
                if res.returncode != 0:
                    print(f"SYNTAX ERROR in {path}:\n{res.stdout}\n{res.stderr}")

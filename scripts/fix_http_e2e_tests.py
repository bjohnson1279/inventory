import os
import re

http_dir = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http"
ext_dir = r"C:\Users\johns\AppData\Local\Microsoft\WinGet\Packages\PHP.PHP.8.1_Microsoft.Winget.Source_8wekyb3d8bbwe\ext"

for filename in os.listdir(http_dir):
    if not filename.endswith(".php"):
        continue
    filepath = os.path.join(http_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "setUpBeforeClass" not in content or "proc_open" not in content:
        continue

    # Fix extDir logic inside PHP code string
    target = "$extDir = ini_get('extension_dir') ?: "
    replacement = "$extDir = "
    content = content.replace(target, replacement)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Fixed extDir in {filename}")

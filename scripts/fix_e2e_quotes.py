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

    if "setUpBeforeClass" not in content:
        continue

    target_pattern = r'\$phpExec = PHP_BINARY \. \'.*?\';'
    m = re.search(target_pattern, content)
    if m:
        repl = f'$phpExec = PHP_BINARY . \' -d extension_dir="{ext_dir}" -d extension=pdo -d extension=mbstring -d extension=pdo_sqlite\';'
        content = content[:m.start()] + repl + content[m.end():]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated phpExec in {filename}")

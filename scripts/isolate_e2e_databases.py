import os

http_dir = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http"

for filename in os.listdir(http_dir):
    if not filename.endswith(".php"):
        continue
    filepath = os.path.join(http_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "setUpBeforeClass" not in content or "proc_open" not in content:
        continue

    content = content.replace("Manager::getInstance();", "new \\Illuminate\\Database\\Capsule\\Manager();")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Fixed Capsule in {filename}")

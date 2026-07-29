import os

http_dir = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http"

for filename in os.listdir(http_dir):
    if not filename.endswith(".php"):
        continue
    filepath = os.path.join(http_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if "setUpBeforeClass" not in content:
        continue

    content = content.replace("\\Illuminate\\Database\\Capsule\\new \\Illuminate\\Database\\Capsule\\Manager()", "new Capsule")
    content = content.replace("new \\Illuminate\\Database\\Capsule\\Manager()", "new Capsule")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Cleaned Capsule in {filename}")

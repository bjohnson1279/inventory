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

    content = content.replace("$capsule = new Capsule;", "$capsule = new \\Illuminate\\Database\\Capsule\\Manager();")
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Fixed Capsule in {filename}")

# Also update DatabaseQueueTest.php and DatabaseOutboxWorkerTest.php setUp()
queue_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Queue\DatabaseQueueTest.php"
with open(queue_path, "r", encoding="utf-8") as f:
    qcontent = f.read()

if "Capsule::table('queued_jobs')->delete();" not in qcontent:
    qtarget = "protected function setUp(): void\n    {"
    qrepl = "protected function setUp(): void\n    {\n        Capsule::table('queued_jobs')->delete();\n        Capsule::table('outbox_messages')->delete();"
    qcontent = qcontent.replace(qtarget, qrepl)
    with open(queue_path, "w", encoding="utf-8") as f:
        f.write(qcontent)
    print("Added table cleanup to DatabaseQueueTest.php")

outbox_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Queue\DatabaseOutboxWorkerTest.php"
with open(outbox_path, "r", encoding="utf-8") as f:
    ocontent = f.read()

if "Capsule::table('outbox_messages')->delete();" not in ocontent:
    otarget = "protected function setUp(): void\n    {"
    orepl = "protected function setUp(): void\n    {\n        Capsule::table('queued_jobs')->delete();\n        Capsule::table('outbox_messages')->delete();"
    ocontent = ocontent.replace(otarget, orepl)
    with open(outbox_path, "w", encoding="utf-8") as f:
        f.write(ocontent)
    print("Added table cleanup to DatabaseOutboxWorkerTest.php")

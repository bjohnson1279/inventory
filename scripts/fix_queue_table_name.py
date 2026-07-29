import os

for qfile in ["DatabaseQueueTest.php", "DatabaseOutboxWorkerTest.php"]:
    path = os.path.join(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Queue", qfile)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    content = content.replace("Capsule::table('outbox_messages')->delete();", "Capsule::table('outbox_events')->delete();")
    
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated outbox_events in {qfile}")

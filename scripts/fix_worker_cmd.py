import os

dq_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Queue\DatabaseQueueTest.php"
with open(dq_path, "r", encoding="utf-8") as f:
    content = f.read()

target1 = 'exec($cmd, $output, $resultCode);'
replacement1 = 'DB::disconnect();\n        exec($cmd, $output, $resultCode);\n        DB::reconnect();'
content = content.replace(target1, replacement1)

with open(dq_path, "w", encoding="utf-8") as f:
    f.write(content)

do_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Queue\DatabaseOutboxWorkerTest.php"
with open(do_path, "r", encoding="utf-8") as f:
    content2 = f.read()

content2 = content2.replace(target1, replacement1)

with open(do_path, "w", encoding="utf-8") as f:
    f.write(content2)

print("Added DB::disconnect() and DB::reconnect() around exec calls!")

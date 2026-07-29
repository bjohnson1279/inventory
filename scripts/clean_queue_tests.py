import os
import re

for test_file in ["DatabaseQueueTest.php", "DatabaseOutboxWorkerTest.php"]:
    path = os.path.join(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Queue", test_file)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Fix line 59/60 construction cleanly
    db_expr = "$dbFile = getenv('DB_DATABASE') ?: ($baseDir . '/storage/data/test.sqlite');"
    
    # Replace $cmd construction in both files
    old_cmd_block = r'\$cmd = \(PHP_OS_FAMILY === \'Windows\'\).*?;'
    new_cmd_block = '''$dbFile = getenv('DB_DATABASE') ?: ($baseDir . '/storage/data/test.sqlite');
        $cmd = (PHP_OS_FAMILY === 'Windows')
            ? "set DB_CONNECTION=sqlite&& set DB_DATABASE={$dbFile}&& " . $phpExec . " " . $baseDir . "/scripts/" . (str_contains(__FILE__, 'Outbox') ? "outbox-worker.php" : "queue-worker.php") . " --once"
            : "DB_CONNECTION=sqlite DB_DATABASE=" . escapeshellarg($dbFile) . " " . $phpExec . " " . $baseDir . "/scripts/" . (str_contains(__FILE__, 'Outbox') ? "outbox-worker.php" : "queue-worker.php") . " --once";'''
    
    content = re.sub(old_cmd_block, new_cmd_block, content, flags=re.DOTALL)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Cleaned up {test_file}")

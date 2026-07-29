path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\src\Infrastructure\Persistence\bootstrap_database.php"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = "if ($driver === 'sqlite') {\n    require_once __DIR__ . '/sqlite_setup.php';"
replacement = "if ($driver === 'sqlite') {\n    try {\n        $capsule->getConnection()->statement('PRAGMA journal_mode=WAL;');\n        $capsule->getConnection()->statement('PRAGMA busy_timeout=10000;');\n    } catch (\\Exception $e) {}\n    require_once __DIR__ . '/sqlite_setup.php';"

content = content.replace(target, replacement)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Updated bootstrap_database.php with WAL mode")

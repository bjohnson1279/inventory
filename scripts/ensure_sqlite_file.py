def add_touch(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    target = "$capsule->addConnection(["
    replacement = """if ($dbPath !== ':memory:') {
        $dir = dirname($dbPath);
        if (!is_dir($dir)) {
            @mkdir($dir, 0777, true);
        }
        if (!file_exists($dbPath)) {
            @touch($dbPath);
        }
    }
    $capsule->addConnection(["""
    
    if target in content and "@touch($dbPath)" not in content:
        content = content.replace(target, replacement, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Added touch check to {path}")

add_touch(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\bootstrap.php")
add_touch(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\src\Infrastructure\Persistence\bootstrap_database.php")

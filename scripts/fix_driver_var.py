def fix(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "$driver = getenv('DB_CONNECTION')" not in content:
        target = "$capsule = new Capsule"
        replacement = "$driver = getenv('DB_CONNECTION') ?: 'sqlite';\n$capsule = new Capsule"
        content = content.replace(target, replacement)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Fixed $driver in {path}")

fix(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\public\index.php")
fix(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\bootstrap.php")
fix(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\src\Infrastructure\Persistence\bootstrap_database.php")

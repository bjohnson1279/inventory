path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\public\index.php"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

target = "$capsule = new Capsule;"
replacement = "error_log('DEBUG_DRIVER: driver=' . var_export($driver, true) . ', DB_CONN=' . var_export(getenv('DB_CONNECTION'), true) . ', pdo_sqlite=' . var_export(extension_loaded('pdo_sqlite'), true) . ', pdo_pgsql=' . var_export(extension_loaded('pdo_pgsql'), true));\n$capsule = new Capsule;"

if target in content:
    content = content.replace(target, replacement)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Added debug log to public/index.php")

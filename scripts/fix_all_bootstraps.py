import re

def patch_file(path, rel):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    content = content.replace('\r\n', '\n')
    
    target_pattern = r'if \(!getenv\(\'DB_CONNECTION\'\).*?\n\}'
    
    replacement = """$connType = getenv('DB_CONNECTION') ?: 'pgsql';
if ($connType === 'pgsql') {
    $pgHost = getenv('DB_HOST') ?: 'db';
    $pgPort = (int)(getenv('DB_PORT') ?: 5432);
    $canConnectPg = extension_loaded('pdo_pgsql') && @fsockopen($pgHost, $pgPort, $errno, $errstr, 0.1);
    if (!$canConnectPg) {
        putenv('DB_CONNECTION=sqlite');
        $_ENV['DB_CONNECTION'] = 'sqlite';
        $_SERVER['DB_CONNECTION'] = 'sqlite';
    }
}"""

    if "if ($connType === 'pgsql')" not in content:
        m = re.search(target_pattern, content, flags=re.DOTALL)
        if m:
            content = content[:m.start()] + replacement + content[m.end():]

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {path}")

patch_file(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\public\index.php", "/../")
patch_file(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\bootstrap.php", "/../../")
patch_file(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\src\Infrastructure\Persistence\bootstrap_database.php", "/../../../")

import re

def update_file(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().replace('\r\n', '\n')

    # Match from Dotenv safeLoad up to Capsule initialization
    pattern = r'(\$dotenv->safeLoad\(\);.*?)(\$capsule = new Capsule;|\$capsule = new Capsule\(\);)'
    
    replacement_logic = """$driver = getenv('DB_CONNECTION') ?: 'pgsql';
if ($driver === 'pgsql') {
    if (!extension_loaded('pdo_pgsql')) {
        $driver = 'sqlite';
    } else {
        $pgHost = getenv('DB_HOST') ?: 'db';
        $pgPort = (int)(getenv('DB_PORT') ?: 5432);
        $fp = @fsockopen($pgHost, $pgPort, $errno, $errstr, 0.1);
        if (!$fp) {
            $driver = 'sqlite';
        } else {
            fclose($fp);
        }
    }
}

if ($driver === 'sqlite') {
    putenv('DB_CONNECTION=sqlite');
    $_ENV['DB_CONNECTION'] = 'sqlite';
    $_SERVER['DB_CONNECTION'] = 'sqlite';
}

\\2"""

    m = re.search(r'\$dotenv->safeLoad\(\);.*?(?=\$capsule = new Capsule)', content, flags=re.DOTALL)
    if m:
        before = content[:m.start()] + "$dotenv->safeLoad();\n\n"
        after = content[m.end():]
        new_content = before + """$driver = getenv('DB_CONNECTION') ?: 'pgsql';
if ($driver === 'pgsql') {
    if (!extension_loaded('pdo_pgsql')) {
        $driver = 'sqlite';
    } else {
        $pgHost = getenv('DB_HOST') ?: 'db';
        $pgPort = (int)(getenv('DB_PORT') ?: 5432);
        $fp = @fsockopen($pgHost, $pgPort, $errno, $errstr, 0.1);
        if (!$fp) {
            $driver = 'sqlite';
        } else {
            fclose($fp);
        }
    }
}

if ($driver === 'sqlite') {
    putenv('DB_CONNECTION=sqlite');
    $_ENV['DB_CONNECTION'] = 'sqlite';
    $_SERVER['DB_CONNECTION'] = 'sqlite';
}\n\n""" + after
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Successfully updated {path}")

update_file(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\public\index.php")
update_file(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\bootstrap.php")
update_file(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\src\Infrastructure\Persistence\bootstrap_database.php")

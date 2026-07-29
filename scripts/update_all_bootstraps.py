def fix_bootstrap(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    for line in lines:
        if "$driver = getenv('DB_CONNECTION') ?: 'pgsql';" in line or "$driver = getenv('DB_CONNECTION') ?: 'sqlite';" in line or "$driver = $envDriver" in line:
            new_lines.append("if (!getenv('DB_CONNECTION') || (getenv('DB_CONNECTION') === 'pgsql' && !extension_loaded('pdo_pgsql'))) {\n")
            new_lines.append("    putenv('DB_CONNECTION=sqlite');\n")
            new_lines.append("    $_ENV['DB_CONNECTION'] = 'sqlite';\n")
            new_lines.append("    $_SERVER['DB_CONNECTION'] = 'sqlite';\n")
            new_lines.append("}\n")
            new_lines.append("$driver = getenv('DB_CONNECTION') ?: 'sqlite';\n")
        elif "$envDriver = getenv('DB_CONNECTION');" in line or "if ($driver === 'pgsql' && !extension_loaded('pdo_pgsql'))" in line:
            continue
        else:
            new_lines.append(line)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

fix_bootstrap(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\bootstrap.php")
fix_bootstrap(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\src\Infrastructure\Persistence\bootstrap_database.php")
print("Both bootstraps fixed!")

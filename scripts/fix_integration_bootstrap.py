file_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\bootstrap.php"
with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "$driver = getenv('DB_CONNECTION') ?: 'pgsql';" in line:
        new_lines.append("$envDriver = getenv('DB_CONNECTION');\n")
        new_lines.append("$driver = $envDriver ?: (getenv('DB_CONNECTION') ?: 'sqlite');\n")
        new_lines.append("if ($driver === 'pgsql' && !extension_loaded('pdo_pgsql')) {\n")
        new_lines.append("    $driver = 'sqlite';\n")
        new_lines.append("}\n")
    else:
        new_lines.append(line)

with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Updated tests/Integration/bootstrap.php successfully")

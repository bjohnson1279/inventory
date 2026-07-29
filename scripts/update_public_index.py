path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\public\index.php"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "$driver = getenv('DB_CONNECTION') ?: 'pgsql';" in line or "$driver = getenv('DB_CONNECTION') ?: 'sqlite';" in line:
        new_lines.append("if (!getenv('DB_CONNECTION') || (getenv('DB_CONNECTION') === 'pgsql' && !extension_loaded('pdo_pgsql'))) {\n")
        new_lines.append("    putenv('DB_CONNECTION=sqlite');\n")
        new_lines.append("    $_ENV['DB_CONNECTION'] = 'sqlite';\n")
        new_lines.append("    $_SERVER['DB_CONNECTION'] = 'sqlite';\n")
        new_lines.append("}\n")
        new_lines.append("$driver = getenv('DB_CONNECTION') ?: 'sqlite';\n")
    else:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Updated public/index.php successfully!")

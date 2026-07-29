def clean_file(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    new_lines = []
    skip = False
    for i, line in enumerate(lines):
        if "$driver = getenv('DB_CONNECTION') ?: 'sqlite';" in line:
            new_lines.append(line)
            # check if next lines are leftover `$driver = 'sqlite';` and `}`
            if i + 1 < len(lines) and "$driver = 'sqlite';" in lines[i+1]:
                skip = True
            continue
        if skip:
            if "}" in line:
                skip = False
            continue
        new_lines.append(line)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

clean_file(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\bootstrap.php")
clean_file(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\src\Infrastructure\Persistence\bootstrap_database.php")
print("Cleaned up!")

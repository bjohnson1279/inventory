import os
import re

# 1. Fix AuditE2ETest line 87 (remove audit_logs delete)
audit_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http\AuditE2ETest.php"
with open(audit_path, "r", encoding="utf-8") as f:
    acontent = f.read()

acontent = acontent.replace("Capsule::table('audit_logs')->delete();\n", "")
with open(audit_path, "w", encoding="utf-8") as f:
    f.write(acontent)
print("Fixed AuditE2ETest.php")

# 2. Fix ApiEndpointsTest line 534 (insertOrIgnore shopify_location_mappings)
api_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http\ApiEndpointsTest.php"
with open(api_path, "r", encoding="utf-8") as f:
    apicontent = f.read()

apicontent = apicontent.replace(
    "\\Illuminate\\Database\\Capsule\\Manager::table('shopify_location_mappings')->insert([",
    "\\Illuminate\\Database\\Capsule\\Manager::table('shopify_location_mappings')->insertOrIgnore(["
)
with open(api_path, "w", encoding="utf-8") as f:
    f.write(apicontent)
print("Fixed ApiEndpointsTest.php")

# 3. Fix DatabaseQueueTest and DatabaseOutboxWorkerTest DB_DATABASE in worker commands
for test_file in ["DatabaseQueueTest.php", "DatabaseOutboxWorkerTest.php"]:
    path = os.path.join(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Queue", test_file)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace hardcoded test.sqlite paths with getenv('DB_DATABASE')
    # Windows pattern: set DB_DATABASE=" . $baseDir . "/storage/data/test.sqlite&&
    # or set DB_DATABASE=" . ($baseDir === "/" ? "" : $baseDir) . "/storage/data/test.sqlite&&
    
    content = re.sub(
        r'set DB_DATABASE=" \. [^\&]+\&\&',
        r'set DB_DATABASE=" . (getenv(\'DB_DATABASE\') ?: ($baseDir . "/storage/data/test.sqlite")) . "&&',
        content
    )
    content = re.sub(
        r'DB_DATABASE=" \. [^ ]+ ',
        r'DB_DATABASE=" . (getenv(\'DB_DATABASE\') ?: ($baseDir . "/storage/data/test.sqlite")) . " ',
        content
    )

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Fixed worker database paths in {test_file}")

import os

# 1. Fix imports in Queue tests
for qfile in ["DatabaseQueueTest.php", "DatabaseOutboxWorkerTest.php"]:
    path = os.path.join(r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Queue", qfile)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "use Illuminate\Database\Capsule\Manager as Capsule;" not in content:
        content = content.replace("namespace Tests\\Integration\\Queue;\n", "namespace Tests\\Integration\\Queue;\n\nuse Illuminate\\Database\\Capsule\\Manager as Capsule;\n")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Added Capsule import to {qfile}")

# 2. Fix AuditE2ETest setup
audit_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http\AuditE2ETest.php"
with open(audit_path, "r", encoding="utf-8") as f:
    acontent = f.read()

if "Capsule::table('catalog_variants')->delete();" not in acontent:
    acontent = acontent.replace("protected function setUp(): void\n    {", "protected function setUp(): void\n    {\n        Capsule::table('catalog_variants')->delete();\n        Capsule::table('catalog_products')->delete();\n        Capsule::table('audit_logs')->delete();")
    with open(audit_path, "w", encoding="utf-8") as f:
        f.write(acontent)
    print("Added table cleanup to AuditE2ETest.php")

# 3. Fix WarehouseLocationE2ETest setup
wh_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http\WarehouseLocationE2ETest.php"
with open(wh_path, "r", encoding="utf-8") as f:
    whcontent = f.read()

if "Capsule::table('warehouse_locations')->delete();" not in whcontent:
    whcontent = whcontent.replace("protected function setUp(): void\n    {", "protected function setUp(): void\n    {\n        Capsule::table('warehouse_locations')->delete();\n        Capsule::table('product_locations')->delete();")
    with open(wh_path, "w", encoding="utf-8") as f:
        f.write(whcontent)
    print("Added table cleanup to WarehouseLocationE2ETest.php")

# 4. Fix WebhookSubscriptionTest worker command
web_path = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http\WebhookSubscriptionTest.php"
with open(web_path, "r", encoding="utf-8") as f:
    webcontent = f.read()

ext_dir = r"C:\Users\johns\AppData\Local\Microsoft\WinGet\Packages\PHP.PHP.8.1_Microsoft.Winget.Source_8wekyb3d8bbwe\ext"
php_bin = r"C:\Users\johns\AppData\Local\Microsoft\WinGet\Packages\PHP.PHP.8.1_Microsoft.Winget.Source_8wekyb3d8bbwe\php.exe"

old_cmd_pattern = r'\$cmd = "php scripts/webhook-worker\.php.*?";'
new_cmd = f'$cmd = (PHP_OS_FAMILY === "Windows" ? "set DB_CONNECTION=sqlite&& set DB_DATABASE=" . escapeshellarg($dbPath) . "&& " . escapeshellarg("{php_bin}") . " -d extension_dir=" . escapeshellarg("{ext_dir}") . " -d extension=mbstring -d extension=pdo_sqlite scripts/webhook-worker.php > tests/Integration/Http/worker_webhook.log 2>&1" : "DB_CONNECTION=sqlite DB_DATABASE=" . escapeshellarg($dbPath) . " php scripts/webhook-worker.php > tests/Integration/Http/worker_webhook.log 2>&1 &");'

import re
if re.search(old_cmd_pattern, webcontent):
    webcontent = re.sub(old_cmd_pattern, new_cmd, webcontent)
    with open(web_path, "w", encoding="utf-8") as f:
        f.write(webcontent)
    print("Updated worker command in WebhookSubscriptionTest.php")

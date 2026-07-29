import os
import re

http_dir = r"c:\Users\johns\DEV\inventory\php-ddd-inventory\tests\Integration\Http"

port_map = {
    'ApiEndpointsTest.php': 8085,
    'PurchaseOrderE2ETest.php': 8086,
    'AllocationsE2ETest.php': 8087,
    'ReorderPolicyE2ETest.php': 8088,
    'ReportControllerTest.php': 8089,
    'ForecastingE2ETest.php': 8090,
    'ReturnsE2ETest.php': 8091,
    'WarehouseLocationE2ETest.php': 8092,
    'FefoRecallE2ETest.php': 8093,
    'ComplianceE2ETest.php': 8094,
    'AuditE2ETest.php': 8095,
    'ShippingCarrierE2ETest.php': 8096,
    'WebhookSubscriptionTest.php': 8097,
}

for filename, port in port_map.items():
    filepath = os.path.join(http_dir, filename)
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace 127.0.0.1:\d+ and http://127.0.0.1:\d+ with the assigned port
    content = re.sub(r'127\.0\.0\.1:\d+', f'127.0.0.1:{port}', content)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Assigned port {port} to {filename}")

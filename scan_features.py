import os
import json

backends = [
    'js-ddd-inventory',
    'gql-ddd-inventory',
    'php-ddd-inventory',
    'python-ddd-inventory'
]

features = {
    'RBAC & Permissions (Sec 12)': ['rbac', 'permission', 'role', 'auth'],
    'Approval Workflows (Sec 12)': ['approval', 'workflow'],
    'Reporting & Analytics (Sec 13)': ['report', 'analytic', 'export'],
    'Omnichannel (Sec 14)': ['omnichannel', 'channel', 'shopify', 'amazon', 'woocommerce'],
}

def scan_backend(backend):
    found_features = {f: {'src': 0, 'tests': 0} for f in features}
    
    for root, dirs, files in os.walk(backend):
        dirs[:] = [d for d in dirs if d not in ('node_modules', 'vendor', '.git', '__pycache__', 'dist', 'build')]
        for name in files:
            path = os.path.join(root, name).lower()
            is_test = 'test' in path or 'spec' in path
            for f_name, keywords in features.items():
                if any(kw in path for kw in keywords):
                    if is_test:
                        found_features[f_name]['tests'] += 1
                    else:
                        found_features[f_name]['src'] += 1
    return found_features

results = {}
for b in backends:
    results[b] = scan_backend(b)

print(json.dumps(results, indent=2))

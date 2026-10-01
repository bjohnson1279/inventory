import os
import json

backend = 'js-ddd-inventory'

files_found = []

for root, dirs, files in os.walk(backend):
    dirs[:] = [d for d in dirs if d not in ('node_modules', 'vendor', '.git', '__pycache__', 'dist', 'build')]
    for name in files:
        path = os.path.join(root, name).lower()
        if any(kw in path for kw in ['report', 'analytic', 'dashboard']):
            files_found.append(os.path.join(root, name))

print(json.dumps(files_found, indent=2))

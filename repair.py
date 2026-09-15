import re

with open('js-ddd-inventory/prisma/schema.prisma', 'r') as f:
    text = f.read()

# Fix duplicates:
# Remove everything from line 11 to 17
# Remove duplicate datasource db
lines = text.split('\n')

valid_lines = []
skip = False
for i, line in enumerate(lines):
    if line.strip() == 'datasource db {' and any('datasource db {' in l for l in valid_lines):
        skip = True
    
    if skip:
        if line.strip() == '}':
            skip = False
        continue

    valid_lines.append(line)

new_text = '\n'.join(valid_lines)
# Check for duplicate InventoryModel
seen_models = set()
final_lines = []
in_model = False
model_name = ''
skip_model = False

for line in new_text.split('\n'):
    m = re.match(r'^model\s+(\w+)\s*\{', line)
    if m:
        in_model = True
        model_name = m.group(1)
        if model_name in seen_models:
            skip_model = True
        else:
            seen_models.add(model_name)
            skip_model = False
            
    if skip_model:
        if line.strip() == '}':
            in_model = False
            skip_model = False
        continue
        
    final_lines.append(line)

final_text = '\n'.join(final_lines)

# Remove the dangling lines 11-17 manually by regex
final_text = re.sub(r'\}\n\s+id\s+String\s+@id[^{]*?@@unique\(\[id\]\)\n\}', '}', final_text, flags=re.MULTILINE)
# Sometimes it's dangling:
final_text = re.sub(r'\}\n\s+id\s+String.*?@@unique\(\[id\]\)\n\}', '}', final_text, flags=re.DOTALL)

with open('js-ddd-inventory/prisma/schema.prisma', 'w') as f:
    f.write(final_text)

print('Repaired schema.')

import re

with open('js-ddd-inventory/prisma/schema.prisma', 'r') as f:
    lines = f.readlines()

clean_lines = []
skip_next = 0
for i, line in enumerate(lines):
    if skip_next > 0:
        skip_next -= 1
        continue
    # Check for hanging closing brace on line 10
    if i == 9 and line.strip() == '}':
        # Let's inspect around it.
        pass
    clean_lines.append(line)

# Let's just print the first 20 lines to see exactly what's wrong.
for i, l in enumerate(lines[:30]):
    print(f'{i+1:02d}: {l.rstrip()}')

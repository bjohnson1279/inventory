file_path = "c:/Users/johns/DEV/inventory/js-ddd-inventory/prisma/schema.prisma"
with open(file_path, 'r') as f:
    lines = f.readlines()

out_lines = []
for line in lines:
    # If the line has '[]' and '@map', it's a relation field. Remove the @map.
    if '[]' in line and '@map' in line:
        line = line.split('@map')[0].rstrip() + '\n'
    out_lines.append(line)

with open(file_path, 'w') as f:
    f.writelines(out_lines)

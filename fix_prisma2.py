file_path = "c:/Users/johns/DEV/inventory/js-ddd-inventory/prisma/schema.prisma"
with open(file_path, 'r') as f:
    lines = f.readlines()

out_lines = []
in_model = ""
for line in lines:
    if line.startswith("model "):
        in_model = line.split()[1]
    
    if "@@map" in line:
        if in_model == "Tenant":
            line = line.replace('"tenants"', '"tenants_legacy"')
        elif in_model == "ApiToken":
            line = line.replace('"api_tokens"', '"api_tokens_legacy"')
        elif in_model == "RmaItem":
            line = line.replace('"rma_items"', '"rma_items_legacy"')
            
    out_lines.append(line)

with open(file_path, 'w') as f:
    f.writelines(out_lines)

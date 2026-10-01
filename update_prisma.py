import re

def to_snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

def process_prisma(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    out_lines = []
    in_model = False
    model_name = ""
    has_map = False
    
    for line in lines:
        if line.strip().startswith('model '):
            in_model = True
            model_name = line.strip().split()[1]
            has_map = False
            out_lines.append(line)
            continue
            
        if in_model and line.strip().startswith('@@map'):
            has_map = True
            
        if in_model and line.strip() == '}':
            if not has_map:
                snake_name = to_snake_case(model_name)
                # Remove 'Model' suffix if present
                if snake_name.endswith('_model'):
                    snake_name = snake_name[:-6]
                if snake_name.endswith('_models'):
                    snake_name = snake_name[:-7]
                # pluralize naive
                if not snake_name.endswith('s'):
                    if snake_name.endswith('y'):
                        snake_name = snake_name[:-1] + 'ies'
                    else:
                        snake_name += 's'
                        
                out_lines.append(f'  @@map("{snake_name}")\n')
            in_model = False
            out_lines.append(line)
            continue
            
        if in_model and not line.strip().startswith('//') and not line.strip().startswith('@@'):
            # Field parsing
            parts = line.split()
            if len(parts) >= 2 and not line.strip().startswith('@@'):
                field_name = parts[0]
                field_type = parts[1]
                
                # Check if field name is camelCase and doesn't already have @map
                if re.search(r'[A-Z]', field_name) and '@map(' not in line and '@relation' not in line:
                    snake_field = to_snake_case(field_name)
                    # insert @map("snake_field") before other attributes or at the end
                    if '//' in line:
                        code_part, comment_part = line.split('//', 1)
                        code_part = code_part.rstrip() + f' @map("{snake_field}") '
                        line = code_part + '//' + comment_part
                    else:
                        line = line.rstrip() + f' @map("{snake_field}")\n'
        
        out_lines.append(line)

    with open(file_path, 'w') as f:
        f.writelines(out_lines)

process_prisma("c:/Users/johns/DEV/inventory/js-ddd-inventory/prisma/schema.prisma")
print("Prisma schema updated.")

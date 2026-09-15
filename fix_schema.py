import re

with open('js-ddd-inventory/prisma/schema.prisma', 'r') as f:
    text = f.read()

replacement = '''model SerializedItemModel {
  id           String                  @id
  serialNumber String
  sku          String
  status       String
  locationId   String
  tenantId     String
  registeredAt DateTime                @default(now())
  transitions  StatusTransitionModel[]
  
  @@unique([serialNumber, tenantId])
}'''

text = text.replace('''model SerializedItemModel {
  id           String                  @id
}''', replacement)

with open('js-ddd-inventory/prisma/schema.prisma', 'w') as f:
    f.write(text)

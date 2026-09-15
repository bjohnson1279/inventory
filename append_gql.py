import os

with open('gql-ddd-inventory/prisma/schema.prisma', 'a') as f:
    f.write('''
model CycleCountPlanModel {
  id                String   @id @default(uuid())
  tenantId          String
  name              String
  abcClassification String
  frequencyDays     Int
  zone              String?
  isActive          Boolean  @default(true)
  createdAt         DateTime @default(now())
}

model CycleCountRecordModel {
  id                String   @id @default(uuid())
  tenantId          String
  planId            String?
  name              String
  status            String
  abcClassification String
  zone              String?
  isBlindCount      Boolean  @default(true)
  createdAt         DateTime @default(now())
}
''')

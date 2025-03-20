import csv

INPUT_CSV = 'cleaned_codes.csv'

with open(INPUT_CSV, 'r', encoding='utf-8') as fin:
    reader = csv.DictReader(fin)
    lines = []
    for row in reader:
        code = row['ota_booking_code']  # Adjust column name if different
        lines.append(f"SELECT '{code}' AS code")

# Build the final block with UNION ALL
union_block = "\nUNION ALL\n".join(lines)
print("-- Paste this into your query:\n")
print(union_block)

import csv

totals = {}

with open("transactions.csv", newline="") as file:
	reader = csv.DictReader(file)
	for row in reader:
		category = row["category"].strip()
		amount = float(row["amount"])
		totals[category] = totals.get(category,0) + amount
for category, total in sorted(totals.items(), key=lambda item: item[1], reverse=True):
	print(f"{category}: ${total:.2f}")

print(f"Total: ${sum(totals.values()):.2f}")
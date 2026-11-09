# Expense Categorizer (P1, legacy)

> **This is the original P1 project, kept for history.** SEWE Finance
> (the rest of this repo) grew out of it. **All data in `transactions.csv`
> is invented**: merchants, amounts, dates and names are sample values,
> not anyone's real statement.

A Python script that reads a CSV of transactions and prints total spending
per category, sorted highest to lowest, with a grand total.

## How to run

From this folder:

```bash
python categorize.py
```

Requires Python 3. No external packages.

## Sample output

```
$ python categorize.py
Rent: $3000.00
Food: $492.00
Shopping: $300.00
Entertainment: $25.00
Transportation: $14.25
Total: $3831.25
```

## Notes

The source CSV has inconsistent spacing after commas, so some category
values arrive as " Food" instead of "Food". The script calls `.strip()` on
each one, which removes the surrounding whitespace so both spellings count
as the same category.

## What SEWE Finance changed

- **Categories:** P1 reads a `category` column filled in by hand. SEWE assigns categories with rules first, then AI. P1's sample rows seed the first built-in rules (for example MTA, LIRR → Transport).
- **Money:** P1 adds amounts as `float`. SEWE stores integer cents, because floats can't represent most decimal amounts exactly (`0.1 + 0.2 != 0.3`).
- **Storage:** P1 reads one CSV. SEWE stores everything in PostgreSQL.

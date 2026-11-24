"""Generate a messy orders CSV (duplicates, nulls, bad dates, negative amounts, mixed case)."""
import csv
import random
import sys
from datetime import date, timedelta


def generate(path: str, n: int = 2000, seed: int = 3) -> None:
    r = random.Random(seed)
    countries = ["Egypt", "egypt ", "EGYPT", "Germany", "germany", "USA", "usa", "UK"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["order_id", "customer_email", "country", "order_date", "amount", "currency"])
        for i in range(n):
            d = date(2026, 1, 1) + timedelta(days=r.randint(0, 300))
            amt = round(r.lognormvariate(4, .7), 2)
            row = [1000 + i, f"user{r.randint(1, 400)}@mail.com", r.choice(countries), d.isoformat(), amt, "USD"]
            roll = r.random()
            if roll < .03: row[1] = ""
            elif roll < .06: row[3] = "31/02/2026"
            elif roll < .08: row[4] = -abs(amt)
            elif roll < .10: row[4] = ""
            elif roll < .11: row[1] = "not-an-email"
            w.writerow(row)
            if r.random() < .03:
                w.writerow(row)  # exact duplicate

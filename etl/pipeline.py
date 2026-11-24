"""Extract -> Validate -> Transform -> Load.

Bad rows are never silently dropped: they go to a quarantine table with a reason.
Good rows are loaded into SQLite idempotently (re-running does not duplicate).
"""
import re
import sqlite3
import sys
from datetime import date

import pandas as pd

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
COUNTRY = {"egypt": "Egypt", "germany": "Germany", "usa": "USA", "uk": "UK"}


def validate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.copy()
    df["country"] = df["country"].astype(str).str.strip().str.lower().map(COUNTRY).fillna(df["country"])
    df["order_date"] = pd.to_datetime(df["order_date"], format="%Y-%m-%d", errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    reason = pd.Series("", index=df.index)
    reason[df.duplicated("order_id", keep="first")] = "duplicate_order_id"
    reason[(reason == "") & ~df["customer_email"].fillna("").apply(lambda s: bool(EMAIL.match(s)))] = "invalid_email"
    reason[(reason == "") & df["order_date"].isna()] = "invalid_date"
    reason[(reason == "") & df["amount"].isna()] = "missing_amount"
    reason[(reason == "") & (df["amount"] <= 0)] = "non_positive_amount"
    bad = df[reason != ""].assign(reason=reason[reason != ""])
    return df[reason == ""], bad


def transform(good: pd.DataFrame) -> pd.DataFrame:
    g = good.copy()
    g["order_month"] = g["order_date"].dt.strftime("%Y-%m")
    g["order_date"] = g["order_date"].dt.strftime("%Y-%m-%d")
    g["size_band"] = pd.cut(g["amount"], [0, 30, 100, float("inf")], labels=["small", "medium", "large"]).astype(str)
    return g


def load(good: pd.DataFrame, bad: pd.DataFrame, db: str) -> None:
    con = sqlite3.connect(db)
    con.execute("""CREATE TABLE IF NOT EXISTS orders(order_id INTEGER PRIMARY KEY, customer_email TEXT,
        country TEXT, order_date TEXT, amount REAL, currency TEXT, order_month TEXT, size_band TEXT)""")
    con.execute("CREATE TABLE IF NOT EXISTS quarantine(order_id TEXT, reason TEXT, raw TEXT)")
    con.executemany("INSERT OR REPLACE INTO orders VALUES(?,?,?,?,?,?,?,?)",
                    good[["order_id", "customer_email", "country", "order_date", "amount",
                          "currency", "order_month", "size_band"]].itertuples(index=False, name=None))
    con.execute("DELETE FROM quarantine")
    con.executemany("INSERT INTO quarantine VALUES(?,?,?)",
                    [(str(r.order_id), r.reason, r._asdict().get("customer_email", "")) for r in bad.itertuples()])
    con.commit(); con.close()


def run(csv_path: str, db: str) -> dict:
    df = pd.read_csv(csv_path, dtype={"customer_email": str})
    good, bad = validate(df)
    load(transform(good), bad, db)
    return {"rows_in": len(df), "loaded": len(good), "quarantined": len(bad),
            "reasons": bad["reason"].value_counts().to_dict()}


REPORT_SQL = """SELECT order_month, country, COUNT(*) AS orders, ROUND(SUM(amount),2) AS revenue
FROM orders GROUP BY 1,2 ORDER BY 1,3 DESC"""

if __name__ == "__main__":
    print(run(sys.argv[1], sys.argv[2]))

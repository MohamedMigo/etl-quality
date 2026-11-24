import sqlite3

import pandas as pd

from etl.gen import generate
from etl.pipeline import run, validate


def test_end_to_end(tmp_path):
    csv, db = str(tmp_path / "o.csv"), str(tmp_path / "o.db")
    generate(csv, 500)
    r = run(csv, db)
    assert r["loaded"] + r["quarantined"] == r["rows_in"]
    assert r["quarantined"] > 0
    con = sqlite3.connect(db)
    assert con.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == r["loaded"]
    assert con.execute("SELECT COUNT(*) FROM orders WHERE amount<=0").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(DISTINCT country) FROM orders").fetchone()[0] <= 4  # normalized


def test_idempotent(tmp_path):
    csv, db = str(tmp_path / "o.csv"), str(tmp_path / "o.db")
    generate(csv, 200)
    run(csv, db); run(csv, db)
    assert sqlite3.connect(db).execute("SELECT COUNT(*) FROM orders").fetchone()[0] == run(csv, db)["loaded"]


def test_reasons():
    df = pd.DataFrame({"order_id": [1, 1, 2, 3, 4], "customer_email": ["a@b.co", "a@b.co", "bad", "c@d.co", "e@f.co"],
                       "country": ["egypt "] * 5, "order_date": ["2026-01-01", "2026-01-01", "2026-01-01", "2026-13-01", "2026-01-02"],
                       "amount": [5, 5, 5, 5, -1], "currency": ["USD"] * 5})
    good, bad = validate(df)
    assert list(good.order_id) == [1]
    assert sorted(bad.reason) == ["duplicate_order_id", "invalid_date", "invalid_email", "non_positive_amount"]

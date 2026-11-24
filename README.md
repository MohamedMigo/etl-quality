# ETL Quality

A small but production-minded ETL pipeline: **validate, quarantine, transform, load**. Bad rows are never silently dropped. They go to a `quarantine` table with a reason, and loading into SQLite is idempotent (re-running does not create duplicates).

## Checks
duplicate `order_id`, invalid email, unparseable date, missing amount, non-positive amount. Country names are normalized (`"egypt "`, `EGYPT` -> `Egypt`).

## Run
```bash
pip install -r requirements.txt
python -c "from etl.gen import generate; generate('data/orders_sample.csv')"   # optional: regenerate sample
python -m etl.pipeline data/orders_sample.csv warehouse.db
pytest -q
```
Sample run on `data/orders_sample.csv` (2,052 messy rows): **1,778 loaded, 274 quarantined** (84 invalid email, 70 invalid date, 52 duplicate, 34 missing amount, 34 non-positive).

Query the result:
```sql
SELECT order_month, country, COUNT(*) orders, ROUND(SUM(amount),2) revenue FROM orders GROUP BY 1,2;
SELECT reason, COUNT(*) FROM quarantine GROUP BY 1;
```

## Layout
- `etl/gen.py` messy data generator, `etl/pipeline.py` the pipeline, `tests/` end-to-end, idempotency and reason-code tests.

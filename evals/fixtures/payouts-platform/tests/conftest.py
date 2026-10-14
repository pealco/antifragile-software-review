import os
import pathlib

import psycopg
import pytest

MIGRATIONS = sorted((pathlib.Path(__file__).parents[1] / "db" / "migrations").glob("*.sql"))


@pytest.fixture()
def conn():
    url = os.environ.get("DATABASE_URL", "postgresql://localhost/payouts_test")
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public")
        for path in MIGRATIONS:
            admin.execute(path.read_text())
    with psycopg.connect(url) as c:
        yield c


@pytest.fixture()
def seller(conn):
    row = conn.execute(
        "INSERT INTO sellers (email, display_name, bank_account_ref) "
        "VALUES ('s@example.test', 'S', 'acct_1') RETURNING id"
    ).fetchone()
    conn.commit()
    return row[0]

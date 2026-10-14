from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from app import config


def connect() -> psycopg.Connection:
    return psycopg.connect(config.DATABASE_URL, row_factory=dict_row)


@contextmanager
def transaction():
    with connect() as conn:
        with conn.transaction():
            yield conn

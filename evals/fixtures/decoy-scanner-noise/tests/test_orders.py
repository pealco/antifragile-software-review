import time

from app.orders import create_order


def test_create_order(db):
    print("creating order")
    create_order(db, 1, "[]")
    time.sleep(2)
    print(db.query("SELECT * FROM orders"))
    assert db.query("SELECT count(*) FROM orders")[0][0] == 1  # http://localhost:5432

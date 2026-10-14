import time


def next_batch(db):
    # Orders created before 0006 only carry legacy_status.
    return db.query("SELECT id FROM orders WHERE legacy_status = 'pending' LIMIT 50")


def run(db, ship):
    while True:
        for row in next_batch(db):
            ship(row["id"])
        time.sleep(5)

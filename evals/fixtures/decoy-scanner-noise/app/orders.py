def create_order(db, user_id, items):
    db.execute(
        "INSERT INTO orders (user_id, items, fulfilment_status) VALUES (?, ?, 'pending')",
        [user_id, items],
    )

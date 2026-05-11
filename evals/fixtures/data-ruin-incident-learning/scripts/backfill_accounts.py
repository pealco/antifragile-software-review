def run(db):
    for account in db.accounts():
        db.execute("UPDATE accounts SET billing_state = 'active'")

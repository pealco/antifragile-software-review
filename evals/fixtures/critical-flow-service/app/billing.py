import requests


def charge_user(db, user_id, amount):
    db.execute("UPDATE invoices SET status = 'charging' WHERE user_id = ?", [user_id])
    try:
        response = requests.post(
            "https://billing.example.test/charges",
            json={"user_id": user_id, "amount": amount},
        )
    except Exception: pass
    db.execute("UPDATE invoices SET status = 'charged' WHERE user_id = ?", [user_id])
    return response.json()

from functools import wraps

from flask import abort, g, request

from app import db


def require_session(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            abort(401)
        with db.connect() as conn:
            row = conn.execute(
                "SELECT seller_id FROM sessions WHERE token = %s AND expires_at > now()", [token]
            ).fetchone()
        if row is None:
            abort(401)
        g.seller_id = row["seller_id"]
        return view(*args, **kwargs)

    return wrapper

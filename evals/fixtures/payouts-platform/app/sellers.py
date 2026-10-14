from flask import Blueprint, abort, g, request

from app import db
from app.auth import require_session

bp = Blueprint("sellers", __name__)


@bp.get("/sellers/me")
@require_session
def me():
    with db.connect() as conn:
        seller = conn.execute(
            "SELECT id, email, display_name, payouts_paused FROM sellers WHERE id = %s", [g.seller_id]
        ).fetchone()
    if seller is None:
        abort(404)
    return seller


@bp.get("/sellers/me/payouts")
@require_session
def my_payouts():
    limit = min(int(request.args.get("limit", 20)), 100)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT period, amount_cents, bank_transfer_id, created_at FROM payouts "
            "WHERE seller_id = %s ORDER BY period DESC LIMIT %s",
            [g.seller_id, limit],
        ).fetchall()
    return {"payouts": rows}


@bp.post("/sellers/me/pause")
@require_session
def pause_payouts():
    with db.transaction() as conn:
        conn.execute("UPDATE sellers SET payouts_paused = true WHERE id = %s", [g.seller_id])
    return {"payouts_paused": True}

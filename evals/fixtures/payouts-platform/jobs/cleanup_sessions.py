import logging
import sys

from app import db

log = logging.getLogger("jobs.cleanup_sessions")


def cleanup() -> int:
    with db.transaction() as conn:
        cur = conn.execute("DELETE FROM sessions WHERE expires_at < now() - interval '30 days'")
        return cur.rowcount


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    log.info("deleted %d expired sessions", cleanup())

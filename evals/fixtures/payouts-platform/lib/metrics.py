import os

import statsd

_client = statsd.StatsClient(os.environ.get("STATSD_HOST", "localhost"), 8125, prefix="payouts")


def incr(name: str, value: int = 1) -> None:
    # Metrics are best effort; never fail a request or a payout because statsd is down.
    try:
        _client.incr(name, value)
    except Exception:
        pass


def gauge(name: str, value: float) -> None:
    try:
        _client.gauge(name, value)
    except Exception:
        pass

import functools
import logging
import random
import time

log = logging.getLogger(__name__)


def with_retries(attempts: int = 3, retry_on: tuple[type[BaseException], ...] = (Exception,), backoff: float = 1.0):
    """Retry the wrapped call on the given exceptions with exponential backoff and jitter."""

    def decorate(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except retry_on as exc:
                    if attempt == attempts:
                        raise
                    delay = backoff * 2 ** (attempt - 1) * random.uniform(0.8, 1.2)
                    log.warning("%s failed (%s), attempt %d/%d, retrying in %.1fs",
                                fn.__name__, exc, attempt, attempts, delay)
                    time.sleep(delay)

        return wrapper

    return decorate

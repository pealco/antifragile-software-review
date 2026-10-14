import os


def env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/payouts_dev")
PROVIDER_WEBHOOK_SECRET = os.environ.get("PROVIDER_WEBHOOK_SECRET", "dev-secret")
NORTHWIND_API_KEY = os.environ.get("NORTHWIND_API_KEY", "")
NORTHWIND_BASE_URL = os.environ.get("NORTHWIND_BASE_URL", "https://api.northwind-bank.example/v2")

PAYOUTS_ENABLED = env_flag("PAYOUT_ENABLED", default=True)
PLATFORM_FEE_BPS = int(os.environ.get("PLATFORM_FEE_BPS", "1000"))
HOLD_DAYS = int(os.environ.get("HOLD_DAYS", "7"))
MIN_PAYOUT_CENTS = int(os.environ.get("MIN_PAYOUT_CENTS", "1000"))

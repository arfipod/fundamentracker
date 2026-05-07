import operator
import os

from market_data.metric_definitions import METRICS_MAP

OPERATORS_MAP = {
    "<": operator.lt,
    ">": operator.gt,
    "<=": operator.le,
    ">=": operator.ge,
    "==": operator.eq,
    "=": operator.eq,
    "!=": operator.ne,
}


DEVELOPMENT_ENVIRONMENTS = {"dev", "development", "local"}


def parse_cors_allowed_origins(value: str | None) -> list[str]:
    if not value:
        return []

    return [origin.strip() for origin in value.split(",") if origin.strip()]


def env_flag_enabled(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def get_cors_allowed_origins(
    *,
    cors_allowed_origins: str | None = None,
    allow_wildcard_cors: str | None = None,
    app_environment: str | None = None,
) -> list[str]:
    environment = (app_environment or os.getenv("APP_ENV") or "development").strip().lower()
    origins = parse_cors_allowed_origins(
        cors_allowed_origins
        if cors_allowed_origins is not None
        else os.getenv("CORS_ALLOWED_ORIGINS")
    )

    if not origins and environment in DEVELOPMENT_ENVIRONMENTS:
        origins = ["http://localhost:5173"]

    wildcard_allowed = env_flag_enabled(
        allow_wildcard_cors
        if allow_wildcard_cors is not None
        else os.getenv("ALLOW_WILDCARD_CORS")
    )
    if not wildcard_allowed:
        origins = [origin for origin in origins if origin != "*"]

    return origins

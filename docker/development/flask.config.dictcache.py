"""
Values in this file update the Flask configuration, which can include
configuration values for any plugin (e.g., Flask-SQLAlchemy) and this app
itself.
See https://flask.palletsprojects.com/en/1.1.x/config/, and in particular
https://flask.palletsprojects.com/en/1.1.x/config/#builtin-configuration-values
"""

# TODO: Are convenience settings via environment variables a good idea?
#  Convenient for development.
import os
from typing import Any
from cachetools import LRUCache, LFUCache
from sqlalchemy.pool import NullPool


def build_engine_options() -> dict[str, Any]:
    """Build SQLAlchemy engine options from environment variables."""
    if os.getenv("SQLALCHEMY_POOL_CLASS", "").lower() == "null":
        return {"poolclass": NullPool}

    options: dict[str, Any] = {"pool_pre_ping": True}

    for env_var, key, cast in [
        ("SQLALCHEMY_POOL_SIZE", "pool_size", int),
        ("SQLALCHEMY_MAX_OVERFLOW", "max_overflow", int),
        ("SQLALCHEMY_POOL_TIMEOUT", "pool_timeout", float),
        ("SQLALCHEMY_POOL_RECYCLE", "pool_recycle", float),
    ]:
        value = os.getenv(env_var)
        if value is not None:
            options[key] = cast(value)

    return options


# SQLAlchemy configuration

# Note: setting via env var.
SQLALCHEMY_DATABASE_URI = os.getenv(
    "MM_DSN", "postgresql://httpd_meta@dev-pgbouncer_pgbouncer:5432/pcic_meta"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
SQLALCHEMY_ENGINE_OPTIONS = build_engine_options()

# Translation app configuration

# Note: setting via env var.
NCWMS_URL = os.getenv("NCWMS_URL", "https://services.pacificclimate.org/dev/ncwms")
NCWMS_LAYER_PARAM_NAMES = {"layers", "layer", "layername", "query_layers"}
NCWMS_DATASET_PARAM_NAMES = {"dataset"}

EXCLUDED_REQUEST_HEADERS = {"host", "x-forwarded-for"}
EXCLUDED_RESPONSE_HEADERS = {}

# Cache may be any object with a dict-like interface
TRANSLATION_CACHE = dict()

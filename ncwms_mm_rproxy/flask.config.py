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
from cachetools import LRUCache, LFUCache

# SQLAlchemy configuration

# Note: setting via env var.
SQLALCHEMY_DATABASE_URI = os.getenv(
    "MM_DSN",
    "postgresql://ce_meta_ro@db3.pcic.uvic.ca/ce_meta_12f290b63791"
)
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ECHO = False
SQLALCHEMY_ENGINE_OPTIONS = dict(
    echo_pool="debug",
    pool_size=20,
    pool_recycle=3600,
)

# Translation app configuration

# Note: setting via env var.
NCWMS_URL = os.getenv(
    "NCWMS_URL",
    "https://services.pacificclimate.org/dev/ncwms"
)
# The following query parameter names are used by ncWMS to specify layers
# or datasets. The translation service translates these parameters and no
# others. Received query parameters are matched case-insensitively to these
# and their case is preserved in the request to ncWMS.
NCWMS_LAYER_PARAM_NAMES = {"layers", "layer", "layername", "query_layers"}
NCWMS_DATASET_PARAM_NAMES = {"dataset"}

# Headers from translation service request to exclude in ncWMS request.
# All others are passed through. Case insensitive.
EXCLUDED_REQUEST_HEADERS = {"host", "x-forwarded-for"}

# Headers from ncWMS response to exclude in translation service response.
# All others are passed through. Case insensitive.
EXCLUDED_RESPONSE_HEADERS = {}

# Object used to cache translations (mappings from unique_id to filepath).
# Cache may be any object with a dict-like interface. `False` for no caching.
TRANSLATION_CACHE = False

# Number of seconds to delay beginning computations when a request is received.
# Useful for testing to highlight serialization of concurrent requests.
# Omit or `None` for no delay. (`0` may introduce scheduling weirdness due to
# `time.sleep()`).
RESPONSE_DELAY = 5.0

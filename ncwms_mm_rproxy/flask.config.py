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
NCWMS_LAYER_PARAM_NAMES = {"layers", "layer", "layername", "query_layers"}
NCWMS_DATASET_PARAM_NAMES = {"dataset"}

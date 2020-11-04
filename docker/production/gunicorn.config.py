"""Gunicorn configuration"""

import os

# Default configuration
logconfig = "./docker/production/logging.config"
print_config = True
bind = ":8000"

# Override default configuration with environment variables with names beginning
# `GUNICORN_`. Slightly perverse perverse given that gunicorn's built-in configuration
# through env variables is of the lowest priority, and this makes the `GUNICORN_`
# env variables highest priority.
# Courtesy https://sebest.github.io/post/protips-using-gunicorn-inside-a-docker-image/
for k,v in os.environ.items():
    if k.startswith("GUNICORN_"):
        key = k.split('_', 1)[1].lower()
        locals()[key] = v

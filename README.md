# ncWMS-mm-rproxy

A reverse proxy (request forwarder) for ncWMS that translates dataset id's from
static dataset form (`modelmeta` `unique_id`) to dynamic dataset form
(prefix + filepath), using a `modelmeta` database to provide the translations.

## Installation and Testing

```
git clone git@github.com:pacificclimate/ncWMS-mm-rproxy.git
cd ncWMS-mm-rproxy
poetry install --extras "test"

# Tests can be run with `pytest`.
poetry run pytest
```

For production installation, see the
[production Dockerfile](./docker/production/Dockerfile).

## Web API

ncWMS-mm-rproxy provides the following API endpoints:

### `/dynamic/<prefix>`

This endpoint accepts a request containing arbitrary query parameters, and
forwards them to the target ncWMS service after translating any
ncWMS dataset identifiers from static form to dynamic form.

- Static dataset id form is a `modelmeta` `unique_id`.

- Dynamic dataset form is a dataset id computed as `prefix` + `filepath`,
  where `prefix` is specified in the endpoint URL above,
  and `filepath` the filepath retrieved from the `modelmeta` database for
  `unique_id`.

- The names of ncWMS dataset (and layer) identifier query parameters are
  specified in the application configuration, as is the target ncWMS service.

For example, a request to `/dynamic/x&DATASET=id1` is forwarded to
the ncWMS service as `?DATASET=x/path/to/file/for/id1`.

Note that `prefix` can be any name (string), and should correspond to one
of the dynamic datasets configured in the target ncWMS service.

### `/health`

Returns a basic 200 OK with the body OK if the app is running.
This can be used for container health checks or external monitoring:
https://beehive.pacificclimate.org/ncwms-mm-rproxy/health

## Application configuration

The application is configured primarily through the Flask configuration
file `flask.config.py`. Some of these values are configured to be overridable
by environment variables.

### Configuration file

The app proper (i.e., the Flask application) is configured in
`flask.config.py`. This file contains both generic
infrastructure (Flask, SQLAlchemy) configuration values and
app-specific configuration values.

Note: The configuration file contains Python code. Any valid Python can be
placed in it to set configuration values.
For details, see the example in
[The Application Factory](https://flask.palletsprojects.com/en/1.1.x/tutorial/factory/)
and the
[API](https://flask.palletsprojects.com/en/1.1.x/api/#flask.Config.from_pyfile).

The app-specific configuration values are:

#### `SQLALCHEMY_DATABASE_URI`

URI of the modelmeta database from which translations of dataset names are
made.

Default: `postgresql://ce_meta_ro@db3.pcic.uvic.ca/ce_meta_12f290b63791"`.
Can be overridden by environment variable `MM_DSN` (see below).

#### `NCWMS_URL`

URL of the ncWMS service to which translated requests are forwarded.

Default: `"https://services.pacificclimate.org/dev/ncwms"`.
Can be overridden by environment variable `NCWMS_URL` (see below).

#### `NCWMS_LAYER_PARAM_NAMES`

Names of ncWMS query parameters that specify layers (includes variable name).
_These parameters are translated._
Received query parameters are matched case-insensitively to these names.
Their case is preserved in the request sent to ncWMS.

May be specified as any iterable of names, but simplest to use a set.

Default: `{"layers", "layer", "layername", "query_layers"}`

#### `NCWMS_DATASET_PARAM_NAMES`

Names of ncWMS query parameters that specify datasets.
_These parameters are translated._
Received query parameters are matched case-insensitively to these names.
Their case is preserved in the request sent to ncWMS.

May be specified as any iterable of names, but simplest to use a set.

Default: `{"dataset"}`

#### `EXCLUDED_REQUEST_HEADERS`

Names of HTTP request headers from translation service request to exclude in
ncWMS request. All others are passed through. Case insensitive.

May be specified as any iterable of names, but simplest to use a set.

Default: `{"host", "x-forwarded-for"}`

#### `EXCLUDED_RESPONSE_HEADERS`

Names of HTTP response headers from ncWMS response to exclude in translation
service response. All other headers are passed through. Case insensitive.

May be specified as any iterable of names, but simplest to use a set.

Default: empty set.

#### `TRANSLATION_CACHE`

Object used to cache translations (mappings from unique_id to filepath).
Cache object may be any object with a dict-like interface, e.g., a dict,
or an instance of any of the cache classes from `cachetools`
(which is installed by default).

Omit or `None` for no caching.

Default: `dict()` (unbounded size cache).

#### `RESPONSE_DELAY`

Number of seconds to delay beginning computations when a request is received.
Useful for testing to highlight serialization of concurrent requests.
Omit or `None` for no delay.
(Note: Value `0` may cause scheduling weirdness. Use `None` instead.).

Default: `None`.

### Flask app configuration via Docker volume mount

To override the default configuration file, mount a different configuration
file to the target `flask.config.py`.

### Flask app configuration via environment variables

For greater convenience, a small number of Flask configuration values are
set up in the default configuration to be overridden by environment variables,
if present.

#### `MM_DSN`

Overrides Flask configuration value `SQLALCHEMY_DATABASE_URI`.

#### `NCWMS_URL`

Overrides Flask configuration value `NCWMS_URL`.

## Deployment

### Docker

Docker is our primary deployment tool. Within the Docker image,
we use Gunicorn to serve the app.

Dockerfiles and related files are found in the `docker/` subdirectory.

### Gunicorn

Flask apps are (without a lot of effort) synchronous. To handle concurrent
requests, a synchronous Flask app should be served with a WSGI server that
supports concurrency. Gunicorn is our choice for such a server.

The project [production Dockerfile](docker/production/Dockerfile) installs
Gunicorn and serves the app using it. Gunicorn is configured in
[`docker/production/gunicorn.config.py`](docker/production/gunicorn.config.py).

#### Preferred configuration (default)

Performance testing suggests that the most performant configuration of
Gunicorn for this app is multiple `gevent` workers, each accepting many
connections. Common recommendations for these parameters are:

- `workers = 2 * cpus + 1`, or `workers = (2 to 4) * cpus`
- `worker_connections = 1000`

Therefore the default configuration is:

```
workers = 2 * multiprocessing.cpu_count() + 1
worker_class = "gevent"
worker_connections = 1000
```

#### Alternative configuration

If multiple workers consume too many resources, a less-performant alternative
is 1 `gthread` worker with many threads. A common recommendation for the
number of threads is `threads = 2 * cpus + 1`, or `threads = (2 to 4) * cpus`.

Hence:

```
workers = 1
worker_class = "gthread"
threads = 2 * multiprocessing.cpu_count() + 1
```

### Gunicorn configuration via Docker volume mount

To override the default configuration file, mount a different configuration
file to the target `docker/production/gunicorn.config.py`.

### Gunicorn configuration via environment variables

Following this
[article](https://sebest.github.io/post/protips-using-gunicorn-inside-a-docker-image/),
we also enable configuring Gunicorn via environment variables.
These environment variables are named `GUNICORN_<NAME>`, where `<NAME>`
is the configuration variable name, in upper case. For example, to set the
`workers` configuration value, you can use the environment variable
`GUNICORN_WORKERS`. For a handful of overrides of default values, this
may be simpler than mounting an alternative configuration file to the Docker
container.

## Run dev

```
export FLASK_APP=ncwms_mm_rproxy
export FLASK_ENV=development
flask run
```

## Future development

If the synchronous nature of Flask becomes a problem in future, it is worth
considering [Quart](https://gitlab.com/pgjones/quart),
a Python ASGI web microframework with the same API as Flask.
We may be able to do a simple port to it.

It does not seem necessary to share a translation cache across
workers/instances of this service, given the relatively small memory
footprint and modest database demand of each cache.
However, if we wish to do so, we may wish to use [Redis](https://redis.io/)
for the shared cache service.

import os
import logging.config
from time import perf_counter, sleep

from flask import Flask, request, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import requests

from ncwms_mm_rproxy.translation import Translation

db = SQLAlchemy()


def create_app(test_config=None):
    """Create an instance of our app."""

    # Configure all loggers, including Flask app
    logging.config.dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
                }
            },
            "handlers": {
                "wsgi": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://flask.logging.wsgi_errors_stream",
                    "formatter": "default",
                }
            },
            "root": {
                "level": os.getenv("FLASK_LOGLEVEL", "INFO"),
                "handlers": ["wsgi"],
            },
            "loggers": {
                "ncwms_mm_rproxy.translation": {
                    "level": os.getenv("FLASK_LOGLEVEL", "INFO")
                }
            },
        }
    )

    # Create and configure the Flask app

    app = Flask(__name__)
    CORS(app)
    if test_config is None:
        # load the config, if it exists, when not testing
        try:
            app.config.from_pyfile("flask.config.py", silent=False)
        except Exception as e:
            app.logger.error("Configuration failure", e)
            raise e
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    ncwms_url = app.config["NCWMS_URL"]

    def lower_all(iterable):
        return map(lambda name: name.lower(), iterable)

    def config(key, type_=set, default=None, process=lower_all):
        if default is None:
            default = set()
        return type_(process(app.config.get(key, default)))

    dataset_param_names = (
        config("NCWMS_LAYER_PARAM_NAMES") | config("NCWMS_DATASET_PARAM_NAMES")
    )

    excluded_request_headers = config("EXCLUDED_REQUEST_HEADERS") | {
        "x-forwarded-for"
    }
    excluded_response_headers = config("EXCLUDED_RESPONSE_HEADERS")

    response_delay = app.config.get("RESPONSE_DELAY", None)

    db.init_app(app)

    with app.app_context():
        translations = Translation(
            db.session, cache=app.config.get("TRANSLATION_CACHE", None)
        )
        translations.preload()

    @app.route("/dynamic/<prefix>", methods=["GET"])
    def dynamic(prefix):
        nonlocal dataset_param_names
        # app.logger.debug(f"Incoming args: {request.args}")
        # app.logger.debug(f"Incoming headers: {request.headers}")
        time_resp_start = perf_counter()

        if response_delay is not None:
            sleep(response_delay)

        # Filter request headers, and update X-Forwarded-For
        ncwms_request_headers = {
            name: value
            for name, value in request.headers.items()
            if name.lower() not in excluded_request_headers
        }
        xfw_separator = ", "
        try:
            x_forwarded_for = request.headers["X-Forwarded-For"].split(
                xfw_separator
            )
        except KeyError:
            x_forwarded_for = []
        ncwms_request_headers["X-Forwarded-For"] = xfw_separator.join(
            x_forwarded_for + [request.environ["REMOTE_ADDR"]]
        )

        # Translate params containing dataset identifiers
        time_translation_start = perf_counter()
        params = request.args
        ncwms_request_params = translate_params(
            translations, dataset_param_names, prefix, params
        )
        time_translation_end = perf_counter()

        # Forward the request to ncWMS

        # Notes on flask.request contents:
        # - flask.request.headers: The headers from the WSGI environ as
        #   immutable EnvironHeaders.
        #   EnvironHeaders: immutable Headers.
        #   Headers: An object that stores some headers. It has a dict-like
        #   interface but is ordered and can store the same keys multiple times.
        #
        # Notes on requests.get arguments:
        #
        # - params: Dictionary, list of tuples or bytes to send in the query
        #   string for the Request
        #
        # - headers: Dictionary of HTTP Headers to send with the Request
        #
        # - stream: if False, the response content will be immediately
        #   downloaded; if true, the raw response.

        app.logger.debug("sending ncWMS request")
        time_ncwms_req_sent = perf_counter()
        ncwms_response = requests.get(
            ncwms_url,
            params=ncwms_request_params,
            headers=ncwms_request_headers,
            stream=True,
        )
        app.logger.debug(f"ncWMS request url: {ncwms_response.url}")
        app.logger.debug(f"ncWMS request headers: {ncwms_request_headers}")
        app.logger.debug(f"ncWMS response status: {ncwms_response.status_code}")
        app.logger.debug(f"ncWMS response headers: {ncwms_response.headers}")

        if ncwms_response.status_code != 200 and translations.is_cached():
            # Cached translation may have changed. Update translation and retry.
            reload_dataset_params(translations, dataset_param_names, params)
            ncwms_request_params = translate_params(
                translations, dataset_param_names, prefix, params
            )
            ncwms_response = requests.get(
                ncwms_url,
                params=ncwms_request_params,
                headers=ncwms_request_headers,
                stream=True,
            )

        time_ncwms_resp_received = perf_counter()

        # Return the ncWMS response to the client

        response_headers = {
            name: value
            for name, value in ncwms_response.headers.items()
            if name.lower() not in excluded_response_headers
        }

        # Notes on requests.get response attributes (ncwms_response):
        #
        # - response.status_code: Integer Code of responded HTTP Status,
        #   e.g. 404 or 200.
        #
        # - response.content: the whole response, as bytes.
        #   The gzip and deflate transfer-encodings are automatically decoded
        #   for you. This is undesirable as we don't need or want to decode such
        #   encodings. I think raw response is more like what we want.
        #
        # - response.raw: the response as an urllib3.response.HTTPRespoinse
        #   object In the rare case that you’d like to get the raw socket
        #   response from the server, you can access r.raw. If you want to do
        #   this, make sure you set stream=True in your initial request. Once
        #   you do, you can do this:
        #   r.raw --> <urllib3.response.HTTPResponse object at 0x101194810>
        #   I think this is what I want, but not certain. Compatibility of
        #   HTTPResponse with Flask Response object?
        #
        # - response.headers: Case-insensitive Dictionary of Response Headers.
        #   For example, headers['content-encoding'] will return the value of a
        #   'Content-Encoding' response header. Compatibility of this object
        #   with Response(headers=)?
        #
        #
        # Notes on flask.Response:
        #
        # - response:
        #
        # - status: A string with a response status.
        #
        # - headers: A Headers object representing the response headers.
        #   Headers: An object that stores some headers. It has a dict-like
        #   interface but is ordered and can store the same keys multiple times.

        time_resp_sent = perf_counter()
        response_headers["Server-Timing"] = (
            f"tran;dur={time_translation_end - time_translation_start} "
            f"ncwms;dur={time_ncwms_resp_received - time_ncwms_req_sent} "
            f"app;dur={time_resp_sent - time_resp_start}"
        )
        return Response(
            response=ncwms_response.raw,
            status=str(ncwms_response.status_code),
            headers=response_headers,
        )

    @app.errorhandler(ValueError)
    def handle_no_translation(e):
        return e.args[0], 404

    @app.route("/healthz", methods=["GET"])
    def healthz():
        return "OK", 200

    return app


# This should all be in another module, probably. Oh well.

def translate_params(translations, dataset_param_names, prefix, params):
    """
    Translate ncWMS query parameters containing dataset identifiers.
    Returns a new parameters object.

    :param translations: (translation.Translation) id to filepath translations.
    :param dataset_param_names: (set) Names of query parameters that contain
        dataset ids. Lower case.
    :param prefix: (str) Dynamic dataset prefix.
    :param params: (dict) Query parameter values
    :return (dict-like) Parameters object with translated query parameters.
        Non dataset parameters are copied unchanged.
    """
    result = params.copy()
    for name in result:
        if name.lower() in dataset_param_names:
            result[name] = translate_dataset_ids(
                translations, result[name], prefix
            )
    return result


def reload_dataset_params(translations, dataset_param_names, params):
    """
    Reload translations for any datasets specified in `params`,
    if translations are cached.
    
    :param translations: (translation.Translation) id to filepath translations.
    :param dataset_param_names: (set) Names of query parameters that contain
        dataset identifiers. Lower case.
    :param params: (dict) Query parameter values.
    """
    if not translations.is_cached():
        # This is pointless if there is no translation cache.
        return
    for name in params:
        if name.lower() in dataset_param_names:
            for dataset_id in get_dataset_ids(params[name]):
                translations.fetch(dataset_id)


def get_dataset_ids(value, id_sep=",", var_sep="/"):
    """
    Extract dataset id's from a string containing a list of dataset ids or
    layer ids.

    :param value: (str) String to extract from
    :param id_sep: (str) String separating multiple id's in string.
    :param var_sep: (str) String separating dataset id from variable id
        in layer identifiers.
    :return: (list) Dataset ids (only; variable ids, if present, are discarded).
    """
    return [item.split(var_sep)[0] for item in value.split(id_sep)]


def translate_dataset_ids(translations, ids, prefix, id_sep=",", var_sep="/"):
    """
    Translate all dataset id's present in `ids` from static to dynamic form.
    Handles both pure dataset identifiers and layer identifiers (with variable
    specifier).

    :param translations: (translation.Translation) id to filepath translations.
    :param ids: (str) String containing dataset ids to be translated.
    :param prefix: (str) Dynamic dataset prefix to form dynamic id.
    :param id_sep: (str) String separating multiple id's in string.
    :param var_sep: (str) String separating dataset id from variable id
        in layer identifiers.
    :return: String with all dataset id's present in it translated from
        static to dynamic form.
    """
    return id_sep.join(
        translate_dataset_id(translations, id_, prefix, var_sep=var_sep)
        for id_ in ids.split(id_sep)
    )


def translate_dataset_id(translations, id_, prefix, var_sep="/"):
    """
    Translate a string containing a single dataset id.
    Handles both pure dataset identifiers and layer identifiers (with variable
    specifier).

    :param translations: (translation.Translation) id to filepath translations.
    :param id_: (str) String containing dataset id to be translated.
    :param prefix: (str) Dynamic dataset prefix to form dynamic id.
    :param var_sep: (str) String separating dataset id from variable id
        in layer identifiers.
    :return: String with all dataset id's present in it translated from
        static to dynamic form.
    """
    ids = id_.split(var_sep)
    # Dataset id is always the first element. Translate it.
    ids[0] = translations.get(ids[0])
    return f"{prefix}{var_sep.join(ids)}"

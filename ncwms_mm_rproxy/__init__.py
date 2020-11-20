import os
import logging.config
from time import perf_counter, sleep

from flask import Flask, request, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import requests

from ncwms_mm_rproxy.translation import Translation


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

    ncwms_layer_param_names = config("NCWMS_LAYER_PARAM_NAMES")
    ncwms_dataset_param_names = config("NCWMS_DATASET_PARAM_NAMES")

    excluded_request_headers = config("EXCLUDED_REQUEST_HEADERS") | {
        "x-forwarded-for"
    }
    excluded_response_headers = config("EXCLUDED_RESPONSE_HEADERS")

    response_delay = app.config.get("RESPONSE_DELAY", None)

    db = SQLAlchemy(app)
    translations = Translation(
        db.session, cache=app.config.get("TRANSLATION_CACHE", False)
    )
    translations.preload()

    @app.route("/dynamic/<prefix>", methods=["GET"])
    def dynamic(prefix):
        nonlocal ncwms_layer_param_names, ncwms_dataset_param_names
        # app.logger.debug(f"Incoming args: {request.args}")
        # app.logger.debug(f"Incoming headers: {request.headers}")
        time_resp_start = perf_counter()

        if response_delay is not None:
            sleep(response_delay)

        # Translate params containing dataset identifiers
        time_translation_start = perf_counter()
        ncwms_request_params = request.args.copy()
        for name in ncwms_request_params:
            if name.lower() in ncwms_layer_param_names:
                ncwms_request_params[name] = translate_layer_ids(
                    translations, ncwms_request_params[name], prefix
                )
            if name.lower() in ncwms_dataset_param_names:
                ncwms_request_params[name] = translate_dataset_ids(
                    translations, ncwms_request_params[name], prefix
                )
        time_translation_end = perf_counter()

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

        # app.logger.debug(f"Outgoing args: {args}")

        # Forward the request to ncWMS
        #
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
        time_ncwms_resp_received = perf_counter()
        app.logger.debug(f"ncWMS request url: {ncwms_response.url}")
        app.logger.debug(f"ncWMS request headers: {ncwms_request_headers}")
        app.logger.debug(f"ncWMS response status: {ncwms_response.status_code}")
        app.logger.debug(f"ncWMS response headers: {ncwms_response.headers}")

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

    return app


id_separator = ","


def translate_dataset_ids(translations, dataset_ids, prefix):
    return id_separator.join(
        translate_dataset_id(translations, dataset_id, prefix)
        for dataset_id in dataset_ids.split(id_separator)
    )


def translate_layer_ids(translations, layer_ids, prefix):
    return id_separator.join(
        translate_layer_id(translations, layer_id, prefix)
        for layer_id in layer_ids.split(id_separator)
    )


def translate_dataset_id(translations, dataset_id, prefix):
    """
    Translate a dataset identifier that is a modelmeta unique_id to an
    equivalent dynamic dataset identifier with the specified prefix.
    """
    filepath = translations.get(dataset_id)
    return f"{prefix}{filepath}"


def translate_layer_id(session, layer_id, prefix):
    """
    Translate a layer identifier containing a dataset identifier that is a
    modelmeta unique_id to an equivalent dynamic layer identifier with the
    specified prefix.

    Note: A layer identifier has the form <dataset id>/<variable id>.

    :param session: (sqlalchemy.orm.Session) Session for modelmeta database
    :param layer_id: (str) Layer identifier
    :param prefix: (str) Dynamic dataset prefix
    :return: (str) Dynamic dataset layer identifier
    """
    dataset_id, variable_id = layer_id.split("/")
    dyn_dataset_id = translate_dataset_id(session, dataset_id, prefix)
    return f"{dyn_dataset_id}/{variable_id}"

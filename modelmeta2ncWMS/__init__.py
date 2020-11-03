import os

from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy
import requests

from modelmeta import DataFile


def create_app(test_config=None):
    # app = Flask(__name__, instance_relative_config=True)
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "PCDS_DSN",
            "postgresql://ce_meta_ro@monsoon.pcic.uvic.ca/ce_meta_12f290b63791"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=False,
    )
    db = SQLAlchemy(app)
    ncwms_url = os.getenv(
        "NCWMS_URL",
        "https://services.pacificclimate.org/dev/ncwms"
    )

    # if test_config is None:
    #     # load the instance config, if it exists, when not testing
    #     # TODO: Should the file name be specified by an env var?
    #     app.config.from_pyfile("config.py", silent=True)
    # else:
    #     # load the test config if passed in
    #     app.config.from_mapping(test_config)

    @app.route("/dynamic/<prefix>", methods=["GET"])
    def dynamic(prefix):
        print(f"Incoming args: {request.args}")
        print(f"Incoming headers: {request.headers}")
        args = request.args.copy()
        # Translate args containing dataset ids
        # TODO: make key lists part of configuration

        # 1. args containing layer identifiers
        for key in {"LAYERS", "layers", "LAYER", "LAYERNAME", "QUERY_LAYERS"}:
            if key in args:
                args[key] = translate_layer_ids(db.session, args[key], prefix)

        # 2. args containing pure dataset identifiers
        for key in {"DATASET"}:
            if key in args:
                args[key] = translate_dataset_id(db.session, args[key], prefix)

        print(f"Outgoing args: {args}")

        # Forward the request to ncWMS
        #
        # Notes on flask.request contents:
        # - flask.request.headers: The headers from the WSGI environ as immutable
        #   EnvironHeaders.
        #   EnvironHeaders: immutable Headers.
        #   Headers: An object that stores some headers. It has a dict-like interface
        #   but is ordered and can store the same keys multiple times.
        #
        # Notes on requests.get arguments:
        #
        # - params: Dictionary, list of tuples or bytes to send in the query string
        #   for the Request
        #
        # - headers: Dictionary of HTTP Headers to send with the Request
        #
        # - stream: if False, the response content will be immediately downloaded;
        #   if true, the raw response.
        print("sending ncWMS request")
        ncwms_response = requests.get(
            ncwms_url,
            params=args,
            # Conversion of headers necessary here? Accepts a simple dict.
            # Apparent answer: no.
            headers=request.headers,
            # stream=True,
        )
        print(f"ncWMS url: {ncwms_response.url}")
        print(f"received ncWMS response: {ncwms_response.status_code}")

        # Return the ncWMS response to the client
        #
        # Notes on requests.get response attributes (ncwms_response):
        #
        # - response.status_code: Integer Code of responded HTTP Status,
        #   e.g. 404 or 200.
        #
        # - response.content: the whole response, as bytes.
        #   The gzip and deflate transfer-encodings are automatically decoded for you.
        #   This is undesirable as we don't need or want to decode such encodings.
        #   I think raw response is more like what we want.
        #
        # - response.raw: the response as an urllib3.response.HTTPRespoinse object
        #   In the rare case that you’d like to get the raw socket response from the
        #   server, you can access r.raw. If you want to do this, make sure you set
        #   stream=True in your initial request. Once you do, you can do this:
        #   r.raw --> <urllib3.response.HTTPResponse object at 0x101194810>
        #   I think this is what I want, but not certain. Compatibility of HTTPResponse
        #   with Flask Response object?
        #
        # - response.headers: Case-insensitive Dictionary of Response Headers. For
        #   example, headers['content-encoding'] will return the value of a
        #   'Content-Encoding' response header. Compatibility of this object with
        #   Response(headers=)?
        #
        #
        # Notes on flask.Response:
        #
        # - response:
        #
        # - status: A string with a response status.
        #
        # - headers: A Headers object representing the response headers.
        #   Headers: An object that stores some headers. It has a dict-like interface
        #   but is ordered and can store the same keys multiple times.
        return Response(
            response=ncwms_response.content,
            # response=ncwms_response.raw,  # ??
            status=str(ncwms_response.status_code),
            headers=ncwms_response.headers.items(),
        )

    return app


def translate_dataset_id(session, dataset_id, prefix):
    """
    Translate a dataset identifier that is a modelmeta unique_id to an equivalent
    dynamic dataset identifier with the specified prefix.
    """
    filepath = (
        session.query(DataFile.filename)
            .filter(DataFile.unique_id == dataset_id)
            .scalar()
    )
    return f"{prefix}{filepath}"


def translate_layer_ids(session, layer_id, prefix):
    """
    Translate a layer identifier containing a dataset identifier that is a modelmeta
    unique_id to an equivalent dynamic layer identifier with the specified prefix.

    Note: A layer identifier has the form <dataset id>/<variable id>.

    :param session: (sqlalchemy.orm.Session) Session for modelmeta database
    :param layer_id: (str) Layer identifier
    :param prefix: (str) Dynamic dataset prefix
    :return: (str) Dynamic dataset layer identifier
    """
    dataset_id, variable_id = layer_id.split('/')
    dyn_dataset_id = translate_dataset_id(session, dataset_id, prefix)
    return f"{dyn_dataset_id}/{variable_id}"

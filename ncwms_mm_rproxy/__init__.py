import os
import sys

from flask import Flask, request, Response
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import requests
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from modelmeta import DataFile


def create_app(test_config=None):
    # app = Flask(__name__, instance_relative_config=True)
    app = Flask(__name__)
    CORS(app)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.getenv(
            "PCDS_DSN",
            "postgresql://ce_meta_ro@db3.pcic.uvic.ca/ce_meta_12f290b63791"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ECHO=False,
        SQLALCHEMY_ENGINE_OPTIONS=dict(
            echo_pool="debug",
            pool_size=20,
            pool_recycle=3600,
        )
    )
    # if test_config is None:
    #     # load the instance config, if it exists, when not testing
    #     # TODO: Should the file name be specified by an env var?
    #     app.config.from_pyfile("config.py", silent=True)
    # else:
    #     # load the test config if passed in
    #     app.config.from_mapping(test_config)

    db = SQLAlchemy(app)
    translations = get_all_translations(db.session)
    print(
        f"Loaded translations. "
        f"{len(translations)} items. "
        f"{sys.getsizeof(translations)} bytes"
    )

    ncwms_url = os.getenv(
        "NCWMS_URL",
        "https://services.pacificclimate.org/dev/ncwms"
    )

    all_layer_id_keys = set(
        os.getenv("NCWMS_LAYER_PARAM_NAMES", "layers,layer,layername,query_layers")
            .split(',')
    )
    all_dataset_id_keys = set(
        os.getenv("NCWMS_DATASET_PARAM_NAMES", "dataset")
            .split(',')
    )

    @app.route("/dynamic/<prefix>", methods=["GET"])
    def dynamic(prefix):
        # print(f"Incoming args: {request.args}")
        # print(f"Incoming headers: {request.headers}")
        args = request.args.copy()

        # Translate args containing layer identifiers
        layer_id_keys = {key for key in args if key.lower() in all_layer_id_keys}
        for key in layer_id_keys:
            args[key] = translate_layer_ids(translations, args[key], prefix)

        # Translate args containing pure dataset identifiers
        dataset_id_keys = {key for key in args if key.lower() in all_dataset_id_keys}
        for key in dataset_id_keys:
            args[key] = translate_dataset_ids(translations, args[key], prefix)

        # print(f"Outgoing args: {args}")

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
        # print("sending ncWMS request")
        ncwms_response = requests.get(
            ncwms_url,
            params=args,
            headers=request.headers,
            stream=True,
        )
        # print(f"ncWMS url: {ncwms_response.url}")
        # print(f"received ncWMS response: {ncwms_response.status_code}")

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
            response=ncwms_response.raw,
            status=str(ncwms_response.status_code),
            headers=ncwms_response.headers.items(),
        )

    @app.errorhandler(KeyError)
    def handle_no_translation(e):
        return e.args[0], 404

    @app.errorhandler(MultipleResultsFound)
    def handle_multi_translation(e):
        return e._message(), 500

    return app


def get_all_translations(session):
    results = (
        session.query(
            DataFile.unique_id.label("unique_id"),
            DataFile.filename.label("filepath"),
        ).all()
    )
    return {r.unique_id: r.filepath for r in results}


id_separator = ','


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
    Translate a dataset identifier that is a modelmeta unique_id to an equivalent
    dynamic dataset identifier with the specified prefix.
    """
    try:
        filepath = translations[dataset_id]
    except KeyError:
        raise KeyError(
            f"Dataset id '{dataset_id}' not found in metadata database."
        )
    return f"{prefix}{filepath}"


def translate_layer_id(session, layer_id, prefix):
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

from functools import wraps
import flask
from flask import Flask, jsonify
from flask.ext.restful import Api
import authorized

import server_config
import string_constants

app = Flask(__name__)

app.config.from_object(server_config.ProductionConfig)

# @app.after_request
# def add_cache_control(response):
#     response.headers['Cache-Control'] = 'public, max-age=%i' % app.config["CACHE_CONTROL"]
#     return response

def exception_handler(app):
    """Overrides the default exception handler to return JSON."""
    handle_exception = app.handle_user_exception
    @wraps(handle_exception)
    def ret_val(exception):
        exc = handle_exception(exception)
        message = ''
        if exc.message == '' or exc.code == 400:
            
            # Create message based on HTTP code
            if exc.code == 400:
                if exc.message == '':
                    message = string_constants.kServer400Error_WithoutMessage
                else:
                    message = string_constants.kServer400Error_WithMessage % exc.message
            elif exc.code == 401:
                message = string_constants.kServer401Error
            elif exc.code == 403:
                message = string_constants.kServer403Error
            elif exc.code == 404:
                message = string_constants.kServer404Error
            elif exc.code == 405:
                message = string_constants.kServer405Error
            elif exc.code == 406:
                message = string_constants.kServer406Error
            elif exc.code == 408:
                message = string_constants.kServer408Error
            elif exc.code == 500:
                message = string_constants.kServer500Error
            elif exc.code == 503:
                message = string_constants.kServer503Error
        else:
            message = exc.message
                
        response = jsonify(     message   = message,
                                status    = False,
                                HTTP_CODE = exc.code
                            ) 
        response.status_code = exc.code
        return response
        
    return ret_val

# Override the exception handler.
app.handle_user_exception = exception_handler(app)

# Redirect every request to the newest api functions
@app.before_request
def before_request():
    #TODO Eventually use the version number in the HTTP headers to redirect to certain api endpoints but for now
    #TODO directing to current v1 is fine.
    device_token = None
    request_timestamp = None

    if flask.request.get_json() is not None:
        if "params" in flask.request.get_json():
            device_token = flask.request.get_json()["params"]["device_token"]
            request_timestamp = flask.request.get_json()["params"]["request_timestamp"]
    elif "device_token" in flask.request.args and "request_timestamp" in flask.request.args:
        request_timestamp = flask.request.args["request_timestamp"]
        device_token = flask.request.args["device_token"]

    notAuthorized = False
    if flask.request.endpoint != 'static':
        if device_token is None or request_timestamp is None:
            notAuthorized = True
        elif authorized.verifyDeviceToken(device_token, request_timestamp) is False:
            notAuthorized = True

        if notAuthorized == True:
            response = jsonify(     message   = string_constants.kServer401Error,
                                    status    = False,
                                    HTTP_CODE = 401
                                )
            response.status_code = 401
            return response

        api_version = ["api", app.config["API_VERSION"]]
        full_path = flask.request.full_path.split('/')

        if "redir" not in flask.request.args and full_path[1] != "?":
            actual_path = '/'.join([i for i in full_path if i not in api_version])
            return flask.redirect("api/"+app.config["API_VERSION"]+actual_path+"&redir=true", code=307)


api = Api(app)
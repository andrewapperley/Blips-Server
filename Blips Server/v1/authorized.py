from flask import jsonify

from datetime import date, datetime
from sqlalchemy import exc
import string_constants
import hashlib


def authorized(user_id, access_token, session):
        import user
        # Check if the user is allowed to access this method
        access = session.query(user.ActiveUser).filter(user.ActiveUser.user_id == user_id).filter(user.ActiveUser.access_token == access_token).first()
        user_deactivated = session.query(user.UserModel).filter(user.UserModel.user_id == user_id).first()
        if user_deactivated != None:
            if user_deactivated.deactivated == 1:
                return notActivatedResponse()
        else:
            return noUserResponse()
        if access == None:
            return notActiveResponse()
        elif access.active == False:
            return notActiveResponse()
        
        today_date = datetime.combine(date.today(), datetime.min.time())
        
        if access.expiry_date <= today_date:
            access.active = False
            session.commit()
            try:
                session.delete(access)
                session.commit()
                session.close()
            except exc.SQLAlchemyError:
                return databaseError()

            return notActiveResponse()
        return True


def notActiveResponse():
    response = jsonify(         message   = string_constants.kServerAuthorizeUserNotActive,
                                status    = False,
                                HTTP_CODE = 401
                            )
    response.status_code = 401
    return response


def noUserResponse():
    response = jsonify(         message   = string_constants.kServerAuthorizeUserDoesntExist,
                                status    = False,
                                HTTP_CODE = 401
                            )
    response.status_code = 401
    return response


def notActivatedResponse():
    response = jsonify(         message   = string_constants.kServerAuthorizeUserDeactivated,
                                status    = False,
                                HTTP_CODE = 401
                            )
    response.status_code = 401
    return response


def wrongParams():
    response = jsonify(         message   = string_constants.kServerAuthorizeWrongParamsSent,
                                status    = False,
                                HTTP_CODE = 400
                            )
    response.status_code = 400
    return response


def databaseError():
    response = jsonify(         message   = string_constants.kServerAuthorizeDatabaseError,
                                status    = False,
                                HTTP_CODE = 500
                            )
    response.status_code = 500
    return response


def verifyDeviceToken(token, timestamp):
    from app import app
    verified = (token == hashlib.sha256(timestamp + app.config["SHARED_PHRASE"]).hexdigest())
    return verified
import random
import hashlib
import os
import errno
import base64
from datetime import datetime
import calendar
import time

import flask
from flask import jsonify
from flask.ext.restful import Resource
from sqlalchemy import Column, String, DateTime, SmallInteger, ForeignKey, exc, Integer, not_, exists, BLOB, UnicodeText
from sqlalchemy.orm import *
from sqlalchemy.ext.hybrid import hybrid_property
import pytz

import database
from database import Base
from app import app
import authorized
import email_handling
import string_constants
from boto.s3.connection import S3Connection, Bucket, Key


class UserModel(Base):
    __tablename__ = 'users'
    user_id = Column(Integer, primary_key=True)
    username = Column(String(app.config["COLUMN_MAX_LENGTH"]))
    password = Column(String(app.config["COLUMN_MAX_LENGTH"]))
    password_salt = Column(String(app.config["COLUMN_MAX_LENGTH"]))
    profile_image = Column(String(app.config["COLUMN_MAX_LENGTH"]))
    _display_name = Column('display_name', UnicodeText())
    deactivated = Column(SmallInteger)
    password_reset = Column(SmallInteger)

    @hybrid_property
    def display_name(self):
        __display_name = self._display_name
        if type(self) is UserModel:
            __display_name = __display_name.decode('unicode_escape')
        return __display_name

    @display_name.setter
    def display_name(self, value):
        _value = value.encode('unicode_escape')

        self._display_name = _value

    def __init__(self, user_id, profile_image, username, password, password_salt, display_name, deactivated=False,
                 password_reset=False):
        self.user_id = user_id
        self.username = username
        self.password = password
        self.password_salt = password_salt
        self.profile_image = profile_image
        self.display_name = display_name
        self.deactivated = deactivated
        self.password_reset = password_reset

    def __repr__(self):
        return "<User('%s', '%s', '%s', '%s', '%s', '%i', '%i')>" % (self.user_id, self.profile_image, self.username, self.password, self.display_name, self.deactivated, self.password_reset)


class ActiveUser(Base):
    __tablename__ = 'active_users'
    user_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), primary_key=True)
    access_token = Column(String(app.config["COLUMN_MAX_LENGTH"]))
    expiry_date = Column(DateTime)
    active = Column(SmallInteger)

    def __init__(self, user_id, access_token, expiry_date, active):
        self.user_id = user_id
        self.access_token = access_token
        self.expiry_date = expiry_date
        self.active = active

    def __repr__(self):
        return "<ActiveUser('%s', '%s', '%s', '%i')>" % (self.user_id, self.access_token, self.expiry_date, self.active)


class Connection(Base):
    __tablename__ = 'connections'
    connection_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), primary_key=True)
    user1 = Column(Integer, ForeignKey(UserModel.user_id))
    user2 = Column(Integer, ForeignKey(UserModel.user_id))
    user1_model = relationship('UserModel', foreign_keys='Connection.user1')
    user2_model = relationship('UserModel', foreign_keys='Connection.user2')
    start_date = Column(DateTime)
    approved = Column(SmallInteger)
    disabled = Column(SmallInteger)

    def __init__(self, connection_id, user1, user2, start_date, approved):
        self.connection_id = connection_id
        self.user1 = user1
        self.user2 = user2
        self.start_date = start_date
        self.approved = approved
        self.disabled = 0

    def __repr__(self):
        return "<Connection('%s', '%i', '%i', '%s', '%i', '%i')>" % (self.connection_id, self.user1, self.user2, self.start_date, self.approved, self.disabled)

class Receipt(Base):
    __tablename__ = 'receipts'
    receipt_id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_data = Column(BLOB)
    receipt_date = Column(Integer)
    receipt_user_id = Column(Integer)
    receipt_product_id = Column(String(app.config["COLUMN_MAX_LENGTH"]))

    def __init__(self, receipt_data, receipt_date, receipt_user_id, receipt_product_id):
        self.receipt_id = None
        self.receipt_data = receipt_data
        self.receipt_date = receipt_date
        self.receipt_user_id = receipt_user_id
        self.receipt_product_id = receipt_product_id

    def __repr__(self):
        return "<Receipt('%i', '%s', '%i', '%i', '%s')>" % (self.receipt_id, self.receipt_data, self.receipt_date, self.receipt_user_id, self.receipt_product_id)


class User(Resource):
    # Creating a user
    # Required Params:
    # username - string (Email)
    # display_name - string
    # password - string
    # profile_image - string
    @app.route('/api/'+app.config["API_VERSION"]+'/user/', methods=["POST"])
    def createUser():
        req = flask.request.get_json()['params']
        username = req['username']
        display_name = req['display_name']
        password = req['password']
        profile_image = None
        if "profile_image" in req:
            profile_image = base64.b64decode(req['profile_image'])

        if username is None or password is None or display_name is None:
            return authorized.wrongParams()

        session = database.DBSession()
        userCheck = session.query(UserModel).filter(UserModel.username == username).first()
        if userCheck is not None:
            response = jsonify(message=string_constants.kServerUserAlreadyExistsError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            return response

        # Create User object
        salt = hashlib.sha256(str(time.time() * random.randint(1, 9999999))).hexdigest()
        password_hash = hashlib.sha256(password + salt).hexdigest()
        new_User = UserModel(None, 'profileImage', username, password_hash, salt, display_name, False)
        user_id = ""

        try:
            session.add(new_User)
            session.commit()
            user_id = session.query(UserModel.user_id).filter(UserModel.username == username).first()[0]

            if app.config["AWS_S3"]:
                if profile_image is not None:
                    aws_s3_connection = S3Connection(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
                    aws_s3_bucket = Bucket(aws_s3_connection, app.config['AWS_BUCKET_NAME'])
                    aws_s3_profile_image_key = Key(aws_s3_bucket)
                    aws_s3_profile_image_key.key = User.getProfileImage(user_id)
                    aws_s3_profile_image_key.content_type = app.config['AWS_KEY_CONTENT_TYPE']
                    aws_s3_profile_image_key.set_contents_from_string(profile_image, replace=True)

            # Create Notification User object
            from notification import RegisteredNotificationUserModel
            notification_user = RegisteredNotificationUserModel(user_id, "")
            session.add(notification_user)
            session.commit()

        except exc.SQLAlchemyError:
            response = jsonify(message=string_constants.kServerUserCreationError,
                               status=False,
                               HTTP_CODE=404
            )
            response.status_code = 404
            session.close()
            return response

        # Send welcome email to new user
        email_handling.send_email(username, (string_constants.kWelcomeEmail % display_name.encode('unicode_escape')), string_constants.kWelcomeEmailSubject)

        session.close()
        response = jsonify(message=string_constants.kServerUserSignUpSuccess,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        return response

        # Getting user information
        # Required Params:
        # user_id - string
        # user - string
        # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/info', methods=["GET"])
    def getUserInfo():
        user_id = flask.request.args.get('user_id')
        other_user_id = flask.request.args.get('user')
        access_token = flask.request.args.get('access_token')
        session = database.DBSession()

        if user_id is None or access_token is None or other_user_id is None:
            session.close()
            return authorized.wrongParams()

        # check if they are None and check the access_token against the active_users table
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        user = session.query(UserModel).filter(UserModel.user_id == other_user_id).first()
        if user is None:
            response = jsonify(message=string_constants.kServerUserNotFoundError,
                               status=False,
                               HTTP_CODE=200,
                               User=None
            )
            response.status_code = 200
            session.close()
            return response
        else:
            response = jsonify(message=string_constants.kServerUserInfoResponseSuccess,
                               status=True,
                               HTTP_CODE=200,
                               User={'user_id': user.user_id,
                                     'profile_image': User.getProfileImage(user.user_id),
                                     'connections': None,
                                     'display_name': user.display_name,
                                     'deactivated': user.deactivated
                               }
            )
            response.status_code = 200
            session.close()
            return response

            # Deleting a user
            # Required Params:
            # user_id - string
            # password - string
            # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/removeUser/', methods=["POST"])
    def removeUser():
        req = flask.request.get_json()['params']

        user_id = req['user_id']
        password = req['password']
        access_token = req['access_token']

        session = database.DBSession()

        if user_id is None and access_token is None and password is None:
            session.close()
            return authorized.wrongParams()

        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        user = session.query(UserModel).filter(UserModel.user_id == user_id).first()

        if user.password != hashlib.sha256(password + user.password_salt).hexdigest():
            response = jsonify(message=string_constants.kServerDeactivatedNotAuthorizedError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        if user.deactivated is True:
            response = jsonify(message=string_constants.kServerUserAlreadyDeactivatedError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        #Deactivate the user's account
        session.query(UserModel).filter(UserModel.user_id == user_id).update({'deactivated': 1}, synchronize_session='fetch')

        #Remove users access token
        active_user = session.query(ActiveUser).filter(ActiveUser.user_id == user_id).filter(
            ActiveUser.access_token == access_token).first()

        if active_user is not None:
            session.delete(active_user)

        #Remove user from registered notifications users
        from notification import RegisteredNotificationUserModel
        notification_user = session.query(RegisteredNotificationUserModel).filter(RegisteredNotificationUserModel.user_id == user_id).first()

        if notification_user is not None:
            session.delete(notification_user)

        session.commit()
        session.close()
        response = jsonify(message=string_constants.kServerUserDeactivatedSuccess,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        return response


        # Updating a user
        # Required Params:
        # user_id - string
        # changes - dictionary <List of items to change>
        # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/updateUser/', methods=["POST"])
    def updateUser():
        req = flask.request.get_json()['params']
        user_id = req['user_id']
        access_token = req['access_token']
        session = database.DBSession()
        changes = {}
        if 'changes' in req:
            changes = req['changes']

        if user_id is None or access_token is None:
            session.close()
            return authorized.wrongParams()

        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        if (len(changes) == 0):
            response = jsonify(message=string_constants.kServerUserUpdateNoInfoToUpdateError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        # Loop through changes dictionary and extract the white listed keys that we allow the user to change
        allowed_keys = ['display_name', 'password', 'username', 'profile_image']
        allowed_changes = {}
        for key in changes:
            if key in allowed_keys:
                if key == 'display_name':
                    changes[key] = changes[key].encode('unicode_escape')
                allowed_changes.update({key: changes[key]})

        if 'profile_image' in allowed_changes:
            try:
                if app.config["AWS_S3"]:
                    profile_image = base64.b64decode(allowed_changes['profile_image'])
                    aws_s3_connection = S3Connection(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
                    aws_s3_bucket = Bucket(aws_s3_connection, app.config['AWS_BUCKET_NAME'])
                    aws_s3_profile_image_key = Key(aws_s3_bucket)
                    aws_s3_profile_image_key.key = User.getProfileImage(user_id)
                    aws_s3_profile_image_key.content_type = app.config['AWS_KEY_CONTENT_TYPE']
                    aws_s3_profile_image_key.set_contents_from_string(profile_image, replace=True)
            except:
                pass
            del allowed_changes['profile_image']

        if 'password' in allowed_changes:
            allowed_changes['password'] = allowed_changes['password']
            salt = hashlib.sha256(str(time.time() * random.randint(1, 9999999))).hexdigest()
            password_hash = hashlib.sha256(allowed_changes['password'] + salt).hexdigest()
            allowed_changes['password'] = password_hash
            allowed_changes['password_reset'] = False
            allowed_changes['password_salt'] = salt

            # Create an expiry date 7 days from today
            expiry_date = datetime.today()
            expiry_date = User.updateTokenExpiryDate(expiry_date)

            try:
                activeUser = session.query(ActiveUser).filter(ActiveUser.user_id == user_id).filter(
                    ActiveUser.access_token == access_token).first()
                # Create a hash of the users information and save it as their access_token
                access_token = hashlib.sha256(str(user_id) + password_hash + expiry_date.strftime(
                    string_constants.kDateFormatMinimalDate)).hexdigest()
                activeUser.access_token = access_token
                activeUser.expiry_date = expiry_date
                activeUser.active = True
            except exc.SQLAlchemyError:
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response
        else:
            activeUser = None

        # Update each property of the user
        if len(allowed_changes) > 0:
            try:
                session.query(UserModel).filter(UserModel.user_id == user_id). \
                    update(allowed_changes, synchronize_session='fetch')
                session.commit()
            except exc.SQLAlchemyError:
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response

        # Get updated user to return
        user = session.query(UserModel).filter(UserModel.user_id == user_id).first()

        response = jsonify(message=string_constants.kServerUserInfoUpdatedSuccess,
                           status=True,
                           HTTP_CODE=200,
                           User={'username': user.username,
                                 'user_id': user.user_id,
                                 'connections': None,
                                 'display_name': user.display_name,
                                 'deactivated': user.deactivated,
                                 'profile_image': User.getProfileImage(user_id)
                           },
                           access_token=activeUser is not None and activeUser.access_token or "",
                           expiry_date=activeUser is not None and activeUser.expiry_date.strftime(
                               string_constants.kDateFormatFullDate) or ""
        )
        response.status_code = 200
        session.close()
        return response

        # Update Token for user
        # Required Params:
        # user_id - string
        # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/update_token', methods=["POST"])
    def updateToken():
        session = database.DBSession()
        req = flask.request.get_json()['params']
        user_id = req['user_id']
        access_token = req['access_token']

        if user_id is None and access_token is None:
            return authorized.wrongParams()

        activeUser = session.query(ActiveUser).filter(ActiveUser.user_id == user_id).filter(
            ActiveUser.access_token == access_token).first()
        if activeUser is None:
            return authorized.notActiveResponse()
        else:
            user = session.query(UserModel).filter(UserModel.user_id == user_id).first()
            if user is None:
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                return response
            else:
                expiry_date = datetime.today()
                expiry_date = User.updateTokenExpiryDate(expiry_date)
                # Create a hash of the users information and save it as their access_token
                try:
                    access_token = hashlib.sha256(str(user.user_id) + user.password + expiry_date.strftime(
                        string_constants.kDateFormatMinimalDate)).hexdigest()
                    activeUser.access_token = access_token
                    activeUser.expiry_date = expiry_date
                    activeUser.active = True
                    session.commit()
                except exc.SQLAlchemyError:
                    response = jsonify(message=string_constants.kServerGeneric500Error,
                                       status=False,
                                       HTTP_CODE=500
                    )
                    response.status_code = 500
                    session.close()
                    return response

                response = jsonify(message=string_constants.kServerUserTokenUpdatedSuccess,
                                   status=True,
                                   HTTP_CODE=200,
                                   access_token=access_token,
                                   expiry_date=expiry_date
                )
                response.status_code = 200
                return response


                # Check username
                # Required Params:
                # username - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/check_username', methods=["GET"])
    def checkUsername():
        session = database.DBSession()
        req = flask.request.args
        username = req['username']
        username_check = session.query(UserModel).filter(UserModel.username == username).first()
        response = jsonify(
            message=username_check is None and string_constants.kServerUserUsernameAvailableSuccess or string_constants.kServerUserUsernameAvailableError,
            status=username_check is None and True or False,
            HTTP_CODE=200
        )
        response.status_code = 200
        session.close()
        return response

    # Logout a user
    # Required Params:
    # user_id - string
    # access_token = string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/logout/', methods=["POST"])
    def logout():
        req = flask.request.get_json()['params']

        user_id = req['user_id']
        access_token = req['access_token']
        session = database.DBSession()

        if user_id is None and access_token is None:
            session.close()
            return authorized.wrongParams()

        active_user = session.query(ActiveUser).filter(ActiveUser.user_id == user_id).filter(
            ActiveUser.access_token == access_token).first()
        if active_user is not None:
            session.delete(active_user)
            session.commit()
            response = jsonify(message=string_constants.kServerUserLoggedOutSuccess,
                               status=True,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response
        else:
            response = jsonify(message=string_constants.kServerUserLoggedOutError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

    # Login a user
    # Required Params:
    # username - string
    # password - string (can be nil)
    # access_token = string (can be nil)

    @app.route('/api/'+app.config["API_VERSION"]+'/user/login/', methods=["POST"])
    def login():
        req = flask.request.get_json()['params']

        username = req['username']
        if req['password'] != '':
            password = req['password']
        else:
            password = ''
        access_token = None
        if 'access_token' in req:
            access_token = req['access_token']
        session = database.DBSession()

        if username is None:
            session.close()
            return authorized.wrongParams()

        def loginWithAccess_tokenAndUsername(username, access_token):
            user = checkUserWithNoPassword(username)
            if user is not None:
                access_check = checkActiveUser(user.user_id, access_token)
                if access_check is True:
                    return setActiveUser(user)
                else:
                    return access_check
            else:
                return incorrectUser()

        def checkUserWithNoPassword(username):
            user = session.query(UserModel).filter(UserModel.username == username).first()
            if (user is None):
                return None
            else:
                return user

        def checkUser(username, password):
            user = session.query(UserModel).filter(UserModel.username == username).first()
            if user is None or user.password != hashlib.sha256(str(password) + user.password_salt).hexdigest():
                return None
            else:
                return user

        def checkActiveUser(user_id, access_token):
            activeUser = session.query(ActiveUser).filter(ActiveUser.user_id == user_id).filter(access_token == ActiveUser.access_token).first()

            if activeUser is None:
                return incorrectUser()
            else:
                return True

        def setActiveUser(user):
            activeUser = session.query(ActiveUser).filter(ActiveUser.user_id == user.user_id).first()

            expiry_date = None
            if activeUser is None:
                # User exists but isn't logged in already, add user to active user and return access_token
                # Create an expiry date 7 days from today

                expiry_date = datetime.today()
                expiry_date = User.updateTokenExpiryDate(expiry_date)
                # Create a hash of the users information and save it as their access_token
                access_token = hashlib.sha256(str(user.user_id) + user.password + expiry_date.strftime(
                    string_constants.kDateFormatMinimalDate)).hexdigest()
                activeUser = ActiveUser(str(user.user_id), access_token, expiry_date, True)
                try:
                    session.add(activeUser)
                    session.commit()
                except exc.SQLAlchemyError:
                    response = jsonify(message=string_constants.kServerGeneric500Error,
                                       status=False,
                                       HTTP_CODE=500
                    )
                    response.status_code = 500
                    session.close()
                    return response

            try:
                if user.deactivated == 1:
                    user.deactivated = 0
                activeUser.expiry_date = User.updateTokenExpiryDate(activeUser.expiry_date)
                session.commit()
            except exc.SQLAlchemyError:
                    response = jsonify(message=string_constants.kServerGeneric500Error,
                                        status=False,
                                        HTTP_CODE=500
                    )
                    response.status_code = 500
                    session.close()
                    return response

            return returnUserInfo(user, activeUser.access_token, activeUser.expiry_date)


        def returnUserInfo(user, access_token, expiry_date):

            UTC_tz = pytz.timezone('UTC')
            expiry_date = UTC_tz.localize(expiry_date).astimezone(pytz.utc)

            response = jsonify(message=string_constants.kServerUserLoggedInSuccess,
                               status=True,
                               HTTP_CODE=200,
                               User={'username': user.username,
                                     'user_id': user.user_id,
                                     'profile_image': User.getProfileImage(user.user_id),
                                     'connections': None,
                                     'display_name': user.display_name,
                                     'deactivated': user.deactivated

                               },
                               access_token=access_token,
                               expiry_date=expiry_date.strftime(string_constants.kDateFormatFullDate)
            )
            response.status_code = 200
            session.commit()
            session.close()
            return response


        def incorrectUser():
            response = jsonify(message=string_constants.kServerUserLoggedInError,
                               status=False,
                               HTTP_CODE=401,
                               User=None,
                               access_token=None,
                               expiry_date=None
            )
            response.status_code = 401
            session.close()
            return response

        # Check if username/password match if not then use access token and username, if that fails then return 401
        if ((username is not None and password is not None) or username is not '' and password is not '') and access_token is None or access_token is '':
            user = checkUser(username, password)
            if user is not None:
                return setActiveUser(user)
            else:
                return incorrectUser()
        elif (username is not None and access_token is not None) or (username is not '' and access_token is not ''):
            return loginWithAccess_tokenAndUsername(username, access_token)

        return incorrectUser()

        # Create a connection between two users
        # Required Params:
        # user_id - string
        # user2 - string
        # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/connection/', methods=["POST"])
    def connection():
        req = flask.request.get_json()['params']
        user_id = req['user_id']
        user2 = req['user2']
        access_token = req['access_token']
        session = database.DBSession()

        if user_id is None and access_token is None and user2 is None:
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        connection_check_query_a = session.query(Connection).filter(Connection.user1 == user_id).filter(
            Connection.user2 != user_id).filter(Connection.user2 == user2).filter(Connection.user1 != user2)
        connection_check_query_b = session.query(Connection).filter(Connection.user1 == user2).filter(
            Connection.user1 != user_id).filter(Connection.user2 == user_id).filter(Connection.user2 != user2)

        connection_check = connection_check_query_a.union(connection_check_query_b).first()

        if connection_check is not None:
            if connection_check.disabled == 0:
                response = jsonify(message=string_constants.kServerUserConnectionRequestExistsError,
                                   status=False,
                                   HTTP_CODE=200
                )
                response.status_code = 200
                session.close()
                return response
        try:
            if connection_check is not None:
                if connection_check.disabled == 1:
                    connection_check.disabled = 0
                    connection_check.user2 = (connection_check.user1 == int(user_id)) and connection_check.user2 or connection_check.user1
                    connection_check.user1 = int(user_id)
                    connection_id = connection_check.connection_id

            else:

                connection_id = hashlib.sha256(str(user_id) + str(user2)).hexdigest()
                connection = Connection(connection_id, int(user_id), user2, datetime.utcnow(), False)

                session.add(connection)

            userDisplayName = session.query(UserModel.display_name).filter(UserModel.user_id == int(user_id)).first()
            userDisplayName = userDisplayName[0]

            # Add the notification for the connection request
            from notification import NotificationModel, RegisteredNotificationUserModel

            notification = NotificationModel(user_id, user2, {
                    string_constants.kServerNotificationsType: string_constants.kServerNotificationsTypeConnectionsRequest,
                    string_constants.kServerNotificationsUser_idKey: user_id,
                    string_constants.kServerNotificationsConnection_idKey: connection_id,
                    string_constants.kServerNotificationsUser_NameKey: userDisplayName
                }, calendar.timegm(datetime.utcnow().timetuple()))
            session.add(notification)


            session.commit()
            response = jsonify(message=string_constants.kServerUserConnectionRequestSentSuccess,
                               status=True,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response
        except exc.SQLAlchemyError as e:
            response = jsonify(message=string_constants.kServerUserConnectionRequestSentError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

            # Accept or decline connection request
            # Required Params:
            # user_id - string
            # connection_id - string
            # status - bool
            # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/connection_status_change', methods=["POST"])
    def connection_status_change():
        req = flask.request.get_json()['params']

        user_id = req['user_id']
        connection_id = req['connection_id']
        status = req['status']
        access_token = req['access_token']
        session = database.DBSession()

        if user_id is None and access_token is None and connection_id is None and status is not None:
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        connection = session.query(Connection).filter(Connection.connection_id == connection_id).filter(Connection.user2 == int(user_id)).first()
        if connection is not None:
            from video import Timeline, Video

            timeline_check = session.query(Timeline).filter(Timeline.connection_id == connection.connection_id).first()

            if status is False or status == 0:
                if timeline_check is None:
                    session.delete(connection)
                    session.commit()
                    session.close()
            else:

                try:
                    if timeline_check is None:
                        timeline_id = Video.createTimeline(session, user_id, connection_id)
                    else:
                        timeline_id = timeline_check.timeline_id

                    userDisplayName = connection.user2_model.display_name

                    # Add the notification for the connection request confirmation
                    from notification import NotificationModel, RegisteredNotificationUserModel

                    notification = NotificationModel(user_id, connection.user1, {
                            string_constants.kServerNotificationsType: string_constants.kServerNotificationsTypeConnectionsRequestConfirmation,
                            string_constants.kServerNotificationsUser_idKey: connection.user2,
                            string_constants.kServerNotificationsTimeline_idKey: timeline_id,
                            string_constants.kServerNotificationsUser_NameKey: userDisplayName
                        }, calendar.timegm(datetime.utcnow().timetuple()))
                    session.add(notification)

                    session.query(Connection).filter(Connection.connection_id == connection_id).filter(Connection.user2 == user_id).update({'approved': 1})


                    if timeline_id is not None:
                        session.commit()
                        session.close()
                except exc.SQLAlchemyError as e:
                    response = jsonify(message=string_constants.kServerUserAcceptConnectionRequestError,
                                       status=False,
                                       HTTP_CODE=200
                    )
                    response.status_code = 200
                    session.close()
                    return response

            response = jsonify(message=string_constants.kServerUserAcceptConnectionRequestSuccess,
                               status=True,
                               HTTP_CODE=200
            )
            response.status_code = 200
            return response
        else:
            session.close()
            response = jsonify(message=string_constants.kServerUserAcceptConnectionRequestError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            return response

            # Get a list of connections for a user
            # Required Params:
            # user_id - string
            # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/connections/', methods=["GET"])
    def connections():
        req = flask.request.args
        user_id = req['user_id']
        access_token = req['access_token']
        session = database.DBSession()

        if user_id is None and access_token is None:
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        connection_list_query_a = session.query(Connection).filter(Connection.user1 == user_id).filter(
            Connection.approved is True or Connection.approved == 1)
        connection_list_query_b = session.query(Connection).filter(Connection.user2 == user_id).filter(
            Connection.approved is True or Connection.approved == 1)

        from notification import NotificationModel
        notification_list = session.query(NotificationModel).filter(NotificationModel.notification_receiver_id == user_id).filter(NotificationModel.notification_sent == 1).all()

        connection_list = connection_list_query_a.union(connection_list_query_b).all()

        connection_id_list = []
        for c in connection_list:
            connection_id_list.append(c.connection_id)
        from video import Timeline

        timelines = None
        if len(connection_id_list) > 0:
            timelines = session.query(Timeline).filter(Timeline.connection_id.in_(connection_id_list)).all()

        connection_list_r = {'connections': [], 'requests': []}

        if connection_list is not None and len(connection_list) > 0:
            for timeline in timelines:
                for connection in connection_list:
                    if connection.connection_id == timeline.connection_id:
                        new_connection = False
                        video_count = 0
                        if notification_list is not None and len(notification_list) > 0:
                            for notification in notification_list:
                                if notification.notification_payload[string_constants.kServerNotificationsType] == string_constants.kServerNotificationsTypeNewVideo:
                                    if notification.notification_payload[string_constants.kServerNotificationsTimeline_idKey] == timeline.timeline_id:
                                        video_count += 1
                                if notification.notification_payload[string_constants.kServerNotificationsType] == string_constants.kServerNotificationsTypeConnectionsRequestConfirmation:
                                    if notification.notification_payload[string_constants.kServerNotificationsTimeline_idKey] == timeline.timeline_id:
                                        new_connection = True
                        connection_list_r['connections'].append(User.getConnectionModelForReturn(connection, user_id, timeline.timeline_id, video_count, new_connection))
        if notification_list is not None and len(notification_list) > 0:
            request_ids = []
            for notification in notification_list:
                if notification.notification_payload['NotificationType'] == string_constants.kServerNotificationsTypeConnectionsRequest:
                    request_ids.append(notification.notification_sender)
            if len(request_ids) > 0:
                friend_requests = session.query(Connection).filter(Connection.user1.in_(request_ids)).filter(Connection.approved == False or Connection.approved == 0).filter(Connection.user2 == int(user_id)).all()
                for request_model in friend_requests:
                    connection_list_r['requests'].append({
                        'user': User.getSerializedUserModel(request_model.user1_model),
                        'connection_id': request_model.connection_id
                    })

        session.close()
        response = jsonify(message=string_constants.kServerUserConnectionListSuccess,
                           connections=connection_list_r['connections'],
                           requests=connection_list_r['requests'],
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        return response

            # Connections Profile with Timelines
            # Required Params:
            # user_id - string
            # timeline_id - string
            # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/connection/timeline/', methods=["GET"])
    def connectionFromTimeline():
        from video import Timeline, Video

        req = flask.request.args
        user_id = int(req['user_id'])
        timeline_id = req['timeline_id']
        access_token = req['access_token']
        session = database.DBSession()

        if user_id is None and access_token is None and timeline_id is None:
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        timeline = session.query(Timeline).filter(Timeline.timeline_id == timeline_id).first()

        # _response = {
        #                        "message": string_constants.kServerUserConnectionProfileSuccess,
        #                        "status": True,
        #                        "HTTP_CODE": 200
        #     }
        #     if connection is not None:
        #         _response["connection"] = connection

        if timeline is not None:
            connection = User.getConnectionModelForReturn(timeline.connection, user_id, timeline_id, timeline.video_count, False)
            if connection is not None:
                session.close()
                response = jsonify(message=string_constants.kServerUserConnectionProfileSuccess,
                                   status=True,
                                   connection=connection,
                                   HTTP_CODE=200
                )

                response.status_code = 200
                return response
        session.close()
        response = jsonify(message=string_constants.kServerUserConnectionProfileError,
                           status=False,
                           HTTP_CODE=200
            )
        response.status_code = 200
        return response

            # Get a limited profile for a user
            # Required Params:
            # user_id - string
            # user - string
            # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/remove_connection/', methods=["POST"])
    def removeConnection():
        req = flask.request.get_json()['params']
        user_id = req['user_id']
        connection_id = req['connection_id']
        access_token = req['access_token']
        session = database.DBSession()

        if user_id is None and access_token is None and connection_id is None:
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        connection_exists = session.query(exists().where(Connection.connection_id == connection_id)).scalar()

        if connection_exists is not None:
            try:
                connection = session.query(Connection).filter(Connection.connection_id == connection_id).first()
                connection.approved = 0
                connection.disabled = 1
                session.commit()
            except exc.SQLAlchemyError as e:
                session.close()
                response = jsonify( message=string_constants.kServerGeneric500Error,
                                    status=True,
                                    HTTP_CODE=500
                )
                response.status_code = 500
                return response

            session.close()
            response = jsonify( message=string_constants.kServerUserConnectionRemoveProfileSuccess,
                                status=True,
                                HTTP_CODE=200
            )
            response.status_code = 200
            return response
        else:
            session.close()
            response = jsonify( message=string_constants.kServerUserConnectionRemoveProfileFailure,
                                status=False,
                                HTTP_CODE=200
            )
            response.status_code = 200
            return response


    @app.route('/api/'+app.config["API_VERSION"]+'/user/limited/', methods=["GET"])
    def getLimitedProfile():
        import video

        req = flask.request.args
        user_id = req['user_id']
        access_token = req['access_token']
        user = req['user']
        session = database.DBSession()

        if user_id is None and access_token is None or user is None:
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        limited_user = session.query(UserModel).filter(UserModel.user_id == user).first()
        # Get the count of the users video list
        limited_users_video_count = session.query(video.VideoModel).filter(video.VideoModel.user == user).count()
        # Get the count of the users connection list
        connection_list_query_a = session.query(Connection).filter(Connection.user1 == user).filter(
            Connection.approved is True or Connection.approved == 1)
        connection_list_query_b = session.query(Connection).filter(Connection.user2 == user).filter(
            Connection.approved is True or Connection.approved == 1)

        limited_users_connection_list_count = connection_list_query_a.union(connection_list_query_b).count()

        if limited_user is not None:
            session.close()
            response = jsonify(message=string_constants.kServerUserLimitedProfileSuccess,
                               status=True,
                               HTTP_CODE=200,
                               user=User.getSerializedLimitedUserModel(limited_user, limited_users_video_count,
                                                                       limited_users_connection_list_count)

            )
            response.status_code = 200
            return response
        else:
            session.close()
            response = jsonify(message=string_constants.kServerUserLimitedProfileError,
                               user=None,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            return response

            # Search endpoint for finding users by display_name
            # Required Params:
            # user_id - string
            # search_query - string
            # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/search/', methods=["GET"])
    def searchUsers():
        req = flask.request.args
        user_id = req['user_id']
        access_token = req['access_token']
        search_query = req['search_query'].strip().replace("%", "").replace("_", "").replace("?", "").replace("*", "")
        session = database.DBSession()

        if user_id is None and access_token is None or search_query is None or search_query is None or search_query == '':
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        connection_list_query_a = session.query(Connection.user2).filter(Connection.user1 == user_id).filter(
            Connection.approved is True or Connection.approved == 1).filter(Connection.disabled == 0)
        connection_list_query_b = session.query(Connection.user1).filter(Connection.user2 == user_id).filter(
            Connection.approved is True or Connection.approved == 1).filter(Connection.disabled == 0)
        connection_list_query_c = session.query(Connection.user1).filter(Connection.user1 != user_id).filter(Connection.user2 == user_id).filter(
            Connection.approved is False or Connection.approved == 0).filter(Connection.disabled == 0)

        connection_list = connection_list_query_a.union(connection_list_query_b).union(connection_list_query_c).all()

        friends = []

        for friend in connection_list:
            friends.append(friend[0])
        if len(friends) <= 0:
            friends.append(-1)

        filter_search = UserModel.display_name.startswith(search_query)
        if len(search_query) > 1:
            search_query = '%{0}%'.format(search_query)
            filter_search = UserModel.display_name.ilike(search_query)

        search_results = session.query(UserModel).filter(filter_search).filter(UserModel.deactivated == 0).filter(not_(UserModel.user_id.in_(friends))).filter(UserModel.user_id != user_id).all()  #TODO maybe add pagination support

        search_results_r = []
        if search_results is not None:
            for returned_user in search_results:
                search_results_r.append(User.getSerializedLimitedUserModel(returned_user))

        session.close()
        response = jsonify(message=string_constants.kServerUserSearchResponse,
                           users=search_results_r,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        return response

        # Allow user to select new passworduser_id
        # Required Params:
        # username - username
        # token - string
        # new_password - string

    @app.route('/api/'+app.config["API_VERSION"]+'/user/reset_password/confirm', methods=["GET"])
    def resetPasswordConfirmation():
        req = flask.request.args
        username = req['username']
        token = req['token']
        new_password = req['new_password']
        device_token = req['device_token']
        request_timestamp = req['request_timestamp']
        version = app.config["API_VERSION"]

        if username is None and token is None:
            return authorized.wrongParams()

        session = database.DBSession()
        user = session.query(UserModel).filter(UserModel.username == username).first()

        if new_password == '':
            session.close()
            return flask.render_template(string_constants.kResetPasswordTemplateName, username=username, token=token, confirm=False, date=datetime.utcnow().strftime('%Y'), device_token=device_token, request_timestamp=request_timestamp, version=version)

        elif user is None:
            session.close()
            return flask.render_template(string_constants.kResetPasswordTemplateName, username=username, token=token, confirm=False,
                                                 confirm_message=string_constants.kResetPasswordError, date=datetime.utcnow().strftime('%Y'), device_token=device_token, request_timestamp=request_timestamp, version=version)
        elif token != hashlib.sha256(user.username + str(0) + user.password_salt).hexdigest():
            session.close()
            return flask.render_template(string_constants.kResetPasswordTemplateName, username=username, token=token, confirm=False,
                                                 confirm_message=string_constants.kResetPasswordError, date=datetime.utcnow().strftime('%Y'), device_token=device_token, request_timestamp=request_timestamp, version=version)
        else:
            new_password = req['new_password']

            reset_check = session.query(UserModel).filter(UserModel.username == username).first().password_reset
            if user is not None and reset_check == 1:
                if token == hashlib.sha256(user.username + str(0) + user.password_salt).hexdigest():
                    salt = hashlib.sha256(str(time.time() * random.randint(1, 9999999))).hexdigest()
                    password_hash = hashlib.sha256(str(new_password) + str(salt)).hexdigest()
                    session.query(UserModel).filter(UserModel.username == username).update({'password_reset': 0,
                                                                                            'password': password_hash,
                                                                                            'password_salt': salt},
                                                                                           synchronize_session='fetch')
                    active_user = session.query(ActiveUser).filter(ActiveUser.user_id == user.user_id).first()
                    if active_user is not None:
                        session.delete(active_user)
                    session.commit()
                    session.close()
                    return flask.render_template(string_constants.kResetPasswordTemplateName, confirm=True,
                                                 confirm_message=string_constants.kResetPasswordConfirmation, date=datetime.utcnow().strftime('%Y'), device_token=device_token, request_timestamp=request_timestamp, version=version)

            else:
                session.close()
                return flask.render_template(string_constants.kResetPasswordTemplateName, username=username, token=token, confirm=False,
                                                 confirm_message=string_constants.kResetPasswordError, date=datetime.utcnow().strftime('%Y'), device_token=device_token, request_timestamp=request_timestamp, version=version)

                # Reset password using email address and username
                # Required Params:
                # username - username

    @app.route('/api/'+app.config["API_VERSION"]+'/user/reset_password/', methods=["POST"])
    def resetPassword():
        req = flask.request.get_json()['params']
        username = req['username']
        device_token = req["device_token"]
        request_timestamp = req["request_timestamp"]

        session = database.DBSession()

        if username is None is None:
            return authorized.wrongParams()

        user = session.query(UserModel).filter(UserModel.username == username).first()

        if user is None:
            response = jsonify(message=string_constants.kServerUserPasswordResetUserDoesNotExistRequestError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            return response

        if user.password_reset == 1:
            session.close()
            response = jsonify(message=string_constants.kServerUserPasswordResetRequestAlreadyPresent,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            return response
        else:
            email_handling.send_email(username,
                                      string_constants.kEmailResetResponseMessage % string_constants.kResetPasswordLink % (
                                      app.config['API_ADDRESS'], username,
                                      hashlib.sha256(username + str(user.password_reset) + user.password_salt).hexdigest(),
                                      device_token,
                                      request_timestamp),
                                      string_constants.kResetPasswordSubject,
                                      string_constants.kEmailTypeReset)

            session.query(UserModel).filter(UserModel.username == username).update({'password_reset': 1},
                                                                                   synchronize_session='fetch')
            session.commit()
            session.close()

            # temp putting password in response
            response = jsonify(message=string_constants.kServerUserPasswordRequestSentSuccess,
                               status=True,
                               HTTP_CODE=200
            )
            response.status_code = 200
            return response

    # Creating a Receipt
    # Required Params:
    # user_id - string
    # access_token - string
    # receipt_timestamp - int
    # receipt_data - string
    # receipt_product_id - string
    @app.route('/api/'+app.config["API_VERSION"]+'/receipts/', methods=["POST"])
    def createReceipt():
        req = flask.request.get_json()['params']
        user_id = req['user_id']
        access_token = req['access_token']
        receipt_data = req['receiptData']
        receipt_date = req['receiptDate']
        receipt_product_id = req['receiptProductID']

        session = database.DBSession()

        if user_id is None and access_token is None and receipt_data is None and receipt_date is None and receipt_product_id is None:
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        receipt = Receipt(receipt_data, receipt_date, user_id, receipt_product_id)
        try:
            session.add(receipt)
            session.commit()
        except exc.SQLAlchemyError:
            session.close()
            response = jsonify( message=string_constants.kServerGeneric500Error,
                                status=True,
                                HTTP_CODE=500
            )
            response.status_code = 500
            return response

        session.close()
        response = jsonify( message=string_constants.kServerReceiptsPostResponse,
                            status=True,
                            HTTP_CODE=200
        )
        response.status_code = 200
        return response


    # Receipts for User
    # Required Params:
    # user_id - string
    # access_token - string
    @app.route('/api/'+app.config["API_VERSION"]+'/receipts/retrieve', methods=["GET"])
    def receiptsForUser():
        req = flask.request.args
        user_id = req['user_id']
        access_token = req['access_token']

        session = database.DBSession()

        if user_id is None and access_token is None:
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        receipts = session.query(Receipt).filter(Receipt.receipt_user_id == int(user_id)).all()
        receipts_return = []
        if len(receipts) > 0:
            for receipt in receipts:
                receipts_return.append({
                    'receipt_product_id': receipt.receipt_product_id,
                    'receipt_date': receipt.receipt_date,
                    'receipt_data': receipt.receipt_data
                })

        session.close()
        response = jsonify(message=string_constants.kServerReceiptsResponse,
                           receipts=receipts_return,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        return response


    # Get limited userModel ready for JSON for user
    # Required Params:
    # user - UserModel

    @classmethod
    def getSerializedLimitedUserModel(cls, user, videoCount=None, connectionCount=None):
        return {'user_id': user.user_id,  # **
                'profile_image': User.getProfileImage(user.user_id),
                'connections': None,  # *
                'display_name': user.display_name,
                'deactivated': user.deactivated,  # *
                'video_count': videoCount,  # *
                'connection_count': connectionCount  # *
                # * = #No need for this as this is a limited profile
                # ** = Not shown in search results but used to grab full profile if the user searching clicks on this user
        }


    @classmethod
    def getConnectionModelForReturn(cls, connection, username, timeline_id, video_count, new_connection):

        if connection.approved == 0 or connection.disabled == 1:
            return None

        user_model = int(connection.user1) != int(username) and connection.user1_model or connection.user2_model

        connection_r = {
            'friend': User.getSerializedUserModel(user_model),
            'connection_id': connection.connection_id,
            'start_date': connection.start_date,
            'timeline_id': timeline_id,
            'video_count': video_count,
            'new_connection': new_connection
        }

        return connection_r

        # Get userModel ready for JSON for user
        # Required Params:
        # user - UserModel

    @classmethod
    def getSerializedUserModel(cls, user):
        return {'user_id': user.user_id,
                'profile_image': User.getProfileImage(user.user_id),
                'connections': None,  # *
                'display_name': user.display_name,
                'deactivated': user.deactivated
                # * = #No need as this is only ever called from the connection endpoint
        }

        # Get userModel for the username
        # Required Params:
        # username - string
        # session - DBSession

    @classmethod
    def userObjectForUsername(cls, user_id, session, forJSON):
        if user_id is not None or user_id == '':
            user = session.query(UserModel).filter(UserModel.user_id == user_id).first()
            if user is not None:
                if forJSON is True:
                    return User.getSerializedUserModel(user)
                else:
                    return user
            else:
                return None
        else:
            return None

    @classmethod
    def getUserImagePath(cls):
        return app.config["STATIC_FILES_FOLDER"] + "%s"

    @classmethod
    def getUserPath(cls):
        return app.config["STATIC_FILES_FOLDER"] + "/users/%s/"

        # Get profile picture for user
        # Required Params:
        # profile_image_id - string
        # user_id - string

    @classmethod
    def getProfileImage(cls, user_id):
        path = User.getProfileImageDirectory(user_id)+'profileImage'
        return path + '.jpg'

    @classmethod
    def getProfileImageDirectory(cls, user_id):
        path = app.config["STATIC_FILES_FOLDER"] + '/users/' + str(user_id) + '/profileImage/'
        return path

    # Updates the Expiry Date of an access_token to be 7 days
    # If the user doesn't use the app at least once every 7 days they will have to re-login
    @classmethod
    def updateTokenExpiryDate(cls, expiryDate):
        belowNextMonth = True
        if expiryDate.month == 2:
            if expiryDate.day + 7 > 28:
                belowNextMonth = False
                expiryDate = expiryDate.replace(month=3, day=1)
        if expiryDate.month == 4 or expiryDate.month == 6 or expiryDate.month == 9 or expiryDate.month == 11:
            if expiryDate.day + 7 > 30:
                belowNextMonth = False
                expiryDate = expiryDate.replace(month=expiryDate.month + 1, day=1)
        if expiryDate.month == 1 or expiryDate.month == 3 or expiryDate.month == 5 or expiryDate.month == 7 or expiryDate.month == 8 or expiryDate.month == 10 or expiryDate.month == 12:
            if expiryDate.day + 7 > 31:
                if expiryDate.month == 12:
                    belowNextMonth = False
                    expiryDate = expiryDate.replace(year=expiryDate.year + 1, month=1, day=1)
                else:
                    belowNextMonth = False
                    expiryDate = expiryDate.replace(month=expiryDate.month + 1, day=1)
        if belowNextMonth == True:
            expiryDate = expiryDate.replace(day=expiryDate.day + 7)
        return expiryDate
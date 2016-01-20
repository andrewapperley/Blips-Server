import flask
from flask import jsonify
from flask.ext.restful import Resource
from sqlalchemy import Column, String, DateTime, Integer, PickleType, ForeignKey, exc, SmallInteger
from sqlalchemy.orm import *
import database
from database import Base
import authorized
import string_constants
from app import app


class RegisteredNotificationUserModel(Base):
    __tablename__ = 'notification_users'
    user_id = Column(Integer, primary_key=True, autoincrement=False)
    registered_user_token = Column(String(app.config["COLUMN_MAX_LENGTH"]))

    def __init__(self, user_id, user_token):
        self.user_id = user_id
        self.registered_user_token = user_token

    def __repr__(self):
        return "<NotificationUser('%i', '%s')>" % (self.user_id, self.registered_user_token)


class NotificationModel(Base):
    __tablename__ = 'notifications'
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    notification_sender = Column(Integer)
    notification_receiver_id = Column(Integer, ForeignKey(RegisteredNotificationUserModel.user_id))
    registered_notification_user_model = relationship('RegisteredNotificationUserModel',
                                                      foreign_keys='NotificationModel.notification_receiver_id')
    notification_payload = Column(PickleType)
    notification_date = Column(Integer())
    notification_sent = Column(SmallInteger)

    def __init__(self, sender, receiver, payload, date):
        self.notification_id = None
        self.notification_sender = sender
        self.notification_receiver_id = receiver
        self.notification_payload = payload
        self.notification_date = date
        self.notification_sent = 0

    def __repr__(self):
        return "<Notification('%i', '%i', '%i', '%s', '%s', '%i')>" % (
            self.notification_id, self.notification_sender, self.notification_receiver_id, self.notification_payload, self.notification_date,
            self.notification_sent)


class Notification(Resource):
    # Register user for notifications
    # Required Params:
    # user_id - string
    # access_token - string
    # unique_token - string
    @app.route('/api/'+app.config["API_VERSION"]+'/notification/register/', methods=["POST"])
    def notificationRegister():
        req = flask.request.get_json()['params']
        user_id = req['user_id']
        access_token = req['access_token']
        unique_token = req['unique_token']
        session = database.DBSession()

        if user_id is None or access_token is None or unique_token is None:
            session.close()
            return authorized.wrongParams()

        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        registered_user_check = session.query(RegisteredNotificationUserModel.user_id).filter(
            user_id == RegisteredNotificationUserModel.user_id).first()
        if registered_user_check is not None:
            try:
                session.query(RegisteredNotificationUserModel).filter(
                    RegisteredNotificationUserModel.user_id == user_id). \
                    update({'registered_user_token': unique_token}, synchronize_session='fetch')
                session.commit()
            except exc.SQLAlchemyError:
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response
        else:
            try:
                registered_user = RegisteredNotificationUserModel(user_id, unique_token)
                session.add(registered_user)
                session.commit()
            except exc.SQLAlchemyError:
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response

        session.close()
        response = jsonify(message=string_constants.kServerUserRegisteredForNotificationSuccess,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        return response


    # UnRegister user for notifications
    # Required Params:
    # user_id - string
    # access_token - string
    @app.route('/api/'+app.config["API_VERSION"]+'/notification/unregister/', methods=["POST"])
    def notificationUnregister():
        req = flask.request.get_json()['params']
        user_id = req['user_id']
        access_token = req['access_token']
        session = database.DBSession()

        if user_id is None or access_token is None:
            session.close()
            return authorized.wrongParams()

        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        registered_check = session.query(RegisteredNotificationUserModel).filter(
            RegisteredNotificationUserModel.user_id == user_id).first()

        if registered_check is not None:
            try:
                registered_check.registered_user_token = ""
                session.commit()
            except exc.SQLAlchemyError:
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response
        else:
            response = jsonify(message=string_constants.kServerUserUnregisterNotificationFailure,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        response = jsonify(message=string_constants.kServerUserUnregisterNotificationSuccess,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        session.close()
        return response

    # List of notifications for user
    # Required Params:
    # user_id - string
    # access_token - string
    @app.route('/api/'+app.config["API_VERSION"]+'/notification/list/', methods=["GET"])
    def notificationList():
        user_id = flask.request.args.get('user_id')
        access_token = flask.request.args.get('access_token')
        session = database.DBSession()

        if user_id is None or access_token is None:
            session.close()
            return authorized.wrongParams()

        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        registered_user_check = session.query(RegisteredNotificationUserModel.user_id).filter(
            user_id == RegisteredNotificationUserModel.user_id).first()
        notification_count = 0
        if registered_user_check is not None:
            notification_count = session.query(NotificationModel).filter(NotificationModel.notification_receiver_id == int(user_id)).count()

        session.close()
        response = jsonify(message=string_constants.kServerListNotificationSuccess,
                           status=True,
                           HTTP_CODE=200,
                           notification_count=notification_count
            )
        response.status_code = 200
        return response

    # Mark notification as read
    # Required Params:
    # user_id - string
    # access_token - string
    # sender_id - int
    @app.route('/api/'+app.config["API_VERSION"]+'/notification/read/', methods=["POST"])
    def markNotificationsAsRead():
        req = flask.request.get_json()['params']
        user_id = req['user_id']
        access_token = req['access_token']
        sender_id = req['sender_id']
        session = database.DBSession()

        if user_id is None or access_token is None or sender_id is None:
            session.close()
            return authorized.wrongParams()

        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        try:
            session.query(NotificationModel).filter(NotificationModel.notification_sender == sender_id).filter(NotificationModel.notification_receiver_id == user_id).filter(NotificationModel.notification_sent == 1).delete()
            session.commit()
        except exc.SQLAlchemyError as e:
            response = jsonify(message=string_constants.kServerGeneric500Error,
                               status=False,
                               HTTP_CODE=500
            )
            response.status_code = 500
            session.close()
            return response

        session.close()
        response = jsonify(message=string_constants.kServerNotificationReadSuccess,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        return response
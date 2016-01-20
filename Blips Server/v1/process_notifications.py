from notification import NotificationModel
from sqlalchemy import desc
import database
import time
import string_constants
from apns import APNs, Frame, Payload
import sys

def process():

    # Defines a function to translate the notification type into a string
    def getNotificationTitle(type, sender):
        type_r = ""
        if type == string_constants.kServerNotificationsTypeConnectionsRequest:
            type_r = string_constants.kServerNotificationsTypeConnectionsRequestTitle % (sender)
        elif type == string_constants.kServerNotificationsTypeConnectionsRequestConfirmation:
            type_r = string_constants.kServerNotificationsTypeConnectionsRequestConfirmationTitle % (sender)
        elif type == string_constants.kServerNotificationsTypeNewVideo:
            type_r = string_constants.kServerNotificationsTypeNewVideoTitle % (sender)
        return type_r

    if len(sys.argv) > 1:
        a = sys.argv[1]
        b = sys.argv[2]
        c = sys.argv[3]
        d = sys.argv[4]
        database.createDatabase(a, b)
        sandbox = False
    else:
        database.createDatabase()
        c = 'certs/apns-dev-cert.pem'
        d = 'certs/apns-dev-key-noenc.pem'
        sandbox = True

    # database.createDatabase()
    session = database.DBSession()

    pendingNotifications = session.query(NotificationModel).filter(NotificationModel.notification_sent == 0).order_by(
        desc(NotificationModel.notification_date)).all()

    if len(pendingNotifications) < 1:
        return

    apns = APNs(use_sandbox=sandbox, cert_file=c, key_file=d)

    # Send multiple notifications in a single transmission
    frame = Frame()
    identifier = 1
    expiry = time.time() + 3600
    priority = 10

    for notification in pendingNotifications:
        _payload = notification.notification_payload
        display_name = _payload[string_constants.kServerNotificationsUser_NameKey]
        _payload[string_constants.kServerNotificationsUser_NameKey] = None
        if _payload is None:
            _payload = {}
        token_hex = notification.registered_notification_user_model.registered_user_token
        if token_hex is not None:
            payload = Payload(alert=getNotificationTitle(notification.notification_payload[string_constants.kServerNotificationsType], display_name), sound="default", badge=1,
                          custom=_payload)

            frame.add_item(token_hex, payload, identifier, expiry, priority)
        session.query(NotificationModel).filter(
            NotificationModel.notification_id == notification.notification_id).update({'notification_sent': 1})

    apns.gateway_server.send_notification_multiple(frame)

    # Get feedback messages
    for (token_hex, fail_time) in apns.feedback_server.items():
        print token_hex
        print fail_time

    # Remove all pending notifications that were just sent and close the DB session
    session.commit()
    session.close()


"""
Process the notifications
"""
process()
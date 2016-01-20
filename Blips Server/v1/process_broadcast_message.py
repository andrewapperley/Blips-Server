from notification import RegisteredNotificationUserModel
import database
import time
from apns import APNs, Frame, Payload
import sys


def process():

    database.createDatabase(environment="MYSQLURL")
    message = sys.argv[1].replace("_", " ")
    c = 'certs/apns-prod-cert.pem'
    d = 'certs/apns-prod-key-noenc.pem'
    sandbox = False
    # database.createDatabase()
    session = database.DBSession()

    active_users = session.query(RegisteredNotificationUserModel).filter(RegisteredNotificationUserModel.registered_user_token != '').all()

    if len(active_users) < 1 or message is None:
        return

    apns = APNs(use_sandbox=sandbox, cert_file=c, key_file=d)

    # Send multiple notifications in a single transmission
    frame = Frame()
    identifier = 1
    expiry = time.time() + 3600
    priority = 10

    for user in active_users:
        token_hex = user.registered_user_token
        if token_hex is not None:
            payload = Payload(alert=message, sound="default", badge=1)
            frame.add_item(token_hex, payload, identifier, expiry, priority)

    apns.gateway_server.send_notification_multiple(frame)

    # Get feedback messages
    for (token_hex, fail_time) in apns.feedback_server.items():
        print token_hex
        print fail_time

    # Close the DB session
    session.close()


"""
Process the notifications
"""
process()

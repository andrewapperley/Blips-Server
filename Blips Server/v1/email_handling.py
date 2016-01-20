import smtplib
import string_constants
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# List of email addresses for the server
EMAIL_ADDRESSES = {
    string_constants.kEmailTypeReset    : "reset@blipsapp.ca",
    string_constants.kEmailTypeGeneric  : "info@blipsapp.ca"
}

EMAIL_PASSWORD = "Aeph9kewn7"
EMAIL_SERVER_URL = "mail.blipsapp.ca"
SIGNED_BY = "blipsapp.ca"

def send_email(email, message, subject, message_type='generic', isHTML=True):

    from_server_email = EMAIL_ADDRESSES[message_type]

    msg = isHTML is False and MIMEText(str(message), 'plain', 'utf-8') or MIMEMultipart()
    msg['From'] = from_server_email
    msg['To'] = str(email)
    msg['Subject'] = subject
    msg['signed-by'] = SIGNED_BY
    msg['mailed-by'] = SIGNED_BY

    if isHTML is True:
        fp = open("static/email_statics/logo_with_text.png", 'rb')
        img = MIMEImage(fp.read(), 'png')
        img.add_header('Content-Id', '<logoImage>')
        fp.close()
        msg.attach(MIMEText(str(message), 'html', 'utf-8'))
        msg.attach(img)

    s = smtplib.SMTP(EMAIL_SERVER_URL, 26)
    s.login(from_server_email, EMAIL_PASSWORD)
    returnObject = s.sendmail(from_server_email, [str(email)], msg.as_string())
    if returnObject:
        s.quit()
        raise
    s.quit()
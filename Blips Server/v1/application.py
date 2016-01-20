from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from flask.ext.compress import Compress

from app import app, api
import database
from user import User
from video import Video
from notification import NotificationModel, RegisteredNotificationUserModel, Notification

application = app
database.createDatabase()

if __name__ == "__main__":
    app.debug = app.config["DEBUG"]
    compress = Compress()
    compress.init_app(app)
    http_server = HTTPServer(WSGIContainer(app))

    http_server.bind(5000)
    http_server.start()
    IOLoop.instance().start()
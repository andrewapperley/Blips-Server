from datetime import datetime
import calendar
import hashlib
import os
import errno
import random
import base64
import logging
from math import ceil

import flask
from flask import jsonify
from flask.ext.restful import Resource
from sqlalchemy import Column, Integer, String, DateTime, desc, ForeignKey, exc, UnicodeText, SmallInteger, or_
from sqlalchemy.orm import *
from sqlalchemy.ext.hybrid import hybrid_property
from dateutil import parser
import pytz
from boto.s3.connection import S3Connection, Bucket, Key

import database
from database import Base
from app import app
import authorized
import string_constants


class Timeline(Base):
    from user import Connection

    __tablename__ = 'timelines'
    timeline_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), primary_key=True)
    connection_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), ForeignKey(Connection.connection_id))
    connection = relationship('Connection', foreign_keys='Timeline.connection_id')
    video_count = Column(Integer)

    def __init__(self, timeline_id, connection_id, video_count=0):
        self.timeline_id = timeline_id
        self.connection_id = connection_id
        self.video_count = video_count

    def __repr__(self):
        return "<Timeline('%s', '%s', '%i')>" % (self.timeline_id, self.connection_id, self.video_count)

class VideoModel(Base):
    from user import UserModel
    __tablename__ = 'videos'
    date = Column(Integer)
    user = Column(Integer, ForeignKey(UserModel.user_id))
    user_model = relationship('UserModel', foreign_keys='VideoModel.user')
    timeline_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), ForeignKey(Timeline.timeline_id))
    timeline = relationship('Timeline', foreign_keys='VideoModel.timeline_id')
    thumbnail = Column(String(app.config["COLUMN_MAX_LENGTH"]))
    _description = Column('description', UnicodeText())
    video_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), primary_key=True)
    public = Column(SmallInteger)

    def __init__(self, date, user, timeline_id, thumbnail, video_id, description, public=False):
        self.date = date
        self.user = user
        self.timeline_id = timeline_id
        self.thumbnail = thumbnail
        self.video_id = video_id
        self.description = description
        self.public = public

    @hybrid_property
    def description(self):
        __description = self._description
        if type(self) is VideoModel:
            __description = __description.decode('unicode_escape')

        return __description

    @description.setter
    def description(self, value):
        _value = value.encode('unicode_escape')

        self._description = _value

    def __repr__(self):
        return "<Video('%s', '%i', '%s', '%s', '%s', '%s', '%i')>" % (self.date, self.user, self.timeline_id, self.thumbnail, self.video_id, self.description, self.public)


class FlaggedVideoModel(Base):
    __tablename__ = 'flaggedVideos'
    flagged_id = Column(Integer, primary_key=True)
    video_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), ForeignKey(VideoModel.video_id))
    video = relationship('VideoModel', foreign_keys='FlaggedVideoModel.video_id')
    video_path = Column(String(app.config["COLUMN_MAX_LENGTH"]))
    timeStamp = Column(Integer())

    def __init__(self, video_id, video_path, timeStamp):
        self.video_id = video_id
        self.flagged_id = None
        self.video_path = video_path
        self.timeStamp = timeStamp

    def __repr__(self):
        return "<FlaggedVideo('%s', '%s', '%i', '%i')>" % (self.video_id, self.video_path, self.timeStamp, self.flagged_id)


class VideoFavourite(Base):
    __tablename__ = 'video_favourites'
    fav_id = Column(Integer, primary_key=True)
    fav_date = Column(Integer())
    user = Column(Integer)
    video_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), ForeignKey(VideoModel.video_id))
    video = relationship('VideoModel', foreign_keys='VideoFavourite.video_id')
    timeline_id = Column(String(app.config["COLUMN_MAX_LENGTH"]), ForeignKey(Timeline.timeline_id))
    timeline = relationship('Timeline', foreign_keys='VideoFavourite.timeline_id')

    def __init__(self, fav_id, fav_date, user, video_id, timeline_id):
        self.fav_id = fav_id
        self.fav_date = fav_date
        self.user = user
        self.video_id = video_id
        self.timeline_id = timeline_id

    def __repr__(self):
        return "<Video_Favourite('%s', '%i', '%s', '%s')>" % (self.fav_date, self.user, self.video_id, self.timeline_id)


class Video(Resource):
    # Creating a video
    # Required Params:
    # date - date
    # user_id - string
    # timeline_id - string
    # access_token - string
    # description - string
    ####
    ## Optional - client version 1.1.1+ will send these values
    ####
    # video_content - string (Base64 encoded string that will be saved to a file)
    # video_thumbnail - string (Base64 encoded string that will be saved to a file)
    # public_feed - bool (This is checked if video wants to be sent to the public feed)
    @app.route('/api/'+app.config["API_VERSION"]+'/video/', methods=["POST"])
    def createVideo():
        req = flask.request.get_json()['params']
        session = database.DBSession()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(req['user_id'], req['access_token'], session)
        if allowed is not True:
            session.close()
            return allowed

        from user import Connection

        # Create the video and send back a response
        video_date = int(req['date'])
        user_id = req['user_id']
        timeline_id = req['timeline_id']
        if timeline_id == '':
            timeline_id = string_constants.kServerVideoPublicFeedKey
        description = req['description']
        public_feed = False
        if 'public_feed' in req:
            public_feed = bool(req['public_feed'])

        video_content = None
        if 'video_content' in req:
            video_content = base64.b64decode(req['video_content'])

        video_thumbnail = None
        if 'video_thumbnail' in req:
            video_thumbnail = base64.b64decode(req['video_thumbnail'])

        if video_date is None or user_id is None or timeline_id is None or description is None:
            session.close()
            return authorized.wrongParams()

        # Add video_id to the playlist in the relationship
        timeline = None
        if timeline_id != string_constants.kServerVideoPublicFeedKey:
            timeline = session.query(Timeline).filter(Timeline.timeline_id == timeline_id).join(Timeline.connection).filter(Connection.approved == 1).filter(Connection.disabled == 0).first()
            if timeline is None:
                response = jsonify(message=string_constants.kServerVideoTimelineIDDoesntExist,
                                   status=False,
                                   HTTP_CODE=200
                )
                response.status_code = 200
                session.close()
                return response

        video_filename = hashlib.sha256(str(video_date) + user_id + timeline_id).hexdigest()

        # Check if video already exists
        video_check = session.query(VideoModel).filter(VideoModel.video_id == video_filename).first()
        if video_check is not None:
            response = jsonify(message=string_constants.kServerVideoAlreadyExistsError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        try:

            video_path = str(Video.getVideoObjectPath(video_filename, user_id, timeline_id, str(video_date))+".m4v")
            thumbnail_path = str(Video.getVideoThumbnailObjectPath(video_filename, user_id, timeline_id, str(video_date))+".jpg")

            if app.config["AWS_S3"]:
                if video_content is not None and video_thumbnail is not None:
                    aws_s3_connection = S3Connection(app.config['AWS_ACCESS_KEY'], app.config['AWS_SECRET_KEY'])
                    aws_s3_bucket = Bucket(aws_s3_connection, app.config['AWS_BUCKET_NAME'])
                    aws_s3_video_key = Key(aws_s3_bucket)
                    aws_s3_video_key.key = video_path
                    aws_s3_video_key.content_type = app.config['AWS_KEY_CONTENT_TYPE']
                    aws_s3_video_key.set_contents_from_string(video_content, replace=True)
                    aws_s3_thumb_key = Key(aws_s3_bucket)
                    aws_s3_thumb_key.key = thumbnail_path
                    aws_s3_thumb_key.content_type = app.config['AWS_KEY_CONTENT_TYPE']
                    aws_s3_thumb_key.set_contents_from_string(video_thumbnail, replace=True)

            # Create new video object and save it to the database
            new_video = VideoModel(video_date, user_id, timeline_id, video_filename + '_thumb.jpg', video_filename, description, public_feed)
            if timeline is not None:
                timeline.video_count += 1

                from user import UserModel

                userDisplayName = session.query(UserModel.display_name).filter(UserModel.user_id == int(user_id)).first()
                userDisplayName = userDisplayName[0]

                # Add the notification for the new video
                from notification import NotificationModel, RegisteredNotificationUserModel

                notification = NotificationModel(
                    user_id,
                    (int(timeline.connection.user1) == int(user_id)) and timeline.connection.user2 or timeline.connection.user1, {
                        string_constants.kServerNotificationsType: string_constants.kServerNotificationsTypeNewVideo,
                        string_constants.kServerNotificationsTimeline_idKey: timeline_id,
                        string_constants.kServerNotificationsUser_NameKey: userDisplayName
                    }, calendar.timegm(datetime.utcnow().timetuple()))
                session.add(notification)

            session.add(new_video)

            session.commit()
        except exc.SQLAlchemyError as e:
            response = jsonify(message=string_constants.kServerVideoIssueMakingVideo,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response
        else:
            response = jsonify(message=string_constants.kServerVideoCreatedVideoSuccess,
                               status=True,
                               HTTP_CODE=200,
                               Video={
                                   "video_path": video_path,
                                   "thumbnail_path": thumbnail_path
                               }
            )
            response.status_code = 200
            session.close()
            return response

            # Get videos for Timeline by page (10 videos per page)
            # Required Params:
            # user_id - string
            # timeline_ids - ',' string
            # access_token - string
            # page(offset) - int

    @app.route('/api/'+app.config["API_VERSION"]+'/video/getVideos/', methods=["GET"])
    def getVideosAtPage():
        req = flask.request.args
        session = database.DBSession()

        # Create vars for req object params
        user_id = 0
        if req['user_id'] != "":
            user_id = req['user_id']
        access_token = req['access_token']
        page = int(float(req['page'])) + 1
        timeline_ids = req['timeline_ids']
        playlistType = req['type']
        timeline_ids = timeline_ids.split(',')

        # Check for required params
        if user_id is None or access_token is None or page is None or timeline_ids is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True and playlistType != 'publicType':
            session.close()
            return allowed

        page_limit = 10

        playlist = None
        videoCount = 0
        pageCount = 0
        friend_id = None

        from user import Connection

        # Videos are for a summary snapshot of the user's current timelines
        if playlistType == 'summaryType':
            playlist = session.query(VideoModel).filter(VideoModel.user != user_id).filter(
                VideoModel.timeline_id.in_(timeline_ids)).join(VideoModel.timeline).join(Timeline.connection).filter(or_(Connection.user1 == user_id, Connection.user2 == user_id)).filter(Connection.approved == 1).filter(Connection.disabled == 0).order_by(desc(VideoModel.date)).limit(page_limit).offset(
                (page - 1) * page_limit).all()
            videoCount = session.query(VideoModel.video_id).filter(VideoModel.user != user_id).filter(
                VideoModel.timeline_id.in_(timeline_ids)).count()
        # Videos are not from a single timeline and are marked for public viewing
        elif playlistType == 'publicType':
            playlist = session.query(VideoModel).filter(VideoModel.public == 1).order_by(desc(VideoModel.date)).limit(page_limit).offset(
                (page - 1) * page_limit).all()
            videoCount = session.query(VideoModel.video_id).filter(VideoModel.public == 1).count()
        # Videos are for a single timeline
        else:
            playlist = session.query(VideoModel).filter(VideoModel.timeline_id == timeline_ids[0]).join(VideoModel.timeline).join(Timeline.connection).filter(or_(Connection.user1 == user_id, Connection.user2 == user_id)).filter(Connection.approved == 1).filter(Connection.disabled == 0).order_by(
                desc(VideoModel.date)).limit(page_limit).offset((page - 1) * page_limit).all()
            videoCount = session.query(Timeline.video_count).filter(Timeline.timeline_id == timeline_ids[0]).first()[0]

        import user

        if len(timeline_ids) > 0 and playlistType == 'timelineType':
            timeline = session.query(Timeline).filter(Timeline.timeline_id == timeline_ids[0]).first()

            friend_id = timeline.connection.user1
            if timeline.connection.user2 != int(user_id):
                friend_id = timeline.connection.user2

        if playlist is not None and len(playlist) > 0:
            # A list to check against to see if the video being returned is favourited by the user
            favourited_items = []
            if user_id != 0:
                if playlistType == 'publicType':
                    timeline_ids.append("__PUBLIC_FEED__")
                favourites_public = session.query(VideoFavourite.video_id).filter(VideoFavourite.user == user_id).join(VideoFavourite.video).filter(VideoModel.public == 1)
                favourites_all = session.query(VideoFavourite.video_id).filter(VideoFavourite.user == user_id).filter(VideoFavourite.timeline_id.in_(timeline_ids)).join(VideoFavourite.timeline).join(Timeline.connection).filter(Connection.approved == 1).filter(Connection.disabled == 0)
                favourited_items = favourites_all.union(favourites_public).all()
                # favourited_items = session.query(VideoFavourite.video_id).filter(VideoFavourite.user == user_id).filter(VideoFavourite.timeline_id.in_(timeline_ids)).all()
            flagged_items = session.query(FlaggedVideoModel.video_id).filter(VideoModel.user != user_id).filter(VideoModel.timeline_id.in_(timeline_ids)).all()
            filteredFlagged = []
            for flag in flagged_items:
                filteredFlagged.append(flag[0])
            filteredFavourites = []
            for fav in favourited_items:
                filteredFavourites.append(fav[0])
            vids = Video.videoObjectsFromPlaylistArrayForPage(playlist, False, filteredFavourites, filteredFlagged)
            if videoCount < 1:
                videoCount = 1
            else:
                if videoCount - (++ceil(videoCount / page_limit)) * page_limit > 0:
                    pageCount = ++ceil(videoCount / page_limit) + 1
                else:
                    pageCount = ++ceil(videoCount / page_limit)

            videos = []

            if vids['videos'] is not None:
                videos = vids['videos']

            response = jsonify(message=string_constants.kServerVideoVideosForPage,
                               status=True,
                               HTTP_CODE=200,
                               videos=videos,
                               total_pages=int(pageCount),
                               video_count=int(videoCount),
                               friend_image=(friend_id != '' and friend_id is not None) and user.User.getProfileImage(friend_id) or ""
            )
            response.status_code = 200
            session.close()
            return response
        elif playlist is not None and len(playlist) <= 0:

            friend_image = None
            if friend_id is not None:
                friend_image = user.User.getProfileImage(friend_id)

            response = jsonify(message=string_constants.kServerVideoVideosForPage,
                               status=True,
                               HTTP_CODE=200,
                               videos=[],
                               total_pages=0,
                               video_count=0,
                               friend_image=friend_image
            )
            response.status_code = 200
            session.close()
            return response
        else:
            response = jsonify(message=string_constants.kServerVideoTimelineIDDoesntExist,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

            # Set favourite video for user
            # Required Params:
            # user_id - string
            # access_token - string
            # video_id - string
            # timeline_id - string
            # fav_date - string

    @app.route('/api/'+app.config["API_VERSION"]+'/video/setfavourite/', methods=["POST"])
    def setFavourite():
        req = flask.request.get_json()['params']
        session = database.DBSession()

        user_id = req['user_id']
        access_token = req['access_token']
        video_id = req['video_id']
        timeline_id = req['timeline_id']
        fav_date = req['fav_date']

        # Check for required params
        if user_id is None or access_token is None or video_id is None or timeline_id is None or fav_date is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        fav_check = session.query(VideoFavourite).filter(VideoFavourite.video_id == video_id).filter(
            VideoFavourite.user == user_id).first()

        if fav_check is not None:
            response = jsonify(message=string_constants.kServerVideoAlreadyFavourited,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        new_fav = VideoFavourite(None, fav_date, user_id, video_id, timeline_id)

        try:
            session.add(new_fav)
            session.commit()
        except exc.SQLAlchemyError:
            session.close()
            response = jsonify(message=string_constants.kServerVideoFavouritingError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        response = jsonify(message=string_constants.kServerVideoFavouritedSuccess,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        session.close()
        return response

        # Removing favourite video for user
        # Required Params:
        # user_id - string
        # access_token - string
        # video_id - string

    @app.route('/api/'+app.config["API_VERSION"]+'/video/unsetfavourite/', methods=["POST"])
    def removeFavourite():
        req = flask.request.get_json()['params']
        session = database.DBSession()

        # Check for required params
        if req['user_id'] is None or req['access_token'] is None or req['video_id'] is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(req['user_id'], req['access_token'], session)
        if allowed is not True:
            session.close()
            return allowed

        fav = session.query(VideoFavourite).filter(VideoFavourite.video_id == req['video_id']).filter(
            VideoFavourite.user == req['user_id']).first()

        if fav is None:
            response = jsonify(message=string_constants.kServerVideoNotFavourited,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        try:
            session.delete(fav)
            session.commit()
        except exc.SQLAlchemyError:
            response = jsonify(message=string_constants.kServerVideoFavouritingError,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        response = jsonify(message=string_constants.kServerFavouriteRemovedSuccess,
                           status=True,
                           HTTP_CODE=200
        )
        response.status_code = 200
        session.close()
        return response

        # Get favourite videos for user
        # Required Params:
        # username - string
        # access_token - string
        # page - int

    @app.route('/api/'+app.config["API_VERSION"]+'/video/favourites/', methods=["GET"])
    def getFavouritesForUserAtPage():
        req = flask.request.args
        session = database.DBSession()

        # Create vars for req object params
        user_id = req['user_id']
        access_token = req['access_token']
        page = int(float(req['page'])) + 1

        # Check for required params
        if user_id is None or access_token is None or page is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        page_limit = 10

        from user import Connection

        # Get Videos that are favourited for a user
        favourites_all = session.query(VideoFavourite).filter(VideoFavourite.user == user_id).join(VideoFavourite.video).filter(VideoModel.public == 1 or VideoModel.public == True).limit(page_limit).offset((page - 1) * page_limit)
        favourites_public = session.query(VideoFavourite).filter(VideoFavourite.user == user_id).join(VideoFavourite.timeline).join(Timeline.connection).filter(Connection.approved == 1).filter(Connection.disabled == 0).limit(page_limit).offset((page - 1) * page_limit)
        favourites = favourites_all.union(favourites_public).order_by(
            desc(VideoFavourite.fav_date)).all()
        videoCount = len(favourites)
        if len(favourites) > 0:

            vids = Video.videoObjectsFromPlaylistArrayForPage(favourites, True)
            if videoCount < 1:
                videoCount = 1
            pageCount = ++ceil(videoCount / 10)

            videos = []

            if vids['videos'] is not None:
                videos = vids['videos']

            response = jsonify(message=string_constants.kServerVideoVideosForPage,
                               status=True,
                               HTTP_CODE=200,
                               videos=videos,
                               total_pages=int(pageCount),
                               video_count=int(videoCount)
            )
            response.status_code = 200
            session.close()
            return response
        elif favourites is not None and len(favourites) <= 0:

            response = jsonify(message=string_constants.kServerVideoVideosForPage,
                               status=True,
                               HTTP_CODE=200,
                               videos=[],
                               total_pages=0,
                               video_count=0
            )
            response.status_code = 200
            session.close()
            return response
        else:
            response = jsonify(message=string_constants.kServerVideoUserHasNoFavourites,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response

        # Get timelines for connection
        # Required Params:
        # user_id - string
        # connection_id - string
        # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/video/timelines/', methods=["GET"])
    def getTimelinesForConnection():
        req = flask.request.args
        session = database.DBSession()

        # Create vars for req object params
        user_id = req['user_id']
        access_token = req['access_token']
        connection_id = req['connection_id']

        # Check for required params
        if user_id is None or access_token is None or connection_id is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        timelines = session.query(Timeline).filter(Timeline.connection_id == connection_id).all()

        response = jsonify(message=string_constants.kServerVideoTimelineList,
                           status=True,
                           timelines=(timelines is not None and len(timelines) > 0) and Video.sanitizedTimelineObjects(
                               timelines, user_id) or None,
                           HTTP_CODE=200
        )
        response.status_code = 200
        session.close()
        return response

        # Get timelines for user
        # Required Params:
        # user_id - string
        # access_token - string

    @app.route('/api/'+app.config["API_VERSION"]+'/video/getTimelines/', methods=["GET"])
    def getTimelines():

        from user import Connection

        req = flask.request.args
        session = database.DBSession()

        # Create vars for req object params
        user_id = req['user_id']
        access_token = req['access_token']

        # Check for required params
        if user_id is None or access_token is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        try:
            connection_list_query_a = session.query(Connection.connection_id).filter(
                Connection.user1 == user_id).filter(Connection.approved is True or Connection.approved == 1)
            connection_list_query_b = session.query(Connection.connection_id).filter(
                Connection.user2 == user_id).filter(Connection.approved is True or Connection.approved == 1)

            timelines = session.query(Timeline.timeline_id).filter(
                Timeline.connection_id.in_(connection_list_query_a.union(connection_list_query_b))).all()
            timelines_r = []
            for timeline in timelines:
                timelines_r.append(timeline[0])

        except exc.SQLAlchemyError:
            response = jsonify(message=string_constants.kServerVideoTimelineIDsForUserFailure,
                               status=False,
                               HTTP_CODE=200
            )
            response.status_code = 200
            session.close()
            return response
        else:
            response = jsonify(message=string_constants.kServerVideoTimelineIDsForUser,
                               status=True,
                               HTTP_CODE=200,
                               timelines=timelines_r
            )
            response.status_code = 200
            session.close()
            return response

    # Setting video as watched
    # Required Params:
    # user_id - string
    # access_token - string
    # video_id - string

    @app.route('/api/'+app.config["API_VERSION"]+'/video/watched/', methods=["POST"])
    def watchedVideo():
        req = flask.request.get_json()['params']
        user_id = int(req['user_id'])
        access_token = req['access_token']
        video_id = req['video_id']
        session = database.DBSession()

        # Check for required params
        if user_id is None or access_token is None or video_id is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        video = session.query(VideoModel).filter(VideoModel.video_id == video_id).first()

        if video is not None:
            timeline = session.query(Timeline).filter(Timeline.timeline_id == video.timeline_id).first()
            if timeline is not None:
                if timeline.user1 == user_id or timeline.user2 == user_id:
                    if video.user != user_id:
                        try:
                            session.query(VideoModel).filter(VideoModel.video_id == video_id). \
                            update({'watched': True}, synchronize_session='fetch')
                            session.commit()
                        except exc.SQLAlchemyError:
                            response = jsonify(message=string_constants.kServerVideoSetVideoToWatchFailure,
                                               status=False,
                                               HTTP_CODE=200
                            )
                            response.status_code = 200
                            session.close()
                            return response

                        response = jsonify(message=string_constants.kServerVideoSetVideoToWatchSuccess,
                               status=True,
                               HTTP_CODE=200
                        )
                        response.status_code = 200
                        session.close()
                        return response
        response = jsonify(message=string_constants.kServerVideoSetVideoToWatchFailure,
                           status=False,
                           HTTP_CODE=200
                        )
        response.status_code = 200
        session.close()
        return response

    # Removing a video from the public feed
    # Required Params:
    # user_id - string
    # access_token - string
    # video_id - string

    @app.route('/api/'+app.config["API_VERSION"]+'/video/public/remove/', methods=["POST"])
    def makeVideoPrivate():
        req = flask.request.get_json()['params']
        user_id = int(req['user_id'])
        access_token = req['access_token']
        video_id = req['video_id']

        session = database.DBSession()

        # Check for required params
        if user_id is None or access_token is None or video_id is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        video = session.query(VideoModel).filter(bool(VideoModel.public) is True).filter(VideoModel.user == user_id).filter(VideoModel.video_id == video_id).first()
        if video is not None:
            try:
                video.public = False
                session.commit()
            except exc.SQLAlchemyError as e:
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response
            response = jsonify( message=string_constants.kServerVideoPrivateSuccessfully,
                                status=True,
                                HTTP_CODE=200
                )
            response.status_code = 200
            session.close()
            return response
        else:
            response = jsonify( message=string_constants.kServerVideoPrivateFailed,
                                status=False,
                                HTTP_CODE=200
                )
            response.status_code = 200
            session.close()
            return response

    # Deleting a video
    # Required Params:
    # user_id - string
    # access_token - string
    # video_id - string
    # video_path - string

    @app.route('/api/'+app.config["API_VERSION"]+'/video/delete/', methods=["POST"])
    def deleteVideo():
        req = flask.request.get_json()['params']
        user_id = int(req['user_id'])
        access_token = req['access_token']
        video_id = req['video_id']
        video_path = req['video_path']

        session = database.DBSession()

        # Check for required params
        if user_id is None or access_token is None or video_id is None or video_path is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        # Check if the video exists
        video = session.query(VideoModel).filter(VideoModel.video_id == video_id).first()
        if video is None:
            response = jsonify(message=string_constants.kServerVideoDoesntExistError,
                               status=False,
                               HTTP_CODE=200
                        )
            response.status_code = 200
            session.close()
            return response
        else:
            import process_flagged_content
            try:
                deleteVideo = process_flagged_content.process(string_constants.AWS_ACCESS_KEY_ID, string_constants.AWS_SECRET_KEY, string_constants.AWS_BUCKET_NAME, video_path, video)
                if deleteVideo is True and deleteVideo is not None:
                    session.delete(video)
                    session.commit()
            except:
                logging.exception('')
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response

        response = jsonify(message=string_constants.kServerVideoDeletedSuccessfully,
                           status=True,
                           HTTP_CODE=200
                        )
        response.status_code = 200
        session.close()
        return response


    # Setting video as flagged for being offensive
    # Required Params:
    # user_id - string
    # access_token - string
    # video_id - string
    # video_path - string
    # flagged - bool

    @app.route('/api/'+app.config["API_VERSION"]+'/video/flagged/', methods=["POST"])
    def flagVideo():
        req = flask.request.get_json()['params']
        user_id = int(req['user_id'])
        access_token = req['access_token']
        video_id = req['video_id']
        video_path = req['video_path']
        flagged = bool(req['flagged'])

        session = database.DBSession()

        # Check for required params
        if user_id is None or access_token is None or video_id is None:
            session.close()
            return authorized.wrongParams()

        # Check if the user is allowed to access this method
        allowed = authorized.authorized(user_id, access_token, session)
        if allowed is not True:
            session.close()
            return allowed

        # Check if the video is already flagged
        flagged_video = session.query(FlaggedVideoModel).filter(FlaggedVideoModel.video_id == video_id).first()
        if flagged_video is not None and flagged is True:
            response = jsonify(message=string_constants.kServerVideoAlreadyFlagged,
                               status=True,
                               HTTP_CODE=200
                        )
            response.status_code = 200
            session.close()
            return response
        elif flagged_video is not None and flagged is False:

            try:
                session.delete(flagged_video)
                session.commit()
            except exc.SQLAlchemyError:
                logging.exception('')
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response

            response = jsonify(message=string_constants.kServerVideoUnFlaggedSuccessfully,
                               status=True,
                               HTTP_CODE=200
                            )
            response.status_code = 200
            session.close()
            return response
        else:
            flagged_video = FlaggedVideoModel(video_id, video_path, calendar.timegm(datetime.utcnow().timetuple()) + app.config["FLAGGED_CONTENT_TIME_BUFFER"])

            try:
                session.add(flagged_video)
                session.commit()
            except exc.SQLAlchemyError:
                logging.exception('')
                response = jsonify(message=string_constants.kServerGeneric500Error,
                                   status=False,
                                   HTTP_CODE=500
                )
                response.status_code = 500
                session.close()
                return response

            response = jsonify(message=string_constants.kServerVideoFlaggedSuccessfully,
                               status=True,
                               HTTP_CODE=200
                            )
            response.status_code = 200
            session.close()
            return response




    @classmethod
    def sanitizedTimelineObjects(cls, timelines, user_id):

        import user
        timelines_r = []

        for timeline in timelines:

            friend_id = timeline.connection.user1
            if timeline.connection.user2 != user_id:
                friend_id = timeline.connection.user2

            timelines_r.append({
                'timeline_id': timeline.timeline_id,
                'title': timeline.title,
                'description': timeline.description,
                'coverImage': user.User.getProfileImage(friend_id),
                'start_date': timeline.start_date,
                'video_count': timeline.video_count
            })
        return timelines_r

    @classmethod
    def videoObjectsFromPlaylistArrayForPage(cls, playlist, forFav=False, withFavList=None, withFlagList=None):
        import user
        # Get the video_objs for the range of the page
        video_objs = playlist
        # Gather the video objects for the page from the playlist
        videos = []
        for v in video_objs:
            if forFav is True:
                video = v.video
            else:
                video = v

            video_favourited = forFav
            video_flagged = False
            if withFavList is not None:
                video_favourited = video.video_id in withFavList and True or False
            if withFlagList is not None:
                video_flagged = video.video_id in withFlagList and True or False

            video_object = {
                'date': video.date,
                'thumbnail_path': Video.getVideoObjectPath(video.thumbnail, str(video.user), video.timeline_id, video.date),
                'video_id': video.video_id,
                'video_path': Video.getVideoObjectPath(video.video_id, str(video.user), video.timeline_id, video.date) + '.m4v',
                'timeline_id': video.timeline_id,
                'user': video.user_model.display_name,
                'user_thumbnail': user.User.getProfileImage(video.user),
                'description': video.description,
                'favourited': video_favourited,
                'flagged': video_flagged,
                'publicVideo': video.public
            }

            if forFav is True:
                video_object.update({'fav_date': v.fav_date})

            videos.append(video_object)

        return {'videos': videos}

        # Get video object path
        # Required Params:
        # video_id - string
        # username - string
        # relationship_id - string
        # date - string

    @classmethod
    def getVideoObjectPath(cls, v_id, user_id, timeline_id, date):
        path = app.config["RESPONSE_STATICS_FOLDER"] + '/videos/' + timeline_id + '/' + user_id + '/' + str(date) + '/' + v_id
        return path

    @classmethod
    def getVideoThumbnailObjectPath(cls, v_id, user_id, timeline_id, date):
        path = app.config["RESPONSE_STATICS_FOLDER"] + '/videos/' + timeline_id + '/' + user_id + '/' + str(date) + '/' + v_id + '_thumb'
        return path

    @classmethod
    def getTimelineCoverImageObjectPath(cls, timeline_id, coverImageName):
        return app.config["RESPONSE_STATICS_FOLDER"] + '/videos/' + timeline_id + '/' + coverImageName

    @classmethod
    def getTimelineFolder(cls, timeline_id):
        return app.config["STATIC_FILES_FOLDER"] + "/videos/%s/" % timeline_id

    @classmethod
    def getVideoPath(cls):
        return app.config["STATIC_FILES_FOLDER"] + "/videos/%s/%s/%s/"

    # Create a timeline
    # Required Params:
    # user_id - string
    # connection_id - string
    # access_token - string

    @classmethod
    def createTimeline(cls, session, user_id, connection_id):

        timeline = session.query(Timeline).filter(Timeline.connection_id == connection_id).first()

        if timeline is not None:
            return timeline.timeline_id
        else:
            timeline_id = (hashlib.sha256(str(user_id) + str(connection_id) + str(random.seed())).hexdigest())
            timeline = Timeline(timeline_id, connection_id)

            try:
                session.add(timeline)
                session.commit()
            except exc.SQLAlchemyError as e:
                return None

            return timeline_id
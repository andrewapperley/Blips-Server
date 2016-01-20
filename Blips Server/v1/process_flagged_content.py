__author__ = 'andrewapperley'

import database
from sqlalchemy import exc
from video import FlaggedVideoModel, VideoFavourite
import sys
from boto.s3.connection import S3Connection, Bucket, Key
from datetime import datetime
import calendar


def process(access_key=None, secret_key=None, bucket_name=None, video_path=None, video=None):

    for_deleting = False

    if len(sys.argv) > 1:
        a = sys.argv[1]
        ACCESS_KEY = sys.argv[2]
        SECRET_KEY = sys.argv[3]
        BUCKET_NAME = sys.argv[4]
        database.createDatabase(a)
    else:
        for_deleting = True
        ACCESS_KEY = access_key
        SECRET_KEY = secret_key
        BUCKET_NAME = bucket_name
        database.createDatabase()

    aws_s3_connection = S3Connection(ACCESS_KEY, SECRET_KEY)
    aws_s3_bucket = Bucket(aws_s3_connection, BUCKET_NAME)

    session = database.DBSession()

    object_keys = []

    # This is if the CRON job is running and is removing flagged videos
    if for_deleting is False:
        flagged_content = session.query(FlaggedVideoModel).all()
        if len(flagged_content) > 0:
            time_stamp_now = calendar.timegm(datetime.utcnow().timetuple())
            for content in flagged_content:
                if content.timeStamp <= time_stamp_now:
                    video = content.video
                    favourites_of_video = session.query(VideoFavourite).filter(VideoFavourite.video_id == video.video_id).all()
                    for key in aws_s3_bucket.list(prefix=content.video_path):
                        object_keys.append(key)

                    if len(favourites_of_video) > 0:
                        for fv in favourites_of_video:
                            session.delete(fv)
                    session.delete(content)
                    session.delete(video)
    # This is for when you are deleting a video from the timeline
    elif for_deleting is True and video is not None and video_path is not '' and video_path is not None:
        favourites_of_video = session.query(VideoFavourite).filter(VideoFavourite.video_id == video.video_id).all()
        flags_for_video = session.query(FlaggedVideoModel).filter(FlaggedVideoModel.video_id == video.video_id).all()

        # Collect the AWS S3 objects to delete
        for key in aws_s3_bucket.list(prefix=video_path):
            object_keys.append(key)
        # Collect the Video Favourites
        if len(favourites_of_video) > 0:
            for fv in favourites_of_video:
                session.delete(fv)
        # Collect the Video Flags
        if len(flags_for_video) > 0:
            for fv in flags_for_video:
                session.delete(fv)

    try:
        if len(object_keys) > 0:
            aws_s3_bucket.delete_keys(object_keys)
        session.commit()
        session.close()
        return True
    except exc.SQLAlchemyError:
        session.close()
        return False


if len(sys.argv) > 1:
    process()
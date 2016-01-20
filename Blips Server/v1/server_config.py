import os


class Config(object):
    DEBUG = False
    DATABASE_URI = 'mysql+pymysql://root:root@localhost:8889/blips?charset=utf8&use_unicode=0'
    CACHE_CONTROL = 300
    COLUMN_MAX_LENGTH = 255
    API_ADDRESS = 'http://localhost:5000'
    SERVER_ADDRESS = 'http://localhost'
    RESPONSE_STATICS_FOLDER = "user_content"
    STATIC_FILES_FOLDER = "user_content"
    COMPRESS_MIN_SIZE = 0
    API_VERSION = "v1"
    SHARED_PHRASE = "&^uZ7S?56BaRP73hq7*#568gGG#xZau$MFrnM6Wm6rt+zM&GWq29aV!ScrBL2ba#2npc!N6V^qUHDjx!"
    FLAGGED_CONTENT_TIME_BUFFER = 43200  # 12 Hours
    AWS_ACCESS_KEY = "AKIAIFKCGDPZFYJCDWXQ"
    AWS_SECRET_KEY = "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"
    AWS_BUCKET_NAME = "elasticbeanstalk-us-east-1-799484155427"
    AWS_KEY_CONTENT_TYPE = 'binary/octet-stream'


class DevelopmentConfig(Config):
    DEBUG = True
    COMPRESS_DEBUG = True
    AWS_S3 = False


class Development_Staging_Config(DevelopmentConfig):
    DATABASE_URI = 'mysql+pymysql://root:Seph9kewn7@localhost/blips?charset=utf8&use_unicode=0'


class Development_Local_Config(DevelopmentConfig):
    DATABASE_URI = 'mysql+pymysql://root:root@localhost/blips?charset=utf8&use_unicode=0'


class ProductionConfig(Config):
    AWS_S3 = True
    if "RDS_USERNAME" in os.environ and "RDS_PASSWORD" in os.environ and "RDS_HOSTNAME" in os.environ and "RDS_DB_NAME" in os.environ:
        DATABASE_URI = 'mysql+pymysql://' + os.environ["RDS_USERNAME"] + ':' + os.environ["RDS_PASSWORD"] + '@' + \
                       os.environ["RDS_HOSTNAME"] + '/' + os.environ["RDS_DB_NAME"]+"?charset=utf8&use_unicode=0"

    API_ADDRESS = 'http://blips-server-env-hicpnnbs3v.elasticbeanstalk.com'
    if "AWS_ACCESS_KEY_ID" in os.environ and "AWS_SECRET_KEY" in os.environ and "AWS_BUCKET_NAME" in os.environ:
        AWS_ACCESS_KEY = os.environ['AWS_ACCESS_KEY_ID']
        AWS_SECRET_KEY = os.environ['AWS_SECRET_KEY']
        AWS_BUCKET_NAME = os.environ['AWS_BUCKET_NAME']
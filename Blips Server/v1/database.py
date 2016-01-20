from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import *

from app import app


Base = declarative_base()


def createDatabase(environment=None, debug=None):
    if environment is None:
        environment = app.config["DATABASE_URI"]
    if debug is None:
        debug = app.config["DEBUG"]
    # CreateDatabase
    global db
    db = create_engine(environment, echo=bool(debug), pool_size=20, max_overflow=0, pool_recycle=499, pool_timeout=20)
    global DBSession
    DBSession = sessionmaker(bind=db)
    Base.metadata.create_all(db)
__author__ = 'andrewapperley'

import database
import string_constants
from video import Timeline


def setup_app():
    database.createDatabase(environment="MYSQLURL")
    session = database.DBSession()

    # Create Public Timeline if doesn't exist

setup_app()

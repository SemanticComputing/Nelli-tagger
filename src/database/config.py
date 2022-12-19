import os

basedir = os.path.abspath(os.path.dirname(__file__))
type = "sqlite"
name = "feedback.db"

class Config(object):
    # default setup
    basedir = os.path.abspath(os.path.dirname(__file__))
    type = "sqlite"
    name = "feedback.db"

    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        str(type)+':///' + os.path.join(basedir, name)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProdConfig(Config):
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              str(type) + ':///' + os.path.join(basedir, name)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    print("Saving db to:", basedir)

class DevConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              str(type) + ':///' + os.path.join(basedir, name)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    print("Saving db to:", basedir)

class TestConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              str(type) + ':///' + os.path.join(basedir, name)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    print("Saving db to:", basedir)

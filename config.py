import os
from dotenv import load_dotenv

load_dotenv(os.environ.get('env_file'))

basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    FLASK_APP = os.environ.get('FLASK_APP')
    FLASK_DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY')


class DevelopmentConfig(Config):
    FLASK_DEBUG = True
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')


config = {
    'development': DevelopmentConfig
}

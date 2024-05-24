import os
import logging
from flask import Flask
from config import config
from flask_mail import Mail
from dotenv import load_dotenv

load_dotenv(os.environ.get('env_file'))

# flask extensions
mail = Mail()


def create_app(config_name, **kwargs):
    logging.basicConfig(
        format=f'%(asctime)s %(levelname)s %('f'name)s %(threadName)s : %(message)s' # noqa
    )
    formatter = logging.Formatter(f'%(asctime)s %(levelname)s %('f'name)s %(threadName)s : %(message)s') # noqa
    file_logging = logging.FileHandler('error_record.log')
    file_logging.setLevel(logging.WARNING)
    file_logging.setFormatter(formatter)
    logging.getLogger().addHandler(file_logging)
    app = Flask(
        __name__
    )
    app.config.from_object(config[config_name])

    # Initializing flask extensions
    mail.init_app(app)

    # Registering Blueprints
    from core.auth_app import bp as a_bp

    app.register_blueprint(a_bp)

    return app

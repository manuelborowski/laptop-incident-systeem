DB_TOOLS = False


class Config(object):
    STATIC_PATH = "app/static"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LOG_LEVEL = "INFO"
    PRESERVE_CONTEXT_ON_EXCEPTION = True
    SOCKETIO_ASYNC_MODE = 'gevent'

class DevelopmentConfig(Config):
    SQLALCHEMY_ECHO = False
    # Native threads avoid monkey-patching threads created by the debugger.
    SOCKETIO_ASYNC_MODE = 'threading'


class ProductionConfig(Config):
    DEBUG = False


app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
    }

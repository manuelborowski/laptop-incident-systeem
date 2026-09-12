import logging.handlers, os, sys
from flask import Flask, abort, send_from_directory
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask_jsglue import JSGlue
from flask_migrate import Migrate
from flask_apscheduler import APScheduler
from werkzeug.routing import IntegerConverter
from functools import wraps

#Warning: update flask_jsglue.py: from markupsafe import Markup

# DONE: filter: voeg locatie filter toe
# DONE: paswoord veld met oogje
# DONE: maximum tijdsuur per toestand
# DONE: historiek: nieuwste bovenaan
# DONE: incident-types toevoegen: "laptop vergeten", "nieuwe leerling, nog geen laptop"
# DONE: link toevoegen naar m4s
# DONE: GSM gebruiken voor ingeven nieuwe incident of updaten bestaande
# DONE: laders ook een badge geven? -> nee
# DONE: bericht opnieuw verzenden, eventueel naar co-accounts
# DONE: bericht verzenden, voorzie mogelijkheid om tekst uit te breiden
# DONE: retour laptops: nieuwe statussen ("wacht op laptop", "wacht op signpost", retour afgehandeld")
# DONE: retour, onderscheid tussen laptops van de school (geen signpost) en signpost
# DONE: hoes -> ook inbrengen in m4s
# DONE: locaties -> signpost = hardware incident?
# DONE: lader lenen
# DONE: tijdelijk laptop lenen of nieuw in school en laptop lenen
# DONE: tijdelijke laptop: in voorbereiding, uitgeleend, gesloten

version = "0.141"

app = Flask(__name__, instance_relative_config=True, template_folder='presentation/template/')

#  enable logging
top_log_handle = "LIS"
log = logging.getLogger(f"{top_log_handle}.{__name__}")
# support custom filtering while logging
class MyLogFilter(logging.Filter):
    def filter(self, record):
        record.username = current_user.username if current_user and current_user.is_active else 'NONE'
        return True

log.addFilter(MyLogFilter())
LOG_FILENAME = os.path.join(sys.path[0], f'log/lis.txt')
log_level = getattr(logging, 'INFO')
log.setLevel(log_level)
log_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=1024 * 1024, backupCount=20)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(username)s - %(message)s')
log_handler.setFormatter(log_formatter)
log.addHandler(log_handler)

email_log_handler = None
def subscribe_email_log_handler_cb(cb):
    global email_log_handler
    email_log_handler = cb


# if the log-error-message is FLUSH-TO-EMAIL, all error logs are emailed and the buffer is cleared.
class MyBufferingHandler(logging.handlers.BufferingHandler):
    def flush(self):
        if len(self.buffer) > 1:
            message_body = ""
            for b in self.buffer:
                message_body += self.format(b) + "<br>"
            with app.app_context():
                if email_log_handler:
                    email_log_handler(message_body)
        self.buffer = []

    def shouldFlush(self, record):
        return record.msg == "FLUSH-TO-EMAIL"


buf_handler = MyBufferingHandler(2)
buf_handler.setLevel("ERROR")
log.addHandler(buf_handler)
buf_handler.setFormatter(log_formatter)


log.info("START Laptop Incident Systeem")

from app.config import app_config
config_name = os.getenv('FLASK_CONFIG')
config_name = config_name if config_name else 'production'
app.config.from_object(app_config[config_name])
app.config.from_pyfile('config.py')

jsglue = JSGlue(app)
db = SQLAlchemy()
login_manager = LoginManager()
db.app = app  #  hack:-(
db.init_app(app)
migrate = Migrate(app, db)

app.url_map.converters['int'] = IntegerConverter
login_manager.init_app(app)
login_manager.login_message = 'Je moet aangemeld zijn om deze pagina te zien!'
login_manager.login_view = 'auth.login'

socketio = SocketIO(app, async_mode=app.config['SOCKETIO_ASYNC_MODE'], cors_allowed_origins="*")


def default_db_entries():
    with app.app_context():
        try:
            from app.data.user import User
            from app import data as dl
            # create admin account if not present
            find_admin = User.query.filter(User.username == 'admin').first()
            if not find_admin:
                admin = User(username='admin', password='admin', level=5, user_type=User.USER_TYPE.LOCAL)
                db.session.add(admin)
                db.session.commit()
            # create api account if not present.  All access via the API is on account of this user.
            find_api = User.query.filter(User.username == 'api').first()
            if not find_api:
                api = User(username='api', password=app.config["USER_API_PASSWORD"], level=1, user_type=User.USER_TYPE.LOCAL)
                db.session.add(api)
                db.session.commit()
            # create api default location if not present
            found , _ = dl.settings.get_setting("default-location", "api")
            if not found:
                dl.settings.add_setting("default-location", app.config["USER_API_DEFAULT_LOCATION"], user="api")

        except Exception as e:
            db.session.rollback()
            log.error(f'{sys._getframe().f_code.co_name}: {e}')

default_db_entries()

SCHEDULER_API_ENABLED = True
ap_scheduler = APScheduler()
ap_scheduler.init_app(app)
ap_scheduler.start()

# decorator to grant access to admins only
def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_at_least_admin:
            abort(403)
        return func(*args, **kwargs)
    return decorated_view


# decorator to grant access to at least supervisors
def supervisor_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_at_least_supervisor:
            abort(403)
        return func(*args, **kwargs)
    return decorated_view


# Should be last to avoid circular import
from app.presentation.view import auth, api, user, settings, incident, spare, lisbadge, history, student, staff
app.register_blueprint(auth.bp_auth)
app.register_blueprint(api.bp_api)
app.register_blueprint(user.bp_user)
app.register_blueprint(settings.bp_settings)
app.register_blueprint(incident.bp_incident)
app.register_blueprint(spare.bp_spare)
app.register_blueprint(lisbadge.bp_lisbadge)
app.register_blueprint(history.bp_history)
app.register_blueprint(student.bp_student)
app.register_blueprint(staff.bp_staff)

# see https://search.google.com/search-console/welcome
@app.route(f"/{app.config["GOOGLE_SITE_VERIFICATION"]}")
def google_site_verification():
    return send_from_directory(app.static_folder, app.config["GOOGLE_SITE_VERIFICATION"])
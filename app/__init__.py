import logging.handlers, os, sys
from flask import Flask, abort
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

# 0.1 first backup, user-view is ok
# 0.2: messages have status [ok, warning, error].  Reworked user add/update/delete
# 0.3: clean up.  Datatables to 2.1.8.  Replaced most document.ready in js to fix the order of invocation.  Updated cell_edit
# 0.4: minor updates
# 0.5: reworked column visibility
# 0.6: columns visibility, in rowCallback(), cells refer to the columns that are visible, so a mapping from real to visible colums must be made.
# 0.7: fixed issue with column-visibility and local-store of datatable settings.
# 0.8: ellipsis and variable column width
# 0.9: cleanup.  fixed cell- and row-backgroundcolor
# 0.10: bugfixed cell_edit.  Introduced incident.
# 0.11: moved filter and column menu into navbar
# 0.12: added students-table and sync from SDH.  When client fetches, return inband message.  Added cron.  Formio-templates/defaults are fetched iso hard-inserted in HTML.
# Updated incidents.  Placed filters and column-visibility into navbar.  Added buttons in navbar.
# 0.13: added fetch to entra to get laptopinfo.  Incident, added code to get the laptops of a selected student.
# 0.14: added tables for staff and spares.  Added popups to add a single spare or a list.
# 0.15: added lis-badge.  Various large updates
# 0.16: small bugfix in incident.  Updated CSS
# 0.17: added history.  Added helper functions for forms.  Added datatable cell renderer for labels.  Incident form reused for incident update/state change.
# Added event buttons/select to table.  Added template-post-processing to e.g. replace a value with a label.
# 0.18: added history overview page.  Bugfix select2, make sure it is done initializing before changing its value.
# 0.19: on incident overview page, added a context-menu and popup to display history
# 0.20: reworked fetch-get to use the api filters/fields.  Put the endpoints in the correct files. Use try/except and logging as much as possible to propagate errors.
# Data/defaults/configuration/... is fetched from the server when required.
# 0.21: log in via smartschool
# 0.22: send email when location changed.  Add arguments to incident.show url.
# 0.23: pywin only on windows
# 0.24: added smartschool-send-message
# 0.25: updated smartschool.  Added incident-update form
# 0.26: generate incidents for test purposes
# 0.27: small bugfix
# 0.28: incident-generate, avoid endless loop in case no default-location
# 0.29: replaced, in table, select with button.  Select is now in update-form.  Unified labels/options/defaults.  State-change-buttons, moved from server to client
# 0.30: added filter to hide closed incidents
# 0.31: added cell coloring, based on value.
# 0.32: datatables ellipsis, changed because it took too much processingtime
# 0.33: added qr-code to scan de laptop label
# 0.34 replace the action buttons (to change state) to generic buttons to update the incident and view the incident
# 0.35: update incident, select location and/or new state, make sure that the selections are coherent.
# 0.36: default password, inform user that password is being reset.  Added functionality to set password vi ADproxy
# 0.37: added "condition" label to datatables column.  Added state "message" to explicitly send a message.
# 0.38: from state repaired, it is possible to transit to state transition
# 0.39: add button to close incident
# 0.40: add button to filters to scan lis badge
# 0.41: added m4s.  Updated various items
# 0.42: multiple times a message can be sent.  It is possible to add an extra comment to the message.
# 0.43: implement state-timout, if timeout detected, inform location responsibles.  SS message, sender is incident owner.
# 0.44: reworked sending of ss-messages.  Use the quill RT editor.  Removed message state
# 0.45: general bugfixes.  Extended buttonmenu.  Add button to set defaults. Added category and reworked states/locations/types
# 0.46: message: before updating incident, remove HTML formatting.  Clear password field
# 0.47: clean up of password-field-mess
# 0.48: reworked laptop_type, i.e. students and staff are in 1 select, spare laptop is checkbox.
# 0.49: added m4s api.  Use problemtypes defined by m4s.  General bugfixes
# 0.50: category hw, added link to defect in m4s
# 0.51: datatable, solved conflict between initialization and columns-visibility.  Bootbox, made confirm synchronous to avoid premature closing.
#  Started with combining hardware and software category into repair
# 0.52: added funcionality to switch from hardware to software incident type
# 0.53: small updates and bugfixes
# 0.54: improved new-incident-form ico spare laptop.  Reshuffled the layout of the forms a bit.  Added timeout for incident-types.
# 0.55: bugfixed adding spare laptop badges and incident badges
# 0.56: spare loan, added state "in preparation"
# 0.57: esthetic updates.  Added installation of new laptop
# 0.58: added incident-type filter
# 0.59: small bugfix
# 0.60: remove keys from client
# 0.61: incident-type is hardware, make location change more generic
# 0.62: first version of return-api
# 0.63: implemented laptop return, use thefuzz to match a given name with a name in the database
# 0.63-mobile-0.1: implement a seperate page for mobile login.  Create user specific urls to avoid logging in
# 0.63-mobile-0.2: continue with mobile page, view and update repair incident.  Update incident-generate.
# 0.63-mobile-0.3: small updates
# 0.63-mobile-0.4: update repair form so that only one is required for new repairs and repairs to update
# 0.63-mobile-0.5: incident.js, extracted functionality into a class.
# 0.63-mobile-0.6: mobile and laptop view, shared code and form.  Small updates
# 0.64: merge from 0.63-mobile-0.6
# 0.65: regular users have less rights, cannot create or update incidents
# 0.66: small bugfixes.  lis-badge-id cannot be reused until incident is closed
# 0.67: minor layout updates
# 0.68: minor layout updates.  Implemented QR code scanner (mobile).
# 0.69: added minimalistic help
# 0.70: small updates
# 0.71: small bugfix when entering an owners' password
# 0.72: small bugfixes.  Reworked cell_edit, works for select only.  Added homelocation to spares.
# 0.73: cell_edit works for regular input.  LIS-badge is also available when state is repaired
# 0.74: upload, view and delete attachments
# 0.75: busy-indication activated
# 0.76: bugfix busy-indication activated
# 0.77: bugfix busy-indication activated
# 0.77-home_current-0.1: introduction of home/current location/owner.  API calls are on behalve of default api user.
# Reworked meta to supply keyed-options, i.e. in function of incident-state and category.  Added "display" tag to columns-data to apply multiple, combined renderings on datatable data.
# 0.78: merge from 0.77-home_current-0.1
# 0.79: datatable, column-rendering, added "less", updated "display".
# 0.80: added user pin and rfid so that users can login with a badge or pin code.
# 0.81: new incident, owner field is default empty.
# 0.82: new incident, M4S category field is default empty.
# 0.83: update software incident, make sure M4S fields are not visible
# 0.84: token-login, disable browser autocomplete
# 0.85: bugfix cron, access to request outside app_context.  Changed info-field to unicidetext for long string.
# 0.86: nieuw iso new
# 0.87: made it possible to type the label of the laptop
# 0.88: type label and serial of a laptop.  Updated m4s data.
# 0.89: implemented FLUSH-TO-EMAIL
# 0.90: small bugfixes
# 0.91: add spare history.  Add spare-laptop to incident history
# 0.92: update info in "update-lis" email
# 0.93: bugfix, when type changes from SW to HW, was not properly inserted into M4S
# 0.94: improved adding case in m4s.  Bugfixed manually inputting laptopname and serial number
# 0.95: logging, minor bugfix. incident-repair, make it possible to switch type from sw to hw and back.
# 0.96: small bugfix when closing incident.  Added info field for spare laptops.
# 0.97: rename incident to reparatie
# 0.98: rename incident to herstelling
# 0.99: remove filter-button-scan-badge
# 0.100: small update
# 0.101: update navigation menu to include hard urls
# 0.102: update states, depending on type
# 0.103: small bugfix with regard to new state
# 0.104: updated m4s reference, use template to insert url.  Updated filter-fields.
# 0.105: small bugfix
# 0.106: search in M4S column.  Add "login" column
# 0.107: small bugfix and added state "installed"
# 0.108: small bugfix
# 0.109: new repair, location is saved to current and home location
# 0.110: history form, add M4S reference, if applicable.
# 0.111: update api with respect to laptop-return
# 0.112: spare-laptop-repair, make it possible to add serial number
# 0.113: m4s specific, if a case could not be inserted in m4s, display warning to user and add warning in database.
# 0.114: small update
# 0.115: added state: cancelled
# 0.116: repair of spare laptop -> hw issue -> check if info field is filled in
# 0.117: add checkbox to push attachment to m4s.  At the moment, it is possible to push images only.

version = "0.117"

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

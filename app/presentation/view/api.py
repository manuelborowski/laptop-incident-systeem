from flask import request, Blueprint
from app import log, app, data as dl, application as al
import json, sys, html
from functools import wraps
from flask_login import login_user, logout_user

bp_api = Blueprint('api', __name__)

with app.app_context():
    user_api = dl.user.get(("username", "=", "api"))

def api_core(api_level, func, *args, **kwargs):
    try:
        header_key = request.headers.get('x-api-key')
        key_info = dl.settings.get_configuration_setting('api-keys')[header_key]
        if request.headers.get("X-Forwarded-For"):
            remote_ip = request.headers.get("X-Forwarded-For")
        else:
            remote_ip = request.remote_addr
        if key_info["active"]:
            if key_info["level"] >= api_level:
                log.info(f"API access by '{key_info["label"]}', from {remote_ip}, URI {request.url}")
                try:
                    login_user(user_api)
                    ret = func(*args, **kwargs)
                    logout_user()
                    return ret
                except Exception as e:
                    log.error(f'{func.__name__}: {e}')
                    return json.dumps({"status": False, "data": f'API-EXCEPTION {func.__name__}: {html.escape(str(e))}'})
            log.error(f'{func.__name__}: level of request too low')
        log.error(f'{func.__name__}: key not active')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return json.dumps({"status": False, "data": html.escape(str(e))})
    log.error(f"API, API key not valid, {header_key}, from {remote_ip} , URI {request.url}")
    return json.dumps({"status": False, "data": f'API key not valid'})


def level_1(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return api_core(1, func, *args, **kwargs)
    return wrapper


def level_3(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return api_core(3, func, *args, **kwargs)
    return wrapper


def level_5(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return api_core(5, func, *args, **kwargs)
    return wrapper

@bp_api.route('/api/retour', methods=['POST'])
@level_1
def retour():
    try:
        din = json.loads(request.data)
        log.info(din)
        ret = al.incident.api_add_laptop_return(din)
        return(json.dumps(ret))
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": "Deze velden zijn verplicht: achternaam, voornaam, klas, laptop-label, telefoon, mail, bestemming, balie"}

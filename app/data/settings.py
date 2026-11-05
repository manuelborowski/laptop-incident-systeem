from app import log, db
from app.warranty import (WARRANTY_NONE, WARRANTY_REPAIR_TO_BE_APPROVED, WARRANTY_REPAIR_APPROVED, WARRANTY_INVOICE_APPROVED)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy_serializer import SerializerMixin
import json, yaml, re, sys


class Settings(db.Model, SerializerMixin):
    __tablename__ = 'settings'

    class SETTING_TYPE:
        E_INT = 'INT'
        E_STRING = 'STRING'
        E_FLOAT = 'FLOAT'
        E_BOOL = 'BOOL'
        E_JSON = 'JSON'
        E_YAML = 'YAML'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256))
    value = db.Column(MEDIUMTEXT)
    type = db.Column(db.String(256))
    username = db.Column(db.String(256))


# return: found, value
# found: if True, setting was found else not
# value ; if setting was found, returns the value
def get_setting(name, user=None, convert_to_string=False):
    try:
        setting = Settings.query.filter_by(name=name, username=user).first()
        if setting:
            if setting.type == Settings.SETTING_TYPE.E_INT:
                value = int(setting.value)
            elif setting.type == Settings.SETTING_TYPE.E_FLOAT:
                value = float(setting.value)
            elif setting.type == Settings.SETTING_TYPE.E_BOOL:
                value = True if setting.value == 'True' else False
            elif setting.type == Settings.SETTING_TYPE.E_JSON:
                value = json.dumps(json.loads(setting.value), indent=2) if convert_to_string else json.loads(setting.value)
            elif setting.type == Settings.SETTING_TYPE.E_YAML:
                value = setting.value if convert_to_string else yaml.safe_load(setting.value)
            else:
                value = setting.value
            return True, value
        return False, ""
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return False, ''
    return True, value


def add_setting(name, value, type=Settings.SETTING_TYPE.E_STRING, user=None):
    try:
        if type == Settings.SETTING_TYPE.E_JSON:
            value = json.dumps(value)
        setting = Settings(name=name, value=str(value), type=type, username=user)
        db.session.add(setting)
        db.session.commit()
        log.info(f'add: {setting.to_dict()}')
        return True
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e


def set_setting(name, value, user=None):
    try:
        setting = Settings.query.filter_by(name=name, username=user).first()
        if setting:
            if setting.type == Settings.SETTING_TYPE.E_BOOL:
                value = 'True' if value else 'False'
            elif setting.type == Settings.SETTING_TYPE.E_JSON:
                if type(value) is dict:
                    value = json.dumps(value)
                else:
                    value = json.dumps(json.loads(value))
            setting.value = value
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return False
    return True


default_configuration_settings = {
    'generic-new-via-smartschool-default-level': (1, Settings.SETTING_TYPE.E_INT),
    'generic-new-via-smartschool': (True, Settings.SETTING_TYPE.E_BOOL),
    'generic-ss-send-to': ('', Settings.SETTING_TYPE.E_STRING),

    'user-datatables-template': ({}, Settings.SETTING_TYPE.E_YAML),
    'incident-datatables-template': ({}, Settings.SETTING_TYPE.E_YAML),
    'incident-warranty-datatables-template': ([
        {'data': 'm4s_reference', 'name': 'M4S'},
        {'data': 'warranty_state', 'name': 'Garantie'},
        {'data': 'time', 'name': 'Tijd'},
        {'data': 'incident_state', 'name': 'Status'},
        {'data': 'home_location', 'name': 'Thuis'},
        {'data': 'm4s_problem_type_guid', 'name': 'M4S-type'},
        {'data': 'laptop_owner_name', 'name': 'Eigenaar'},
        {'data': 'info', 'name': 'Info'},
    ], Settings.SETTING_TYPE.E_YAML),
    'incidentm-datatables-template': ({}, Settings.SETTING_TYPE.E_YAML),
    'incident-history-datatables-template': ({}, Settings.SETTING_TYPE.E_YAML),
    'spare-datatables-template': ({}, Settings.SETTING_TYPE.E_YAML),
    'lis-badge-datatables-template': ({}, Settings.SETTING_TYPE.E_YAML),

    'ss-student-message-template': ('', Settings.SETTING_TYPE.E_STRING),
    'ss-coaccount-message-template': ('', Settings.SETTING_TYPE.E_STRING),
    WARRANTY_REPAIR_TO_BE_APPROVED: ('<p>Beste %%VOORNAAM%%,</p><p>De herstelling van uw laptop wacht op goedkeuring.</p><p>%%SIGNATURE%%</p>', Settings.SETTING_TYPE.E_STRING),
    WARRANTY_REPAIR_APPROVED: ('<p>Beste %%VOORNAAM%%,</p><p>De herstelling van uw laptop is goedgekeurd.</p><p>%%SIGNATURE%%</p>', Settings.SETTING_TYPE.E_STRING),
    WARRANTY_INVOICE_APPROVED: ('<p>Beste %%VOORNAAM%%,</p><p>De Signpost-factuur voor de herstelling van uw laptop is goedgekeurd.</p><p>%%SIGNATURE%%</p>', Settings.SETTING_TYPE.E_STRING),
    f'{WARRANTY_INVOICE_APPROVED}_subject': ('Signpost factuur goedgekeurd', Settings.SETTING_TYPE.E_STRING),
    f'{WARRANTY_REPAIR_TO_BE_APPROVED}_recipients': ([], Settings.SETTING_TYPE.E_YAML),
    f'{WARRANTY_REPAIR_APPROVED}_recipients': ([], Settings.SETTING_TYPE.E_YAML),
    f'{WARRANTY_INVOICE_APPROVED}_recipients': ([], Settings.SETTING_TYPE.E_YAML),

    'cron-scheduler-template': ('', Settings.SETTING_TYPE.E_STRING),
    'cron-enable-modules': ({}, Settings.SETTING_TYPE.E_JSON),

    'api-keys': ([], Settings.SETTING_TYPE.E_YAML),

    'popup-new-update-user': ({}, Settings.SETTING_TYPE.E_JSON),
    'popup-new-update-incident': ({}, Settings.SETTING_TYPE.E_JSON),

    'lis-badge-rfid': ({}, Settings.SETTING_TYPE.E_JSON),
    'lis-locations': ({}, Settings.SETTING_TYPE.E_YAML),
    'lis-state': ({
        WARRANTY_NONE: {'label': 'NVT', 'color': 'orange'},
        WARRANTY_REPAIR_TO_BE_APPROVED: {'label': 'Wacht op goedkeuring om te herstellen', 'color': 'orange'},
        WARRANTY_REPAIR_APPROVED: {'label': 'Herstelling goedgekeurd', 'color': 'orange'},
        WARRANTY_INVOICE_APPROVED: {'label': 'Signpost factuur goedgekeurd', 'color': 'orange'},
    }, Settings.SETTING_TYPE.E_YAML),
    'lis-incident-types': ({}, Settings.SETTING_TYPE.E_YAML),
    'lis-categories': ({}, Settings.SETTING_TYPE.E_YAML),
    'lis-home-locations': ({}, Settings.SETTING_TYPE.E_YAML),

    'logging-inform-emails': ('', Settings.SETTING_TYPE.E_YAML),

    'm4s_bearer_token': ('', Settings.SETTING_TYPE.E_STRING),
    'm4s_bearer_expires_in': ('', Settings.SETTING_TYPE.E_STRING),

    'help-link-wikijs': ({}, Settings.SETTING_TYPE.E_YAML),

}


def get_configuration_settings(convert_to_string=False):
    configuration_settings = {}
    for k in default_configuration_settings:
        configuration_settings[k] = get_configuration_setting(k, convert_to_string)
    return configuration_settings


def set_configuration_setting(setting, value, user=None):
    if None == value:
        value = default_configuration_settings[setting][0]
    ret = set_setting(setting, value, user=user)
    if setting in setting_changed_cb:
        for cb in setting_changed_cb[setting]:
            cb[0](value, cb[1])
    return ret


def get_configuration_setting(setting, convert_to_string=False, user=None):
    found, value = get_setting(setting, user=user, convert_to_string=convert_to_string)
    if found:
        if setting == "lis-state":
            states = yaml.safe_load(value) if isinstance(value, str) else value
            states = dict(states or {})
            defaults = default_configuration_settings[setting][0]
            for key, state in defaults.items():
                states.setdefault(key, state)
            return yaml.safe_dump(states, sort_keys=False, allow_unicode=True) if convert_to_string else states
        return value
    else:
        default_setting = default_configuration_settings[setting]
        add_setting(setting, default_setting[0], default_setting[1], user=user)
        value = default_setting[0]
        if setting == "lis-state" and convert_to_string:
            return yaml.safe_dump(value, sort_keys=False, allow_unicode=True)
        return value


setting_changed_cb = {}
def subscribe_setting_changed(setting, cb, opaque):
    if setting in setting_changed_cb:
        setting_changed_cb[setting].append((cb, opaque))
    else:
        setting_changed_cb[setting] = [(cb, opaque)]
    return True


def set_json_template(key, data):
    try:
        template_string = json.dumps(data)
        template_string = re.sub('},', '},\n', template_string)
        return set_configuration_setting(key, template_string)
    except json.JSONDecodeError as e:
        raise Exception(f'Template has invalid JSON syntax: {key}, {data}, {e}')


def get_datatables_config(key):
    return get_configuration_setting(f'{key}-datatables-template')

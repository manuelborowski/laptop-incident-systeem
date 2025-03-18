from app import db
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import UnicodeText
from app import data as dl

#logging on file level
import logging, sys
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

class History(db.Model, SerializerMixin):
    __tablename__ = 'histories'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer)
    priority = db.Column(db.Integer, default=1)
    info = db.Column(UnicodeText, default=None)
    incident_type = db.Column(db.String(256), default=None)
    incident_state = db.Column(db.String(256), default=None)
    current_location = db.Column(db.String(256), default=None)
    current_incident_owner = db.Column(db.String(256), default=None)
    time = db.Column(db.DateTime, default=None)


def add(data = {}):
    return dl.models.add_single(History, data)


def update(incident, data={}):
    return dl.models.update_single(History, incident, data)


def get_m(filters=[], fields=[], order_by=None, first=False, count=False, active=True):
    return dl.models.get_multiple(History, filters=filters, fields=fields, order_by=order_by, first=first, count=count, active=active)


def get(filters=[]):
    return dl.models.get_first_single(History, filters)


def delete(ids=None):
    return dl.models.delete_multiple(History, ids=ids)


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')

############ incident-history overview list #########
def filter(query_in):
    return query_in

def pre_sql_query():
    return db.session.query(History)


def pre_sql_filter(query, filters):
    for f in filters:
        if f['id'] == 'incident-id':
            if f['value'] != 'all':
                query = query.filter(History.incident_id == f['value'])
    return query


def pre_sql_search(search_string):
    search_constraints = []
    return search_constraints





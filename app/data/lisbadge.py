from email.policy import default
from app import db
from sqlalchemy_serializer import SerializerMixin
from app import data as dl

#logging on file level
import logging, sys
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


class LisBadge(db.Model, SerializerMixin):
    __tablename__ = 'lisbadges'

    id = db.Column(db.Integer, primary_key=True)
    rfid = db.Column(db.String(256), default=None)
    label = db.Column(db.String(256), default=None)

def add(data = {}):
    return dl.models.add_single(LisBadge, data)


def update(incident, data={}):
    return dl.models.update_single(LisBadge, incident, data)


def get_m(filters=[], fields=[], order_by=None, first=False, count=False, active=True):
    return dl.models.get_multiple(LisBadge, filters=filters, fields=fields, order_by=order_by, first=first, count=count, active=active)


def get(filters=[]):
    return dl.models.get_first_single(LisBadge, filters)


def delete_m(ids=None, objs=None):
    return dl.models.delete_multiple(LisBadge, ids=ids, objs=objs)


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')



############ incident overview list #########
def filter(query_in):
    return query_in

def pre_sql_query():
    return db.session.query(LisBadge)


def pre_sql_filter(query, filters):
    return query


def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(LisBadge.id.like(search_string))
    search_constraints.append(LisBadge.rfid.like(search_string))
    return search_constraints





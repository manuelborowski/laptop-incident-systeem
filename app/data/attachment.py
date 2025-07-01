from app import db
from sqlalchemy_serializer import SerializerMixin
from app import data as dl

#logging on file level
import logging, sys
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


class Attachment(db.Model, SerializerMixin):
    __tablename__ = 'attachments'

    id = db.Column(db.Integer, primary_key=True)
    incident_id = db.Column(db.Integer)
    name = db.Column(db.String(256), default='')
    type = db.Column(db.String(256), default='')
    m4s_reference = db.Column(db.String(256), default='')


def add(data = {}):
    return dl.models.add_single(Attachment, data)


def update(obj, data={}):
    return dl.models.update_single(Attachment, obj, data)


def get_m(filters=[], fields=[], order_by=None, first=False, count=False, active=True):
    return dl.models.get_multiple(Attachment, filters=filters, fields=fields, order_by=order_by, first=first, count=count, active=active)


def get(filters=[]):
    return dl.models.get_first_single(Attachment, filters)


def delete_m(ids=None, objs=None):
    return dl.models.delete_multiple(Attachment, ids=ids, objs=objs)


def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')






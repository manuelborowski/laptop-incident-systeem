from app import db
from sqlalchemy_serializer import SerializerMixin
from app import data as dl

#logging on file level
import logging, sys
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

class ProblemType(db.Model, SerializerMixin):
    __tablename__ = 'm4s_problem_types'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'

    id = db.Column(db.Integer, primary_key=True)
    guid = db.Column(db.String(256), default=None)
    type = db.Column(db.String(256), default=None)
    category = db.Column(db.String(256), default=None)
    problem = db.Column(db.String(256), default=None)

    def add(self):
        try:
            db.session.add(self)
        except Exception as e:
            db.session.rollback()
            log.error(f'{sys._getframe().f_code.co_name}: {e}')

    def delete(self):
        try:
            db.session.delete(self)
        except Exception as e:
            db.session.rollback()
            log.error(f'{sys._getframe().f_code.co_name}: {e}')


def get_m(filters=[], fields=[], order_by=None, first=False, count=False, active=True):
    return dl.models.get_multiple(ProblemType, filters=filters, fields=fields, order_by=order_by, first=first, count=count, active=active)

def get(filters=[]):
    return dl.models.get_first_single(ProblemType, filters)

def commit():
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')

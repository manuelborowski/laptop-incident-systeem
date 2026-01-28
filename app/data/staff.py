import sys, json, datetime

from app import db
import app.data.models
from sqlalchemy_serializer import SerializerMixin

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


class Staff(db.Model, SerializerMixin):
    __tablename__ = 'staff'

    date_format = '%Y-%m-%d'
    datetime_format = '%Y-%m-%d %H:%M'

    id = db.Column(db.Integer(), primary_key=True)
    voornaam = db.Column(db.String(256), default='')
    naam = db.Column(db.String(256), default='')
    email = db.Column(db.String(256), default='')
    code = db.Column(db.String(256), default='')
    rfid = db.Column(db.String(256))
    ss_internal_nbr = db.Column(db.String(256), default='')

    new = db.Column(db.Boolean, default=True)
    delete = db.Column(db.Boolean, default=False)
    active = db.Column(db.Boolean, default=True)    # long term
    enable = db.Column(db.Boolean, default=True)    # short term
    changed = db.Column(db.TEXT, default='')

    @property
    def person_id(self):
        return self.code


def commit():
    return app.data.models.commit()


def add(data = {}, commit=True):
    return app.data.models.add_single(Staff, data, commit, timestamp=True)


def add_m(data = []):
    return app.data.models.add_multiple(Staff, data)


def update(staff, data={}, commit=True):
    return app.data.models.update_single(Staff, staff, data, commit, timestamp=True)


def delete_m(ids=[], staffs=[]):
    return app.data.models.delete_multiple(Staff, ids, staffs)


def get_m(filters=[], fields=[], order_by=None, first=False, count=False, active=True):
    return app.data.models.get_multiple(Staff, filters=filters, fields=fields, order_by=order_by, first=first, count=count, active=active)


def get(filters=[]):
    return app.data.models.get_first_single(Staff, filters)


# data is a list, with:
# staff: the ORM-staff-object
# changed: a list of properties that are changed
# property#1: the first property changed
# property#2: ....
def change_m(data = [], overwrite=False):
    try:
        for d in data:
            staff = d['staff']
            for property in d['changed']:
                v = d[property]
                if hasattr(staff, property):
                    if getattr(Staff, property).expression.type.python_type == type(v):
                        setattr(staff, property, v.strip() if isinstance(v, str) else v)
            # if the staff is new, do not set the changed flag in order not to confuse other modules that need to process the staffs (new has priority over changed)
            if staff.new:
                staff.changed = ''
            else:
                if overwrite:
                    staff.changed = json.dumps(d['changed'])
                else:
                    changed = json.loads(staff.changed) if staff.changed != '' else []
                    changed.extend(d['changed'])
                    changed = list(set(changed))
                    staff.changed = json.dumps(changed)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
    return None

############ staff overview list #########
def pre_sql_query():
    return db.session.query(Staff).filter(Staff.active == True)


def pre_sql_filter(query, filter):
    return query


def pre_sql_search(search_string):
    search_constraints = []
    search_constraints.append(Staff.naam.like(search_string))
    search_constraints.append(Staff.voornaam.like(search_string))
    search_constraints.append(Staff.code.like(search_string))
    return search_constraints



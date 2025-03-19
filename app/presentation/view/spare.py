from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from app.data.datatables import DatatableConfig
from app import data as dl, application as al
from app.presentation.view import datatable_get_data, fetch_return_error
import json, pathlib, sys

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

bp_spare = Blueprint('spare', __name__)

@bp_spare.route('/spareshow', methods=['GET', "POST"])
@login_required
def show():
    if request.method == "GET":
        return render_template("spare.html", table_config=config.create_table_config())

# invoked when the client requests data from the database
al.socketio.subscribe_on_type("spare-datatable-data", lambda type, data: datatable_get_data(config, data))

def value_update(type, data):
    spare = dl.spare.get(("id", "=", data["id"]))
    dl.spare.update(spare, {data["column"]: data["value"]})

# invoked when a single cell in the table is updated
al.socketio.subscribe_on_type("spare-cell-update", value_update)

@bp_spare.route('/spare', methods=["POST", "UPDATE", "GET"])
@login_required
def spare():
    try:
        if request.method == "GET":
            ret = al.models.get(dl.spare.Spare, request.args)
            return json.dumps(ret)
        elif request.method == "UPDATE":
            data = json.loads(request.data)
            ret = al.spare.update(data)
            return json.dumps(ret)
        else:
            data = json.loads(request.data)
            ret = al.spare.add(data)
            return json.dumps(ret)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return fetch_return_error()

@bp_spare.route('/spare/form', methods=['GET'])
@login_required
def form():
    try:
        if request.method == "GET":
            form = request.args.get('form')
            template = open(pathlib.Path(f"app/presentation/template/forms/spare/{form}.html")).read()
            return {"template": template}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: Exception, {e}')
        return fetch_return_error(f'Exception, {e}')

class Config(DatatableConfig):
    def pre_sql_query(self):
        return dl.spare.pre_sql_query()

    def pre_sql_filter(self, q, filters):
        return dl.spare.pre_sql_filter(q, filters)

    def pre_sql_search(self, search):
        return dl.spare.pre_sql_search(search)

config = Config("spare", "Reserve laptops")

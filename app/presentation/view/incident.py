from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.data.datatables import DatatableConfig
from app import data as dl, application as al
from app.presentation.view import datatable_get_data, fetch_return_error
from app.application.m4s import m4s
import json, sys, pathlib, datetime

# logging on file level
import logging
from app import MyLogFilter, top_log_handle, app

log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

bp_incident = Blueprint('incident', __name__)

@bp_incident.route('/incidentshow', methods=['GET'])
@login_required
def show():
    id_to_show = request.args.get("id")
    generate = request.args.get("generate")
    if generate:
        al.incident.generate(int(generate))
        return redirect(url_for("incident.show"))
    event = request.args.get("event")
    if event:
        al.incident.event(int(event))
        return redirect(url_for("incident.show"))
    locations = dl.settings.get_configuration_setting("lis-locations")
    location_options = [{"label": v["label"], "value": k} for (k, v) in locations.items()]
    found, default_location = dl.settings.get_setting("default-location", current_user.username)
    if not found:
        default_location = location_options[0]["value"]
        dl.settings.add_setting("default-location", default_location, user=current_user.username)
    data = {"filters": [{"id": "incident-id", "value": id_to_show}]}
    return render_template("incident.html", table_config=config.create_table_config(), view_data=data)

# invoked when the client requests data from the database
al.socketio.subscribe_on_type("incident-datatable-data", lambda type, data: datatable_get_data(config, data))

@bp_incident.route('/incident', methods=['POST', "UPDATE", "GET"])
@login_required
def incident():
    try:
        ret = {}
        if request.method == "POST":
            data = json.loads(request.data)
            ret = al.incident.add(data)
        if request.method == "UPDATE":
            data = json.loads(request.data)
            ret = al.incident.update(data)
        if request.method == "GET":
            ret = al.models.get(dl.incident.Incident, request.args)
        return json.dumps(ret)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return fetch_return_error()

@bp_incident.route('/incident/attachment', methods=['POST', "GET", "DELETE"])
@login_required
def attachment():
    try:
        ret = {}
        if request.method == "POST":
            files = request.files.getlist("attachment_file")
            incident_id = request.form.get("incident_id")
            al.attachment.add(incident_id, files)
        if request.method == "GET":
            ret = al.attachment.get(request.args["id"])
        if request.method == "DELETE":
            al.attachment.delete(request.args["ids"].split(","))
        return json.dumps(ret)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return fetch_return_error()

@bp_incident.route('/incident/attachment/meta', methods=["GET"])
@login_required
def attachment_meta():
    try:
        ret = {}
        if request.method == "GET":
            ret = al.attachment.get_meta(request.args["incident_id"])
        return json.dumps(ret)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return fetch_return_error()

@bp_incident.route('/incident/message', methods=['POST', "GET"])
@login_required
def message():
    try:
        ret = {}
        if request.method == "POST":
            data = json.loads(request.data)
            ret = al.incident.message_send(data)
        if request.method == "GET":
            id = request.args.get("id")
            ret = al.incident.message_default(id)
        return json.dumps(ret)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return fetch_return_error()

# used in incident.js
@bp_incident.route('/incident/meta', methods=['GET'])
@login_required
def meta():
    categories = dl.settings.get_configuration_setting("lis-categories")
    category_labels = {k: v["label"] for k, v in categories.items()}
    locations = dl.settings.get_configuration_setting("lis-locations")
    location_options = [{"value": k, "label": v["label"]} for k, v in locations.items()]
    location_labels = {k: v["label"] for k, v in locations.items()}
    incident_types = dl.settings.get_configuration_setting("lis-incident-types")
    type_options = [{"value": k, "label": v["label"]} for k, v in incident_types.items()]
    type_labels = {k: v["label"] for k, v in incident_types.items()}
    fields = ["incident_state", "location"]
    keyed_options = {f: {"key_field": "incident_type"} for f in fields}
    for type, data in incident_types.items():
        for f in fields:
            if f in data: keyed_options[f][type] = data[f]
    keyed_options["incident_type"] = {"key_field": "category"}
    for category, data in categories.items():
        if "incident_type" in data: keyed_options["incident_type"][category] = data["incident_type"]
    states = dl.settings.get_configuration_setting("lis-state")
    state_options = [{"value": k, "label": v["label"]} for k, v in states.items()]
    state_labels = {k: v["label"] for k, v in states.items()}
    home_locations = dl.settings.get_configuration_setting("lis-home-locations")
    home_location_options = [{"value": k, "label": location_labels[k]} for k in home_locations]
    m4s_problem_types = m4s.problem_type_get()
    m4s_category_options = [{"value": "none", "label": "Selecteer categorie"}] + [{"value": k, "label": k} for k, _ in m4s_problem_types.items()]
    m4s_problem_options = m4s_problem_types["Algemeen"]
    m4s_problem_options = [{"value": "none", "label": ""}]
    m4s_problem_labels = {t["value"]: t["label"] for _, types in m4s_problem_types.items() for t in types}
    m4s_problem_labels.update({None: "NVT"})

    _, default_location = dl.settings.get_setting("default-location", current_user.username)
    default_password = app.config["AD_DEFAULT_PASSWORD"]
    return json.dumps({"option": {"location": location_options, "incident_state": state_options, "incident_type": type_options, "m4s_category": m4s_category_options, "m4s_problem_type_guid": m4s_problem_options, "home_location": home_location_options},
                       "label": {"location": location_labels, "incident_state": state_labels, "category": category_labels, "incident_type": type_labels, "m4s_problem_type_guid": m4s_problem_labels},
                       "default": {"location": default_location, "m4s_category": "none", "m4s_problem_type_guid": m4s_problem_options[0]["value"]},
                       "default_password": default_password,
                       "category": categories,
                       "state": states,
                       "keyed_option": keyed_options,
                       "location": locations,
                       "m4s": m4s_problem_types,
                       "type": incident_types
                       })

@bp_incident.route('/incident/location', methods=['POST', ])
@login_required
def location():
    try:
        if request.method == "POST":
            data = json.loads(request.data)
            dl.settings.set_setting("default-location", data["default"], user=current_user.username)
            ret = {"data": "ok"}
            return json.dumps(ret)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: Exception, {e}')
        return fetch_return_error(f'Exception, {e}')

@bp_incident.route('/incident/laptop', methods=['GET', ])
@login_required
def laptop():
    try:
        ret = al.incident.laptop_get(request.args)
        return json.dumps(ret)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: Exception, {e}')
        return fetch_return_error()

@bp_incident.route('/incident/form', methods=['GET'])
@login_required
def form():
    try:
        if request.method == "GET":
            form = request.args.get('form')
            optional = []
            template = ""
            if form == "repair":
                template = open(pathlib.Path("app/presentation/template/forms/repair.html")).read()
            if form == "history":
                template = open(pathlib.Path("app/presentation/template/forms/history.html")).read()
            if form == "message":
                template = open(pathlib.Path("app/presentation/template/forms/ss_message.html")).read()
            if form == "loan":
                template = open(pathlib.Path("app/presentation/template/forms/loan_new.html")).read()
            if form == "setting":
                template = open(pathlib.Path("app/presentation/template/forms/setting.html")).read()
            if form == "return":
                template = open(pathlib.Path("app/presentation/template/forms/return.html")).read()
            return {"template": template, "defaults": [], "data": optional}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: Exception, {e}')
        return fetch_return_error(f'Exception, {e}')

class Config(DatatableConfig):
    def pre_sql_query(self):
        return dl.incident.pre_sql_query()

    def pre_sql_filter(self, q, filters):
        return dl.incident.pre_sql_filter(q, filters)

    def pre_sql_search(self, search):
        return dl.incident.pre_sql_search(search)

    def post_process_template(self, template):
        locations = dl.settings.get_configuration_setting("lis-locations")
        location_labels = {k: v["label"] for (k, v) in locations.items()}
        states = dl.settings.get_configuration_setting("lis-state")
        state_labels = {k: v["label"] for (k, v) in states.items()}
        state_colors = {k: v["color"] for (k, v) in states.items()}
        edit_button_template = f'<a type="button" class="btn-incident-update btn btn-success"><i class="fa-solid fa-pen-to-square" title="Incident aanpassen"></i></a></div>'
        history_button_template = f'<a type="button" class="btn-show-history btn btn-success"><i class="fa-solid fa-clock-rotate-left" title="Historiek bekijken"></i></a></div>'
        # regular user have less rights
        message_button_template = f'<a type="button" class="btn-send-message btn btn-success"><i class="fa-regular fa-envelope" title="Bericht sturen"></i></a></div>' if current_user.level >= 3 else ""
        close_button_template = f'<a type="button" class="btn-incident-close btn btn-success"><i class="fa-solid fa-xmark" title="Incident sluiten"></i></a></div>' if current_user.level >= 3 else ""
        categories = dl.settings.get_configuration_setting("lis-categories")
        category_labels = {k: v["label"] for k, v in categories.items()}
        types = dl.settings.get_configuration_setting("lis-incident-types")
        type_labels = {k: v["label"] for k, v in types.items()}
        m4s_problem_types = m4s.problem_type_get()
        m4s_problem_labels = {t["value"]: t["label"] for _, types in m4s_problem_types.items() for t in types}
        m4s_problem_labels.update({"": "NVT"})

        action_labels = {
            "started": edit_button_template + history_button_template + message_button_template,
            "transition": edit_button_template + history_button_template + message_button_template,
            "installing": edit_button_template + history_button_template + message_button_template + close_button_template,
            "repaired": edit_button_template + history_button_template + message_button_template + close_button_template,
            "prepared": edit_button_template + history_button_template + message_button_template,
            "expecting": edit_button_template + history_button_template + close_button_template,
            "signpost": edit_button_template + history_button_template + close_button_template,
            "loaned": edit_button_template + history_button_template + message_button_template + close_button_template,
            "closed": history_button_template
        }

        # used in dt.js
        # for each column below, a specific cell-render-function is attached to it.  These functions are called when the table is populated with data.
        # The render function depends on the required behaviour:
        # label: depending on the content of the cell, display a label
        # color: depending on the content of the cell, set the background color
        # ellipsis: long strings in the cell will be cut off and ellipsis are displayed
        # bool: show a tick-box when the content of the cell is true
        # less: if the value is less than value of field "than", then replace with value of field "then" else with value of field "else"
        #   if field "then" or "else" are not used, return the original data.
        # display: apply mulitple renderers (if required) and combine into template (if required).
        for column in template:
            if "data" in column:
                if column["data"] == "incident_state" and column["name"] == "Status":
                    column["display"] = {"template": "%0% (%1%/%2%)", "fields": [{"field": "incident_state", "labels": state_labels}, {"field": "current_location", "labels": location_labels},
                                                                                 {"field": "current_incident_owner"}, {"field": "incident_state", "colors": state_colors}]}
                if column["data"] == "home_location":
                    column["display"] = {"template": "%0%/%1%", "fields": [{"field": "home_location", "labels": location_labels}, {"field": "home_incident_owner"}]}
                if column["data"] == "category":
                    column["label"] = {"labels": category_labels}
                if column["data"] == "incident_type":
                    column["label"] = {"labels": type_labels}
                if column["data"] == "m4s_problem_type_guid":
                    column["label"] = {"labels": m4s_problem_labels}
                if column["data"] == "m4s_reference":
                    column["display"] = {"template": '<a target="_blank" href="https://byod.signpost.be/incidents/%0%">%0%</a>', "fields": [{"field": "m4s_reference"}]}
                if column["data"] == "info":
                    column["ellipsis"] = {"cutoff": 30, "wordbreak": True}
                if column["data"] == "lis_badge_id":
                    column["less"] = {"than": 0, "then": ""}
                if column["data"] == "incident_state" and column["name"] == "Actie":
                    column["label"] = {"labels": action_labels}
                if column["data"] == "spare_laptop_name":
                    column["display"] = {"template": "%0% %1%", "fields": [{"field": "spare_laptop_name"}, {"field": "charger", "bool": True}]}
        return template

    def format_data(self, db_list, total_count=None, filtered_count=None):
        return al.incident.format_data(db_list, total_count, filtered_count)

config = Config("incident", "Incidenten")

@bp_incident.route('/mincidentshow', methods=['GET'])
@login_required
def m_show():
    fields = ["id", "lis_badge_id", "laptop_owner_name", "incident_state", "time"]
    incidents = dl.incident.get_m(("category", "=", "repair"), fields=fields)
    incidents = [{f: i[e].strftime("%Y-%m-%d %H:%M") if isinstance(i[e], datetime.datetime) else i[e] for e, f in enumerate(fields)} for i in incidents]
    return render_template("m/incident.html", incidents=incidents)

@bp_incident.route('/mincidentdetail', methods=['GET'])
@login_required
def m_detail():
    id = request.args.get('id')
    if id:
        incident = dl.incident.get(("id", "=", id))
        histories = [h.to_dict() for h in dl.history.get_m(("incident_id", "=", incident.id))]
        if incident:
            return render_template("m/repair.html", incident=incident.to_dict(), histories=histories)
    else:
        return render_template("m/repair.html")

@bp_incident.route('/incident/qr', methods=['GET'])
@login_required
def qr():
    try:
        if request.method == "GET":
            generate_new_qr = request.args.get("new")
            qr = al.user.qr_get(current_user, generate_new_qr)
            return qr
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: Exception, {e}')
        return fetch_return_error(f'Exception, {e}')

@bp_incident.route('/incidenthelp', methods=['GET'])
@login_required
def help():
    return render_template("help.html")

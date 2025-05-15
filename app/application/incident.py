import sys, datetime, re, random, requests, wonderwords, json
from app.application.m4s import m4s
from app import app, data as dl, application as al
from flask_login import current_user
from flask import request

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def __send_incident_message_to_location(incident):
    try:
        if incident.lis_badge_id > 999999:
            return True
        body_template = [
            {"state": "transition", "heading": {"s": "1 incident komt van een andere locatie", "m": "{nbr} incidenten komen van een andere locatie"}},
            {"state": "started", "heading": {"s": "1 incident in reparatie", "m": "{nbr} incidenten in reparatie"}},
            {"state": "repaired", "heading": {"s": "1 incident hersteld, laptop nog niet afgehaald", "m": "{nbr} incidenten hersteld, laptop nog niet afgehaald"}},
            {"state": "expecting", "heading": {"s": "1 retour-laptop wordt verwacht", "m": "{nbr} retour-laptops worden verwacht"}},
            {"state": "signpost", "heading": {"s": "1 retour-laptop wacht om opgehaald te worden door Signpost", "m": "{nbr} retour-laptops wachten om opgehaald te worden door Signpost"}},
        ]
        logging = f"{incident.id}/{incident.current_location}"
        locations = dl.settings.get_configuration_setting("lis-locations")
        states = dl.settings.get_configuration_setting("lis-state")
        location = locations[incident.current_location]
        if "email" in location:
            url = request.url_root
            incidents = dl.incident.get_m(("current_location", "=", incident.current_location))
            state2incident = {}
            for incident in incidents:
                if incident.incident_state in state2incident:
                    state2incident[incident.incident_state].append(incident)
                else:
                    state2incident[incident.incident_state] = [incident]
            body = ""
            for item in body_template:
                if item["state"] in state2incident:
                    nbr = len(state2incident[item["state"]])
                    line = item["heading"]["m"].replace("{nbr}", str(nbr)) if nbr > 1 else item["heading"]["s"]
                    body += f"<b style=\"background-color:{states[item['state']]['color']}\"><u>{line}</u></b><br>"
                    for incident in state2incident[item["state"]]:
                        line = (f'<a href="{url}incidentshow?id={incident.id}">&#x1F517;</a>(Wie) {incident.laptop_owner_name}, (LIS id) {incident.lis_badge_id}')
                        body += f"{line}<br>"
                    body += "<br><br>"
            if body:
                body += "<br><br>Laptop Incident Systeem"
                dl.entra.entra.send_mail(location["email"], "LIS update", body)
                log.info(f"{sys._getframe().f_code.co_name}, location-changed mail sent to {location['email']}, {logging}")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')

def __send_return_message_to_location(incident):
    try:
        locations = dl.settings.get_configuration_setting("lis-locations")
        location = locations[incident.home_location]
        if "email" in location:
            url = request.url_root
            body = "<b><u>1 laptop aangemeld voor retour</u></b><br>"
            body += (f'<a href="{url}incidentshow?id={incident.id}">&#x1F517;</a>(Tijd) {incident.time}, (Wie) {incident.current_incident_owner}, '
                    f'(Locatie) {locations[incident.home_location]["label"]}, (Info) {incident.info}')
            body += "<br><br>Laptop Incident Systeem"
            dl.entra.entra.send_mail(location["email"], "LIS update", body)
            log.info(f"{sys._getframe().f_code.co_name}, new-return mail sent to {location['email']}, {incident.info}")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')

def __event(incident, event):
    try:
        incident.flag_reset("state-timeout")
        if incident.category == "repair":
            if event == "transition":
                __send_incident_message_to_location(incident)
            elif event == "closed":
                if incident.laptop_owner_password_default:
                    __password_update(incident, app.config["AD_DEFAULT_PASSWORD"], True)
        elif incident.category == "return":
            if event == "prepared":
                __send_return_message_to_location(incident)
            if event == "transition":
                __send_incident_message_to_location(incident)
        dl.incident.commit()
        log.info(f'{sys._getframe().f_code.co_name}: state change, incident-id/state/event, {incident.id}/{incident.incident_state}/{event}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        raise e

def __password_update(incident, password, must_update=False):
    try:
        adp_url = app.config["ADP_URL"]
        if adp_url != "":
            test = app.config["ADP_TEST"]
            if incident.laptop_type == "leerling":
                user = dl.student.get(("leerlingnummer", "=", incident.laptop_owner_id))
                user_id = user.username
            elif incident.laptop_type == "personeel":
                user = dl.staff.get(("code", "=", incident.laptop_owner_id))
                user_id = user.code
            else:
                return False
            ret = requests.post(adp_url, json={"user": user_id, "password": password, "test": test})
            if ret.status_code == 200:
                resp = json.loads(ret.text)
                log.info(f'{sys._getframe().f_code.co_name}: password of {user_id} set to {password}, must_update {must_update}, test {test}, resp {resp["status"]}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return False
    return True

def add(data):
    try:
        data["time"] = datetime.datetime.now()
        data["home_incident_owner"] = current_user.username
        data["current_incident_owner"] = current_user.username
        _, default_location = dl.settings.get_setting("default-location", current_user.username)
        data["home_location"] = default_location
        data["current_location"] = data["location"]
        incident = dl.incident.add(data)
        if incident:
            if data["current_location"] != data["home_location"]:
                __event(incident, "transition")
            # store some data in history
            history_data = {"incident_id": incident.id, "priority": incident.priority, "info": incident.info, "incident_type": incident.incident_type,
                            "incident_state": incident.incident_state, "current_location": incident.current_location, "current_incident_owner": incident.current_incident_owner, "time": incident.time, }
            if incident.laptop_owner_password_default:
                __password_update(incident, app.config["AD_DEFAULT_PASSWORD"])
            history = dl.history.add(history_data)
            if incident.incident_type == "hardware":
                ret = m4s.case_add(incident)
                if ret["status"] != "ok": return ret
        log.info(f'{sys._getframe().f_code.co_name}: incident added, {data}')
        return {"data": {"status": True, "id": incident.id}}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {str(type(e))}, {e}')
        return {"status": "error", "msg": f"{str(type(e))}, {e}"}

def update(data):
    try:
        incident = dl.incident.get(("id", "=", data["id"]))
        if incident:
            current_laptop_owner_password_default = incident.laptop_owner_password_default
            # if the info field is empty, but the previous was not, copy that...
            # don't copy when sending a message, i.e. the message can be empty
            if data["info"] == "" and "event" in data and data["event"] != "message":
                history_latest = dl.history.get_m(("incident_id", "=", data["id"]), order_by="-id", first=True)
                if history_latest:
                    data["info"] = history_latest.info
            data["time"] = datetime.datetime.now()
            data["current_incident_owner"] = current_user.username
            if "location" in data:
                data["current_location"] = data["location"]
                if data["current_location"] != incident.current_location:
                    __event(incident, "transition")
            # incident type changes from hardware to something else.  Save M4S reference in history and clear M4S specific fields.
            if "incident_type" in data and incident.incident_type == "hardware" and data["incident_type"] != "hardware":
                m4s_problem = dl.m4s.get(("guid", "=", incident.m4s_problem_type_guid))
                info = f"M4S: {incident.m4s_reference}, {m4s_problem.problem if m4s_problem else 'NVT'}"
                history_data = {"incident_id": incident.id, "priority": incident.priority, "info": info, "incident_type": incident.incident_type,
                    "incident_state": incident.incident_state, "current_location": incident.current_location, "current_incident_owner": incident.current_incident_owner, "time": incident.time,}
                history = dl.history.add(history_data)
                data["m4s_reference"] = ""
                data["m4s_problem_type_guid"] = ""
                data["m4s_guid"] = None
            del data["id"]
            event = data["incident_state"] if incident.incident_state != data["incident_state"] else None
            incident = dl.incident.update(incident, data)
            if incident:
                if event:
                    __event(incident, event)
                # store some data in history
                history_data = {"incident_id": incident.id, "priority": incident.priority, "info": incident.info, "incident_type": incident.incident_type,
                    "incident_state": incident.incident_state, "current_location": incident.current_location, "current_incident_owner": incident.current_incident_owner, "time": incident.time,}
                history = dl.history.add(history_data)
                if not current_laptop_owner_password_default and incident.laptop_owner_password_default:
                    __password_update(incident, app.config["AD_DEFAULT_PASSWORD"])
                log.info(f'{sys._getframe().f_code.co_name}: incident updated, {data}')
                if "incident_type" in data and data["incident_type"] == "hardware" and incident.m4s_guid == None:  # changed type from software to hardware, put incident in M4S if not already in M4S
                    ret = m4s.case_add(incident)
                    if ret["status"] != "ok": return ret
                return {"id": incident.id}
        log.error(f'{sys._getframe().f_code.co_name}: incident not found, id {data["id"]}')
        return {"status": "error", "msg": f'Incident niet gevonden, id {data["id"]}'}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {str(type(e))}, {e}')
        return {"status": "error", "msg": f"{str(type(e))}, {e}"}

def get(data={}):
    try:
        filters = [(k, "=", v) for k,v in data.items()]
        incidents = dl.incident.get_m(filters)
        if incidents:
            if len(incidents) > 1:
                return {"data": [i.to_dict() for i in incidents]}
            else:
                return {"data": incidents[0].to_dict()}
        else:
            return {"status": "error", "msg": f"Incident niet gevonden, filter {filters}"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {data}, {e}')
        return {"status": "error", "msg": str(e)}

def laptop_get(data):
    try:
        id = data["id"]
        type = data["type"]
        url = app.config["ENTRA_API_URL"]
        key = app.config["ENTRA_API_KEY"]
        if type == 'leerling':
            url += f'/student?filters=leerlingnummer$=${id},active$=$null'
        else:
            url += f'/staff?filters=code$=${id}'
        resp = requests.get(url, headers={"X-Api-Key": key})
        if resp.status_code == 200:
            data = resp.json()
            if "status" in data and data["status"] == True:
                user_entra_id = data["data"][0]["entra_id"]
                url = app.config["ENTRA_API_URL"]
                url = f'{url}/device/get?filters=user_entra_id$=${user_entra_id},active$=$null'
                resp = requests.get(url, headers={"X-Api-Key": key})
                if resp.status_code == 200:
                    data = resp.json()
                    if "status" in data and data["status"] == True:
                        return data["data"]
        else:
            raise
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {data}, {e}')
        raise

def message_default(incident_id):
    try:
        incident = dl.incident.get(("id", "=", incident_id))
        if incident:
            template = dl.settings.get_configuration_setting("ss-student-message-template")
            laptop_owner = None
            if incident.laptop_type == "leerling":
                laptop_owner = dl.student.get(("leerlingnummer", "=", incident.laptop_owner_id))
            elif incident.laptop_type == "personeel":
                laptop_owner = dl.staff.get(("code", "=", incident.laptop_owner_id))
            if laptop_owner:
                template = template.replace("%%VOORNAAM%%", laptop_owner.voornaam)
                password_match_template = re.search("%%IF_STANDARD_PASSWORD%%.*?%%ENDIF%%", template, re.DOTALL)[0]
                if incident.laptop_owner_password_default:
                    password_match = password_match_template.replace("%%IF_STANDARD_PASSWORD%%", "")
                    password_match = password_match.replace("%%ENDIF%%", "")
                    template = template.replace(password_match_template, password_match)
                else:
                    template = template.replace(password_match_template, "")
                staff = dl.staff.get(("code", "=", current_user.username))
                if staff:
                    signature = f"{staff.naam} {staff.voornaam}"
                else:
                    signature = "ICT"
                template = template.replace("%%SIGNATURE%%", signature)
                return {"message_subject": "Uw laptop is klaar",  "message_content": template}
            return {"message_subject": "", "message_content": ""}
        log.error(f'{sys._getframe().f_code.co_name}: unknown incident id {incident_id}')
        return {"status": "error", "msg": f"Kan standaardbericht niet ophalen, incident id is niet gekend {incident_id}"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": str(e)}

def message_send(data):
    try:
        data["time"] = datetime.datetime.now()
        incident = dl.incident.get(("id", "=", data["id"]))
        if incident:
            CLEANR = re.compile('<.*?>')
            # store some data in history
            data['message_content'] = data['message_content'].replace("\n", "<br>")
            info = f"Bericht gestuurd:(O) {data['message_subject']}(I) {data['message_content']}"
            info = re.sub(CLEANR, '', info)
            history_data = {"incident_id": incident.id, "priority": incident.priority, "info": info, "incident_type": incident.incident_type,
                            "incident_state": incident.incident_state, "current_location": incident.current_location, "current_incident_owner": incident.current_incident_owner,
                            "time": incident.time, "id": incident.id}
            update(history_data)
            send_to_overwrite = dl.settings.get_configuration_setting("generic-ss-send-to")
            ss_to = []
            if send_to_overwrite != "":
                for code in send_to_overwrite.split(","):
                    staff = dl.staff.get(("code", "=", code))
                    ss_to.append(staff.ss_internal_nbr)
            else:
                if incident.laptop_type == "leerling":
                    laptop_owner = dl.student.get(("leerlingnummer", "=", incident.laptop_owner_id))
                    ss_to = [laptop_owner.leerlingnummer]
                elif incident.laptop_type == "personeel":
                    laptop_owner = dl.staff.get(("code", "=", incident.laptop_owner_id))
                    ss_to = [laptop_owner.ss_internal_nbr]
                else: # spare laptop
                    location = dl.settings.get_configuration_setting("lis-locations")[incident.laptop_owner_id]
                    if "message" in location:
                        for code in location["message"]:
                            staff = dl.staff.get(("code", "=", code))
                            if staff:
                                ss_to.append(staff.ss_internal_nbr)

            staff = dl.staff.get(("code", "=", current_user.username))
            if staff:
                sender = staff.ss_internal_nbr
            else:
                sender = "lis"
            co_accounts = [0, 1, 2] if data["co_accounts"] else [0]
            log.info(f"{sys._getframe().f_code.co_name}, ss-message to {ss_to}, from {sender}")
            for to in ss_to:
                for co_account in co_accounts:
                    ret = dl.smartschool.smartschool.send_message(to, sender, data['message_subject'], data['message_content'], co_account)
                    if ret != 0:
                        log.error(f'{sys._getframe().f_code.co_name}: send_message returned {ret}')
            return {"status": "ok", "msg": f"Bericht is verstuurd"}
        log.error(f'{sys._getframe().f_code.co_name}: incident not found, {data["id"]}')
        return {"status": "error", "msg": f'Incident met id {data["id"]} niet gevonden'}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": str(e)}

def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    students = dl.student.get_m()
    student_cache = {s.leerlingnummer: s.username for s in students}
    for i in db_list:
        em = i.to_dict()
        em.update({"row_action": i.id, "DT_RowId": i.id,"state_event": "NA"})
        if i.laptop_type == "personeel":
            em.update({"login": i.laptop_owner_id})
        elif i.laptop_type == "leerling":
            em.update({"login": student_cache[i.laptop_owner_id] if i.laptop_owner_id in student_cache else ""})
        else:
            em.update({"login": ""})
        out.append(em)
    return total_count, filtered_count, out

def incident_cron_state_timeout(opaque=None):
    try:
        timeout_locations = {}
        now = datetime.datetime.now()
        def __check_timeout(incidents, key, timeout):
            for incident in incidents:
                if now > incident.time + timeout and not incident.flag_check("state-timeout"):
                    log.info(f'{sys._getframe().f_code.co_name}: state/incident-type timeout, incident {incident.id}, state/incident-type {key}')
                    incident.flag_set("state-timeout")
                    if incident.current_location in timeout_locations:
                        timeout_locations[incident.current_location].append(incident)
                    else:
                        timeout_locations[incident.current_location] = [incident]

        log.info(f'{sys._getframe().f_code.co_name}: START')
        states = dl.settings.get_configuration_setting("lis-state")
        locations = dl.settings.get_configuration_setting("lis-locations")
        for key, state in states.items():
            if "timeout" in state:
                timeout = al.common.ini2timedelta(state["timeout"])
                incidents = dl.incident.get_m([("incident_state", "=", key), ("incident_state", "!", "closed")])
                __check_timeout(incidents, key, timeout)

        incident_types = dl.settings.get_configuration_setting("lis-incident-types")
        for key, type in incident_types.items():
            if "timeout" in type:
                timeout = al.common.ini2timedelta(type["timeout"])
                incidents = dl.incident.get_m([("incident_type", "=", key), ("incident_state", "!", "closed")])
                __check_timeout(incidents, key, timeout)
        dl.incident.commit()
        body_template = {"s": "1 incident staat te lang in dezelfde toestand", "m": "{nbr} incidenten staan te lang in dezelfde toestand"}
        url = app.config["ROOT_URL"] if "ROOT_URL" in app.config else ""
        for key, incidents in timeout_locations.items():
            location = locations[key]
            if "email" in location:
                body = ""
                nbr = len(incidents)
                line = body_template["m"].replace("{nbr}", str(nbr)) if nbr > 1 else body_template["s"]
                body += f"<b><u>{line}</u></b><br>"
                for incident in incidents:
                    line = (f'<a href="{url}incidentshow?id={incident.id}">&#x1F517;</a>(Tijd) {incident.time}, (Wie) {incident.current_incident_owner}, '
                            f'(Toestand) {states[incident.incident_state]["label"]}, (Locatie) {locations[incident.current_location]["label"]}, '
                            f'(Type) {incident.incident_type}, (Info) {incident.info}')
                    body += f"{line}<br>"
                body += "<br><br>"
                if body:
                    body += "<br><br>Laptop Incident Systeem"
                    dl.entra.entra.send_mail(location["email"], "LIS: toestand timeout", body)
                    log.info(f"{sys._getframe().f_code.co_name}, state-timeout mail sent to {location['email']}")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')





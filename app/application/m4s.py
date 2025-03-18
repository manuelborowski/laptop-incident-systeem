from app import app, data as dl
import sys, requests, datetime, json
from flask_login import current_user

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

class M4S:

    def init_bearer(self):
        try:
            self.bearer_token = dl.settings.get_configuration_setting("m4s_bearer_token")
            expires_in = dl.settings.get_configuration_setting("m4s_bearer_expires_in")
            renew_token = False
            if expires_in != "":
                expire_time = datetime.datetime.strptime(expires_in, "%Y-%m-%d %H:%M:%S")
                current_time = datetime.datetime.now()
                if current_time > expire_time or (expire_time - current_time).seconds < 60:
                    renew_token = True
            if renew_token or self.bearer_token == "":
                body = {
                "client_id": app.config["M4S_ID"],
                "client_secret": app.config["M4S_SECRET"],
                "scope": "openid",
                "resource": "management_portal:api",
                "grant_type": "client_credentials",
                }
                resp = requests.post(app.config["M4S_BEARER_URL"], headers={"Content-Type": "application/x-www-form-urlencoded"},  data=body)
                if resp.status_code == 200:
                    resp = json.loads(resp.text)
                    expire_time = (datetime.datetime.now() + datetime.timedelta(seconds=resp["expires_in"])).replace(microsecond=0)
                    dl.settings.set_configuration_setting("m4s_bearer_token", resp["access_token"])
                    dl.settings.set_configuration_setting("m4s_bearer_expires_in", expire_time)
                    self.bearer_token = resp["access_token"]
                    log.info(f'{sys._getframe().f_code.co_name}: new bearer token, expires at {str(expire_time)}')
                else:
                    self.bearer_token = None
                    log.error(f'{sys._getframe().f_code.co_name}: request for bearer returned status {resp.status_code}')
        except Exception as e:
            log.error(f'{sys._getframe().f_code.co_name}: {e}')

    def cases_get(self):
        try:
            self.init_bearer()
            url = app.config["M4S_API_URL"]
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            resp = requests.get(f'{url}/field-service/cases', headers=headers)
            if resp.status_code == 200:
                resp = json.loads(resp.text)
                log.info(resp)
        except Exception as e:
            log.error(f'{sys._getframe().f_code.co_name}: {e}')


    def problem_types_get_from_m4s(self):
        try:
            self.init_bearer()
            url = app.config["M4S_API_URL"]
            headers = {"Authorization": f"Bearer {self.bearer_token}"}
            resp = requests.get(f'{url}/field-service/problem-types', headers=headers)
            if resp.status_code == 200:
                resp = json.loads(resp.text)
                if "items" in resp:
                    return resp["items"]
            log.error(f'{sys._getframe().f_code.co_name}: returned status code {resp.status_code}')
        except Exception as e:
            log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return []

    def problem_type_get(self):
        types = dl.m4s.get_m()
        categories = {}
        for type in types:
            if not type.category: continue
            category = type.category.capitalize()
            if category not in categories:
                categories[category] = [{"label": type.problem.capitalize(), "value": type.guid}]
            else:
                categories[category].append({"label": type.problem.capitalize(), "value": type.guid})
        [v.sort(key=lambda x: x["label"]) for _, v in categories.items()]
        return categories

    def case_add(self, incident):
        try:
            m4s_test = app.config["M4S_TEST"] if "M4S_TEST" in app.config else False
            if m4s_test == True:
                log.info("M4S test, no incident is added into M4S")
                incident.m4s_guid = "test-guid"
                dl.incident.commit()
                return True # test purposes
            self.init_bearer()
            url = app.config["M4S_API_URL"]
            headers = {"Authorization": f"Bearer {self.bearer_token}", "Content-Type": "application/json"}
            location = dl.settings.get_configuration_setting("lis-locations")[incident.current_location]
            [street, number] = location["signpost"].split("+")
            staff = dl.staff.get(("code", "=", current_user.username))
            [contact_first_name, contact_last_name] = [staff.voornaam, staff.naam] if staff else ["manuel", "borowski"]
            contact_email = f"{contact_first_name}.{contact_last_name}@campussintursula.be"
            data = {
                "truthStatement": True,
                "serialNumber": incident.laptop_serial,
                "institutionGuid": app.config["M4S_INSTITUTION_GUID"],
                "problemTypeGuid": incident.m4s_problem_type_guid,
                "description": incident.info,
                "address": {
                    "street": street,
                    "number": number,
                    "repairAtInstitution": True
                },
                "contacts": [
                    {
                        "firstName": contact_first_name,
                        "lastName": contact_last_name,
                        "email": contact_email
                    }
                ],
                "billingContact": app.config["M4S_BILLING_INFO"]
            }
            data["address"].update(app.config["M4S_ADDRESS_INFO"])
            data["status"] = "draft" if m4s_test == "draft" else "new"
            resp = requests.post(f"{url}/field-service/cases", headers=headers, data=json.dumps(data))
            if resp.status_code == 201:
                resp = json.loads(resp.text)
                incident.m4s_guid = resp["guid"]
                incident.m4s_reference = resp["ourReference"]
                log.info(f'{sys._getframe().f_code.co_name}: inserted in m4s, lis-id/m4s-guid/m4s-reference: {incident.id}/{incident.m4s_guid}/{incident.m4s_reference}')
                dl.incident.commit()
                return True
            log.error(f'{sys._getframe().f_code.co_name}: post cases returned {resp.status_code}')
            raise Exception(f"post cases returned {resp.status_code}")
        except Exception as e:
            log.error(f'{sys._getframe().f_code.co_name}: {e}')
            raise e




m4s = M4S()

def m4s_cron_get_problem_types(opaque=None):
    try:
        log.info(f'{sys._getframe().f_code.co_name}: START')
        nbr_new = 0
        nbr_update = 0
        nbr_delete = 0
        m4s_types = m4s.problem_types_get_from_m4s()
        if len(m4s_types) > 0:
            lis_types = dl.m4s.get_m()
            lis_types = {t.guid : t for t in lis_types}
            for type in m4s_types:
                if type["guid"] in lis_types: # update existing
                    lis_type = lis_types[type["guid"]]
                    lis_type.type = type["type"]
                    lis_type.category = type["category"]
                    lis_type.problem = type["problem"]
                    nbr_update += 1
                    del lis_types[type["guid"]]
                    continue
                lis_type = dl.m4s.ProblemType()  # add new
                lis_type.guid = type["guid"]
                lis_type.type = type["type"]
                lis_type.category = type["category"]
                lis_type.problem = type["problem"]
                lis_type.add()
                nbr_new +=1
            # delete not used
            for guid, type in lis_types.items():
                type.delete()
                nbr_delete += 1
        dl.m4s.commit()
        log.error(f'{sys._getframe().f_code.co_name}: new/updated/deleted, {nbr_new}/{nbr_update}/{nbr_delete}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


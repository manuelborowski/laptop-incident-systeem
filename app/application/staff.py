from app import app, data as dl
import sys, requests

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def get(data):
    try:
        filters = [(k, "=", v) for k,v in data.items()]
        if filters:
            staff = dl.staff.get(filters)
            if staff:
                return {"data": staff.to_dict()}
            else:
                return {"status": "error", "msg": f"Staff not found, filter {filters}"}
        else:
            return {"status": "error", "msg": f"No valid data {data}"}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {data}, {e}')
        return {"status": "error", "msg": {str(e)}}

######################### CRON HANDLERS ##################################
def staff_cron_load_from_sdh(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    updated_staffs = []
    nbr_updated = 0
    new_staffs = []
    deleted_staffs = []
    try:
        sdh_staff_url = app.config["SDH_GET_STAFF_URL"]
        sdh_key = app.config["SDH_API_KEY"]
        res = requests.get(sdh_staff_url, headers={'x-api-key': sdh_key})
        if res.status_code == 200:
            sdh_staffs = res.json()
            if sdh_staffs['status']:
                log.info(f'{sys._getframe().f_code.co_name}, retrieved {len(sdh_staffs["data"])} staffs from SDH')
                db_staffs = dl.staff.get_m()
                db_code_to_staff = {s.code: s for s in db_staffs}
                for sdh_staff in sdh_staffs["data"]:
                    if sdh_staff["code"] in db_code_to_staff:
                        db_staff = db_code_to_staff[sdh_staff["code"]]
                        update = {}
                        if db_staff.voornaam != sdh_staff["voornaam"]:
                            update["voornaam"] = sdh_staff["voornaam"]
                        if db_staff.naam != sdh_staff["naam"]:
                            update["naam"] = sdh_staff["naam"]
                        if db_staff.email != sdh_staff["email"]:
                            update["email"] = sdh_staff["email"]
                        if db_staff.rfid != sdh_staff["rfid"]:
                            update["rfid"] = sdh_staff["rfid"]
                        if db_staff.ss_internal_nbr != sdh_staff["ss_internal_nbr"]:
                            update["ss_internal_nbr"] = sdh_staff["ss_internal_nbr"]
                        if update:
                            update["changed"] = list(update.keys())
                            update.update({"staff": db_staff})
                            updated_staffs.append(update)
                            log.info(f'{sys._getframe().f_code.co_name}, Update staff {db_staff.code}, update {update}')
                            nbr_updated += 1
                        del(db_code_to_staff[sdh_staff["code"]])
                    else:
                        new_staffs.append({"code": sdh_staff["code"], "naam": sdh_staff["naam"], "voornaam": sdh_staff["voornaam"], "email": sdh_staff["email"], "rfid": sdh_staff["rfid"], "ss_internal_nbr": sdh_staff["ss_internal_nbr"]})
                        log.info(f'{sys._getframe().f_code.co_name}, New staff {sdh_staff["code"]}, Rfid {sdh_staff["rfid"]}')
                deleted_staffs = [v for (k, v) in db_code_to_staff.items()]
                for staff in deleted_staffs:
                    updated_staffs.append({"staff": staff, "delete": True, "changed": ["delete"]})
                    log.info(f'{sys._getframe().f_code.co_name}, Delete staff {staff.code}')
                dl.staff.add_m(new_staffs)
                dl.staff.change_m(updated_staffs)
                log.info(f'{sys._getframe().f_code.co_name}, staffs add {len(new_staffs)}, update {nbr_updated}, delete {len(deleted_staffs)}')
            else:
                log.info(f'{sys._getframe().f_code.co_name}, error retrieving staffs from SDH, {sdh_staffs["data"]}')
        else:
            log.error(f'{sys._getframe().f_code.co_name}: api call to {sdh_staff_url} returned {res.status_code}')
        log.info(f"{sys._getframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return 0, 0, 0
    return len(new_staffs), nbr_updated, len(deleted_staffs)


def staff_cron_post_processing(opaque=None, **kwargs):
    log.info(f"{sys._getframe().f_code.co_name}, START")
    try:
        db_staffs = dl.staff.get_m(("changed", "!", ""))
        db_staffs += dl.staff.get_m(("new", "=", True))
        for staff in db_staffs:
            staff.new = False
            staff.changed = ""
            staff.changed_old = ""
        dl.staff.commit()
        db_staffs = dl.staff.get_m(("delete", "=", True))
        dl.staff.delete_m(staffs=db_staffs)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')


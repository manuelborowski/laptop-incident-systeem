import sys, base64, os
from app import data as dl, application as al
from app.application.m4s import m4s

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def add(incident_id, attachments, to_m4s):
    try:
        file = attachments[0] # file is a werkzeug.FileStorage object
        m4s_reference = None
        file_parts = file.filename.split(".")
        if len(file_parts) < 2:
            log.error(f'{sys._getframe().f_code.co_name}: attachment without extension')
            return {"status": "error", "msg": "Bijlage moet een extensie hebben"}
        file_extension = file_parts[-1]
        if to_m4s:
            resp = m4s.case_file_add(incident_id, file.filename, file.stream, file.mimetype)
            if resp["status"] != "ok":
                return resp
            m4s_reference = resp["m4s_reference"]
        attachment = dl.attachment.add({
            "incident_id": int(incident_id),
            "name": file.filename,
            "type": file.mimetype,
            "m4s_reference": m4s_reference
        })
        file.seek(0) # make sure to read from the start
        file.save(f"attachments/{attachment.id}.{file_extension}")
        log.info(f'{sys._getframe().f_code.co_name}: saved attachment "{file.filename}", (type) {file.content_type}, (id) {incident_id} (to-m4s) {to_m4s}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": str(e)}

def update(data):
    try:
        to_m4s = data["to_m4s"]
        attachment_id = data["id"]
        if to_m4s:
            attachment = dl.attachment.get(("id", "=", attachment_id))
            if not attachment:
                log.error(f'{sys._getframe().f_code.co_name}: error: attachment not found: {attachment_id}')
                return {"status": "error", "msg": "Attachment niet gevonden"}
            file_parts = attachment.name.split(".")
            file_extension = file_parts[-1]
            with open(f"attachments/{attachment.id}.{file_extension}", "rb") as f:
                resp = m4s.case_file_add(attachment.incident_id, attachment.name, f, attachment.type)
                if resp["status"] != "ok":
                    return resp
                dl.attachment.update(attachment, {"m4s_reference": resp["m4s_reference"]})
                log.info(f'{sys._getframe().f_code.co_name}: updated attachment "{attachment.name}", (type) {attachment.type}, (id) {attachment.incident_id} (to-m4s) {to_m4s}')
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": str(e)}

def delete(ids):
    try:
        for id in ids:
            os.remove(f"attachments/{id}");
        dl.attachment.delete_m(ids)
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": str(e)}

def get(id):
    try:
        data = None
        attachment = dl.attachment.get(("id", "=", id))
        data = attachment.to_dict()
        file_parts = attachment.name.split(".")
        file_extension = file_parts[-1]
        with open(f"attachments/{attachment.id}.{file_extension}", "rb") as file:
            data["file"] = base64.b64encode(file.read()).decode('utf-8')
        return {"data": data}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {data}, {e}')
        return {"status": "error", "msg": {str(e)}}

# Returns all except the file-data
def get_meta(incident_id):
    try:
        data = []
        attachments = dl.attachment.get_m(("incident_id", "=", incident_id))
        for a in attachments:
            data.append(a.to_dict())
        return {"data": data}
    except Exception as e:
        log.error(f'{sys._getframe().f_code.co_name}: {data}, {e}')
        return {"status": "error", "msg": {str(e)}}


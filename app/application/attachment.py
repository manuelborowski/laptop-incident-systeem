import sys, base64, os
from app import data as dl

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def add(incident_id, attachments):
    try:
        for file in attachments:
            attachment = dl.attachment.add({
                "incident_id": int(incident_id),
                "name": file.filename,
                "type": file.content_type,
            })
            log.info(f'{sys._getframe().f_code.co_name}: saved attachment "{file.filename}", (type) {file.content_type}, (id) {incident_id}')
            file.save(f"attachments/{attachment.id}")
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
        with open(f"attachments/{attachment.id}", "rb") as file:
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


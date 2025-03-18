__all__ = ["user", "socketio", "datatables", "common", "formio", "settings", "incident", "student", "cron", "staff", "spare", "lisbadge", "history", "models", "m4s", "attachment", "log"]

import app.application.user
import app.application.socketio
import app.application.datatables
import app.application.common
import app.application.formio
import app.application.settings
import app.application.incident
import app.application.student
import app.application.staff
import app.application.spare
import app.application.lisbadge
import app.application.history
import app.application.models
import app.application.m4s
import app.application.attachment
import app.application.log

from app.application.student import student_cron_load_from_sdh, student_cron_post_processing
from app.application.staff import staff_cron_load_from_sdh, staff_cron_post_processing
from app.application.incident import incident_cron_state_timeout
from app.application.m4s import m4s_cron_get_problem_types

# tag, cront-task, label, help
cron_table = [
    ('SDH-STUDENT-UPDATE', student_cron_load_from_sdh, 'VAN SDH, upload student', ''),
    ('SDH-STAFF-UPDATE', staff_cron_load_from_sdh, 'VAN SDH, upload staff', ''),
    ('STATE_TIMEOUT', incident_cron_state_timeout, 'Controleer of incidenten te lang in dezelfde toestand blijven', ''),
    ('M4S_PROBLEM_TYPES', m4s_cron_get_problem_types, 'VAN M4S, upload the probleem types', ''),
    ('SDH-STUDENT-POST-PROCESSING', student_cron_post_processing, 'Studenten: reset vlaggen', ''),
    ('SDH-STAFF-POST-PROCESSING', staff_cron_post_processing, 'Personeel: reset vlaggen', ''),
]

import app.application.cron
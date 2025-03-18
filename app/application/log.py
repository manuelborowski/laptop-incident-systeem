from app import subscribe_email_log_handler_cb, data as dl

# from app import email_log_handler
def email_log_handler(message_body):
    to_list = dl.settings.get_configuration_setting("logging-inform-emails")
    if to_list:
        dl.entra.entra.send_mail(to_list, "LIS ERROR LOG", message_body)

subscribe_email_log_handler_cb(email_log_handler)

// create a popup the displayes a message with a specified bordercolor
// the popup disappears after a delay (5s) or when clicked next to the popup
export class AlertPopup {
    timer_id = null;
    constructor(status = "ok", msg, delay = 5000) {
        if (window["bootbox"]) {
            if (this.timer_id !== null) clearTimeout(timer.timer_id);
            this.timer_id = setTimeout(() => this.dialog.modal("hide"), delay);
            this.dialog = bootbox.dialog({
                backdrop: true,
                message: msg,
                closeButton: false,
                className: status === "ok" ? "alert-popup timed-popup-ok" : status === "warning" ? "alert-popup timed-popup-warning" : "alert-popup timed-popup-error"
            })
        } else {
            alert(msg)
        }
    }
}

// popup with a formio-layout
// standard are the submit, cancel and clear events returned.  events is a list of additional events
export class FormioPopup {
    formio_handle = null;

    async init({template = null, events = [], cb = null, defaults = null, opaque = null, width = null}) {
        if (template === null) return false
        const form_options = {sanitizeConfig: {addTags: ['iframe'], addAttr: ['allow'], ALLOWED_TAGS: ['iframe'], ALLOWED_ATTR: ['allow']},/* noAlerts: true,*/}
        const overlay = document.createElement("div");
        overlay.classList.add("overlay");
        const popup = document.createElement("div");
        overlay.appendChild(popup)
        popup.classList.add("popup");
        document.querySelector("body").appendChild(overlay);
        if (width)
            popup.style.width = width;
        this.formio_handle = await Formio.createForm(popup, template, form_options)
        if (defaults != null) {
            for (const [k, v] of Object.entries(defaults)) {
                const c = this.formio_handle.getComponent(k)
                if (c !== undefined && c !== null) {
                    if (c.type === "select") {
                        if ("options" in v) c.component.data.json = v.options;
                        if ("default" in v) c.setValue(v.default);
                    } else c.setValue(v);
                }
            }
        }
        if (cb !== null) {
            this.formio_handle.on('submit', async submitted => {
                cb('submit', opaque, submitted.data);
                overlay.remove()
            });
            this.formio_handle.on('cancel', async () => {
                cb('cancel', opaque)
                overlay.remove()
            });
            this.formio_handle.on('clear', async () => {
                cb('clear', opaque)
                overlay.remove()
            });
            for (const event of events) {
                this.formio_handle.on(event, data => cb(event, opaque, data));
            }
        }
        return true
    }

    set_value = (key, value) => {
        const c = this.formio_handle.getComponent(key)
        if (c !== undefined && c !== null) setTimeout(() => {
            c.setValue(value);
            c.redraw();
            }, 500);
    }

    get_value = (key) => {
        const c = this.formio_handle.getComponent(key)
        if (c !== undefined && c !== null) return c.getValue();
    }

    // I have no clue how to set the options and default value of a select component.  Below is the result of trial and error
    set_options = (key, options, default_value = null) => {
        const c = this.formio_handle.getComponent(key)
        if (c !== undefined && c !== null) {
            setTimeout(() => {
                c.component.data.json = options
                c.redraw();
            }, 500);
        }
    }

}
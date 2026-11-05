import {datatables_init, datatable_row_data_from_id, datatable_reload_table} from "../datatables/dt.js";
import {fetch_get, fetch_update} from "../common/common.js";
import {AlertPopup} from "../common/popup.js";

let meta = null;

const html_escape = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

const send_invoice_message = async incident => {
    const defaults = await fetch_get("incident.warranty_message", {id: incident.id});
    if (!defaults || defaults.status === "error") return false;
    const recipients = defaults.recipients.map(recipient => `<label class="d-block"><input type="checkbox" class="invoice-recipient" value="${html_escape(recipient.value)}" checked> ${html_escape(recipient.label)}</label>`).join("");
    let sent = false;
    let sending = false;
    return new Promise(resolve => bootbox.dialog({
        title: defaults.message_subject,
        size: "xl",
        scrollable: true,
        message: `<div class="invoice-message-content"><div class="invoice-message-recipients">${recipients}</div>
            <div class="form-group"><label for="invoice-extra-recipients">Extra e-mailadressen (gescheiden door komma's)</label><input id="invoice-extra-recipients" class="form-control" type="text"></div>
            <div class="form-group"><label for="invoice-subject">Onderwerp</label><input id="invoice-subject" class="form-control" type="text"></div>
            <div class="form-group"><label for="invoice-body">Bericht</label><div id="invoice-body" contenteditable="true" style="min-height:240px;max-height:50vh;overflow:auto;padding:10px;border:1px solid #ced4da"></div></div></div>`,
        buttons: {
            confirm: {label: "Verzenden", className: "btn-primary", callback: () => false},
            cancel: {label: "Annuleer", className: "btn-secondary"}
        },
        onShown: () => {
            const visible_modals = document.querySelectorAll(".bootbox.modal.show");
            const modal = visible_modals[visible_modals.length - 1];
            modal?.querySelector(".modal-dialog")?.classList.add("modal-dialog-scrollable");
            document.getElementById("invoice-subject").value = defaults.message_subject || "";
            document.getElementById("invoice-body").innerHTML = defaults.message_content || "";
            const button = modal?.querySelector(".bootbox-accept");
            button?.addEventListener("click", async () => {
                if (sending) return;
                sending = true;
                button.disabled = true;
                try {
                    const response = await fetch(Flask.url_for("incident.warranty_message"), {method: "POST", body: JSON.stringify({
                        id: incident.id,
                        recipients: [...modal.querySelectorAll(".invoice-recipient:checked")].map(input => input.value),
                        additional_recipients: document.getElementById("invoice-extra-recipients").value.split(",").map(value => value.trim()).filter(Boolean),
                        message_subject: document.getElementById("invoice-subject").value,
                        message_content: document.getElementById("invoice-body").innerHTML
                    })});
                    const result = await response.json();
                    if (!response.ok || result.status !== "ok") {
                        new AlertPopup("error", result.msg || "E-mail kon niet worden verstuurd");
                        $(modal).modal("hide");
                        return;
                    }
                    sent = true;
                    new AlertPopup("ok", result.msg);
                    $(modal).modal("hide");
                } catch (error) {
                    new AlertPopup("error", "E-mail kon niet worden verstuurd");
                    $(modal).modal("hide");
                }
            });
        },
        onHidden: () => resolve(sent)
    }));
};

const set_invoice_approved = async incident_id => {
    const incident = datatable_row_data_from_id(incident_id);
    const previous_state = incident.warranty_state;
    const changed = await fetch_update("incident.incident", {
        id: incident.id,
        incident_state: incident.incident_state,
        incident_type: incident.incident_type,
        info: incident.info || "",
        warranty_state: meta.warranty.invoice,
        warranty_cost: incident.warranty_cost ?? 0
    });
    if (!changed) return;
    const updated = {...incident, warranty_state: meta.warranty.invoice};
    const sent = await send_invoice_message(updated);
    if (!sent) await fetch_update("incident.warranty_state", {id: incident.id, warranty_state: previous_state});
    datatable_reload_table();
};

$(document).ready(async () => {
    meta = await fetch_get("incident.meta");
    if (!meta) return;
    const warranty_states = meta.option.warranty_state.filter(state => state.value !== meta.warranty.none);
    const filter_menu_items = [
        {type: "select", id: "warranty-state", label: "Garantie", options: [{value: "all", label: "Alles"}, ...warranty_states], default: "all", persistent: true},
        {type: "checkbox", id: "include-invoice-approved", label: "Factuur goedgekeurd tonen?", default: false, persistent: true}
    ];
    const context_menu_items = [{type: "item", label: meta.label.incident_state[meta.warranty.invoice], iconscout: "envelope", cb: ids => {
        if (ids.length !== 1) {
            new AlertPopup("warning", "Selecteer één incident");
            return;
        }
        set_invoice_approved(ids[0]);
    }}];
    datatables_init({filter_menu_items, context_menu_items});
});

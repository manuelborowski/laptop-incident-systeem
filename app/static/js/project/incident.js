import { datatable_reload_table, datatable_row_data_from_target, datatables_init} from "../datatables/dt.js";
import {fetch_get, fetch_post, fetch_update, form_default_set, form_populate} from "../common/common.js";
import {badge_raw2hex} from "../common/rfid.js";
import {AlertPopup} from "../common/popup.js";
import {IncidentRepair} from "../forms/incident_repair.js";
import {autologout_disable, autologout_enable} from "../base.js";
import {IncidentGone} from "../forms/incident_gone.js";

const meta = await fetch_get("incident.meta")

const __repair_form = async (incident = null, history = "") => {

    let repair = null;
    const title = incident ? "Herstelling aanpassen (<span style='color:orangered;'>verplichte velden</span>)" : "Nieuwe herstelling (<span style='color:orangered;'>verplichte velden</span>)";
    const form = await fetch_get("incident.form", {form: "repair"});
    form.template = form.template.replace("{{ form_css_file }}", "<link href=\"static/css/form.css\" rel=\"stylesheet\">\n");
    let bootbox_dialog = null;
    if (form) {
        let owner_field = null;
        bootbox_dialog = bootbox.dialog({
            title,
            size: "xl",
            message: form.template,
            buttons: {
                confirm: {label: "Bewaar", className: "btn-primary", callback: () => false},
                cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                        if (incident) datatable_reload_table();
                        autologout_enable();
                    }
                },
            },
            onShown: async () => {
                repair = new IncidentRepair({meta, incident, history, dropdown_parent: $(".bootbox")});
                await repair.display()
                if (current_user.level < 3) document.querySelector(".bootbox-accept").hidden = true; // regular users cannot save changes
                autologout_disable();
            },
        });

        // Confirm button pushed
        document.querySelector(".bootbox .btn-primary").addEventListener("click", async e => {
            if (await repair.save()) {
                datatable_reload_table();
                if (bootbox_dialog) bootbox_dialog.modal("hide");
                autologout_enable();
            }
        });
    }
}

const __loan_form = async (incident = null, history = null) => {
    const incident_update = incident !== null;
    const form = await fetch_get("incident.form", {form: "loan"});
    if (form) {
        let owner_field = null;
        bootbox.dialog({
            title: "Uitlenen van laptop en/of lader",
            size: "xl",
            message: form.template,
            buttons: {
                confirm: {
                    label: "Bewaar",
                    className: "btn-primary",
                    callback: async () => {
                        const form_data = new FormData(document.getElementById("loan-form"));
                        const data = Object.fromEntries(form_data)
                        // checkboxes are present only when selected and have the value "on" => convert
                        document.getElementById("loan-form").querySelectorAll("input[type='checkbox']").forEach(c => data[c.name] = c.name in data)
                        data.incident_type = data.long_loan ? "longloan" : "shortloan";
                        if (incident_update) {
                            data.id = incident.id;
                            await fetch_update("incident.incident", data);
                        } else {
                            const owner_data = owner_field.select2("data")[0];
                            data.laptop_owner_name = owner_data.text;
                            data.category = "loan";
                            [data.laptop_type, data.laptop_owner_id] = data.laptop_owner_id.split("-");
                            data.laptop_name = "NVT";
                            await fetch_post("incident.incident", data);
                        }
                        datatable_reload_table();
                        autologout_enable();
                    }
                },
                cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                        if (incident_update) datatable_reload_table();
                        autologout_enable();
                    }
                },
            },
            onShown: async () => {
                autologout_disable();
                owner_field = $("#owner-field");

                // Scan laptop owner badge
                document.getElementById("owner-badge-scan").addEventListener("click", (e) => {
                    e.preventDefault();
                    bootbox.prompt({
                        title: "Scan de badge van de eigenaar",
                        callback: async res => {
                            if (res !== null) {
                                const [valid_code, code] = badge_raw2hex(res);
                                if (valid_code) {
                                    let loaners = await fetch_get("student.student", {filters: `rfid$=$${code}`, fields: "leerlingnummer"});
                                    if (loaners && loaners.length > 0) {
                                        owner_field.val("leerling-" + loaners[0].leerlingnummer).trigger("change");
                                        return true
                                    } else {
                                        const loaners = await fetch_get("staff.staff", {filters: `rfid$=$${code}`, fields: "code"});
                                        if (loaners && loaners.length > 0) {
                                            owner_field.val("personeel-" + loaners[0].code).trigger("change");
                                            return true
                                        }
                                    }
                                }
                                new AlertPopup("warning", "Ongeldige badge");
                            }
                        }
                    })
                });

                // Scan spare badge
                document.getElementById("spare-badge-scan").addEventListener("click", (e) => {
                    e.preventDefault();
                    bootbox.prompt({
                        title: "Scan de badge van de reservelaptop",
                        callback: async res => {
                            if (res !== null) {
                                const spare_field = document.getElementById("spare-field")
                                const [valid_code, code] = badge_raw2hex(res);
                                if (valid_code) {
                                    const spares = await fetch_get("spare.spare", {filters: `rfid$=$${code}`, fields: "label"});
                                    if (spares && spares.length > 0) spare_field.value = spares[0].label;
                                } else {
                                    spare_field.value = code;
                                }
                            }
                        }
                    })
                });

                // set default values
                if (incident_update) {
                    if (history !== "") {
                        const previous_info_field = document.getElementById("info_previous");
                        previous_info_field.innerHTML = history;
                        previous_info_field.closest(".form-row").hidden = false;
                    }
                    incident.info = "";
                    meta.option.laptop_owner_id = [{value: incident.laptop_owner_id, label: incident.laptop_owner_name}];
                    incident.long_loan = incident.incident_type === "longloan";
                    incident.location = incident.current_location;
                    await form_populate(incident, meta);
                } else {
                    const students = await fetch_get("student.student", {fields: "naam,voornaam,klasgroepcode,leerlingnummer"})
                    const student_data = students ? students.map(e => ({id: "leerling-" + e.leerlingnummer, text: `${e.naam} ${e.voornaam} ${e.klasgroepcode}`})) : []
                    const staff = await fetch_get("staff.staff", {fields: "naam,voornaam,code"})
                    const staff_data = staff ? staff.map(e => ({id: "personeel-" + e.code, text: `${e.naam} ${e.voornaam}`})) : []
                    const data = student_data.concat(staff_data);
                    if (owner_field.hasClass("select2-hidden-accessible")) await owner_field.empty().select2('destroy').trigger("change")
                    await owner_field.select2({dropdownParent: $(".bootbox"), data, width: "600px"});
                    if (data.length > 0) await owner_field.val(data[0].id).trigger("change"); // use await to make sure the select2 is done initializing
                    await form_populate(Object.assign(meta.default, {category: "loan", incident_state: "first", incident_type: "shortloan"}), meta);
                }
            },
        });
    }
}

const __gone_form = async (incident = null, history = "") => {
    let gone = null;
    const form = await fetch_get("incident.form", {form: "gone"});
    form.template = form.template.replace("{{ form_css_file }}", "<link href=\"static/css/form.css\" rel=\"stylesheet\">\n");
    let bootbox_dialog = null;
    if (form) {
        let owner_field = null;
        bootbox_dialog = bootbox.dialog({
            title: `Laptop is verloren of gestolen <a target='_blank' href='${meta.wikijs.gone_dialog}'>(help)</a>`,
            size: "xl",
            message: form.template,
            buttons: {
                confirm: {label: "Bewaar", className: "btn-primary", callback: () => false},
                cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                        if (incident) datatable_reload_table();
                        autologout_enable();
                    }
                },
            },
            onShown: async () => {
                gone = new IncidentGone({meta, incident, history, dropdown_parent: $(".bootbox")});
                await gone.display()
                if (current_user.level < 3) document.querySelector(".bootbox-accept").hidden = true; // regular users cannot save changes
                autologout_disable();
            },
        });

        // Confirm button pushed
        document.querySelector(".bootbox .btn-primary").addEventListener("click", async e => {
            if (await gone.save()) {
                datatable_reload_table();
                if (bootbox_dialog) bootbox_dialog.modal("hide");
                autologout_enable();
            }
        });
    }
}

const __return_form = async (incident = null, history = null) => {
    const incident_update = incident !== null;
    const form = await fetch_get("incident.form", {form: "return"});
    if (form) {
        let owner_field = null;
        bootbox.dialog({
            title: "Binnenbrengen van laptop",
            size: "xl",
            message: form.template,
            buttons: {
                confirm: {
                    label: "Bewaar",
                    className: "btn-primary",
                    callback: async () => {
                        owner_field = $("#owner-field");
                        const laptop_field = document.getElementById("laptop-field");
                        const form_data = new FormData(document.getElementById("incident-form"));
                        const data = Object.fromEntries(form_data)
                        // checkboxes are present only when selected and have the value "on" => convert
                        document.getElementById("incident-form").querySelectorAll("input[type='checkbox']").forEach(c => data[c.name] = c.name in data)
                        if (incident_update) {
                            data.id = incident.id;
                            if (incident.incident_state === "prepared") {
                                const owner_data = owner_field.select2("data")[0];
                                data.laptop_owner_name = owner_data.text;
                                data.laptop_name = laptop_field.options[laptop_field.selectedIndex].innerHTML;
                                data.incident_state = "expecting"
                                data.info = data.info.split("+").slice(-2).join("; ");

                            }
                            await fetch_update("incident.incident", data);
                        } else {
                            const owner_data = owner_field.select2("data")[0];
                            data.laptop_owner_name = owner_data.text;
                            data.category = "return";
                            [data.laptop_type, data.laptop_owner_id] = data.laptop_owner_id.split("-");
                            const laptop_select_option = document.getElementById("laptop-field").selectedOptions[0];
                            data.laptop_name = laptop_select_option ? laptop_select_option.label : "";
                            data.incident_state = "expecting";
                            await fetch_post("incident.incident", data);
                        }
                        datatable_reload_table();
                        autologout_enable();
                    }
                },
                cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                        if (incident_update) datatable_reload_table();
                        autologout_enable();
                    }
                },
            },
            onShown: async () => {
                autologout_disable();
                owner_field = $("#owner-field");
                const laptop_field = document.getElementById("laptop-field");
                const lis_type_field = document.getElementById("lis-type-field");
                const incident_state_field = document.getElementById("incident-state-field");

                // when the lis-type changes, the possible states change accordingly.
                lis_type_field.addEventListener("change", async e => {
                    const new_state = (e.target.value === "school" && incident_state_field.value === "signpost") ? "expecting" : incident_state_field.value;
                    await form_populate({incident_type: e.target.value, incident_state: new_state}, meta);
                })

                // when the owner field changes, get the associated laptops and populate the laptop field
                owner_field.on('change', async e => {
                    const [laptop_type, laptop_owner_id] = e.target.value.split("-");
                    if (laptop_owner_id && laptop_owner_id !== "") {
                        const devices = await fetch_get("incident.laptop", {type: laptop_type, id: laptop_owner_id});
                        if (devices) {
                            laptop_field.innerHTML = "";
                            for (const device of devices) {
                                const label_list = [...new Set([device.m4s_csu_label, device.m4s_signpost_label, device.device_name])].filter(e => e !== null);
                                const label = label_list.join(" / ");
                                // add an option with the received name and class
                                laptop_field.add(new Option(label, device.serial_number, device.active, device.active));
                            }
                        }
                    }
                });

                // set default values
                if (incident_update) {
                    if (history !== "") {
                        const previous_info_field = document.getElementById("info_previous");
                        previous_info_field.innerHTML = history;
                        previous_info_field.closest(".form-row").hidden = false;
                    }
                    document.querySelector(".prepared-visible").hidden = incident.incident_state !== "prepared";
                    document.querySelector(".prepared-hidden").hidden = incident.incident_state === "prepared";
                    if (incident.incident_state === "prepared") {
                        const [naam, voornaam, klasgroepcode, laptop] = incident.info.split("+");
                        let students = await fetch_get("student.fuzzy", {number: 5, fields: `voornaam=${voornaam},naam=${naam},klasgroepcode=${klasgroepcode}`}) || [];
                        const students2 = await fetch_get("student.fuzzy", {number: 5, fields: `voornaam=${naam},naam=${voornaam},klasgroepcode=${klasgroepcode}`}) || [];
                        students = students.concat(students2);
                        if (students) {
                            students.sort((a, b) => b.fuzzy_score - a.fuzzy_score);
                            const data = students ? students.map(e => ({id: "leerling-" + e.leerlingnummer, text: `${e.naam} ${e.voornaam} ${e.klasgroepcode}`})) : []
                            if (owner_field.hasClass("select2-hidden-accessible")) await owner_field.empty().select2('destroy').trigger("change")
                            await owner_field.select2({dropdownParent: $(".bootbox"), data, width: "600px"});
                            if (data.length > 0) await owner_field.val(data[0].id).trigger("change"); // use await to make sure the select2 is done initializing
                        }
                    }
                    incident.location = incident.current_location;
                    // default setting of the owner-id field is taken care of a few lines here above.  The field takes the form 'leerling-83342' while the laptop_owner_id is just '83342'
                    delete incident.laptop_owner_id;
                    await form_populate(incident, meta);
                } else { // new return
                    document.querySelector(".prepared-hidden").hidden = true;
                    const students = await fetch_get("student.student", {fields: "naam,voornaam,klasgroepcode,leerlingnummer"})
                    const student_data = students ? students.map(e => ({id: "leerling-" + e.leerlingnummer, text: `${e.naam} ${e.voornaam} ${e.klasgroepcode}`})) : []
                    const staff = await fetch_get("staff.staff", {fields: "naam,voornaam,code"})
                    const staff_data = staff ? staff.map(e => ({id: "personeel-" + e.code, text: `${e.naam} ${e.voornaam}`})) : []
                    const data = student_data.concat(staff_data);
                    if (owner_field.hasClass("select2-hidden-accessible")) await owner_field.empty().select2('destroy').trigger("change")
                    await owner_field.select2({dropdownParent: $(".bootbox"), data, width: "600px"});
                    if (data.length > 0) await owner_field.val(data[0].id).trigger("change"); // use await to make sure the select2 is done initializing
                    await form_populate(Object.assign(meta.default, {category: "return", incident_state: "prepared", incident_type: "school"}), meta);
                }
            },
        });
    }
}

const __setting_form = async () => {
    const form = await fetch_get("incident.form", {form: "setting"});
    if (form) {
        bootbox.dialog({
            title: "Instellingen",
            message: form.template,
            buttons: {
                confirm: {
                    label: "Bewaar",
                    className: "btn-primary",
                    callback: async () => {
                        const form_data = new FormData(document.getElementById("setting-form"));
                        const data = Object.fromEntries(form_data)
                        // checkboxes are present only when selected and have the value "on" => convert
                        document.getElementById("setting-form").querySelectorAll("input[type='checkbox']").forEach(c => data[c.name] = c.name in data)
                        await fetch_post("incident.location", {default: data.home_location})
                        let user_data = {"username": current_user.username};
                        if (data.rfid !=="") user_data["rfid"] = data.rfid;
                        if (data.pin !=="") user_data["pin"] = data.pin;
                        if ("pin" in user_data || "rfid" in user_data) await fetch_update("user.user", user_data);
                        meta.default.location = data.home_location;
                        __update_toolbar_fields();
                        datatable_reload_table();
                        autologout_enable();
                    }
                },
                cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                        autologout_enable();
                    }
                },
            },
            onShown: async () => {
                autologout_disable();
                const new_login_url_btn = document.getElementById("new-login-url-btn");
                const new_login_url_chk = document.getElementById("new-login-url-chk");
                const rfid_field = document.getElementById("rfid-field");

                // Scan user badge
                document.getElementById("user-badge-scan").addEventListener("click", (e) => {
                    e.preventDefault();
                    bootbox.prompt({
                        title: "Scan je badge",
                        callback: async res => {
                            if (res !== null) {
                                const [valid_code, code] = badge_raw2hex(res);
                                rfid_field.value = code;
                            }
                        }
                    })
                });


                // generate new QR code
                new_login_url_btn.addEventListener("click", async (e) => {
                    e.preventDefault();
                    const resp = await fetch_get("incident.qr", {new: true});
                    if (resp) document.getElementById("login-url-img").src = `data:image/png;base64,${resp.qr}`;
                });
                new_login_url_chk.addEventListener("click", e => new_login_url_btn.disabled = !e.target.checked);
                const defaults = {home_location: meta.default.location};
                form_populate(defaults, meta);
                const resp = await fetch_get("incident.qr", {new: false});
                if (resp) document.getElementById("login-url-img").src = `data:image/png;base64,${resp.qr}`;
            },
        });
    }
}

const __history_form = async (ids) => {
    const id = ids[0];
    const form = await fetch_get("incident.form", {form: "history"});
    if (form) {
        bootbox.dialog({
            title: "Incident historiek",
            size: "xl",
            message: form.template,
            buttons: {
                cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                    }
                },
            },
            onShown: async () => {
                const incidents = await fetch_get("incident.incident", {filters: `id$=$${id}`});
                const incident = incidents && incidents.length > 0 ? incidents[0] : null;
                const histories = await fetch_get("history.history", {filters: `incident_id$=$${id}`, order_by: "-id"});
                const history_table = document.querySelector("#history-table");
                for (const h of histories) {
                    let tr = "<tr>";
                    for (const e of ["time", "current_incident_owner", "priority", "incident_state", "current_location", "info", "incident_type"]) {
                        let val = h[e];
                        if (e === "incident_state") val = meta.label.incident_state[val];
                        if (e === "current_location") val = meta.label.location[val];
                        if (val === true) val = "&#10003;"
                        if (val === false) val = "";
                        tr += `<td>${val}</td>`
                    }
                    tr += "</tr>";
                    history_table.innerHTML += tr;
                }
                if (incident.m4s_reference !== "") {
                    const m4s_reference_row = document.getElementById("m4s-reference-field");
                    m4s_reference_row.hidden = false;
                    const m4s_reference_a = m4s_reference_row.querySelector("a");
                    m4s_reference_a.innerHTML = incident.m4s_reference;
                    m4s_reference_a.href = `https://byod.signpost.be/incidents/${incident.m4s_guid}`;
                }
                await form_populate(incident);
            },
        });
    }
}

const __send_message = async (ids) => {
    let message_content_quill = null;
    const form = await fetch_get("incident.form", {form: "message"});
    if (form) {
        bootbox.dialog({
            title: "Bericht sturen",
            message: form.template,
            buttons: {
                confirm: {
                    label: "Verzenden",
                    className: "btn-primary",
                    callback: async () => {
                        const ss_message_form = document.getElementById("ss-message-form")
                        const form_data = new FormData(ss_message_form);
                        const data = Object.fromEntries(form_data)
                        // checkboxes are present only when selected and have the value "on" => convert
                        ss_message_form.querySelectorAll("input[type='checkbox']").forEach(c => data[c.name] = c.name in data)
                        data.id = ids[0];
                        data.message_content = message_content_quill.root.innerHTML;
                        await fetch_post("incident.message", data);
                        datatable_reload_table();
                    }
                },
                cancel: {
                    label: "Annuleer", className: "btn-secondary", callback: async () => {
                    }
                },
            },
            onShown: async () => {
                const default_message_field = document.getElementById("default-message-chk");
                const message_content_field = document.getElementById("message-content");
                const message_subject_field = document.getElementById("message-subject");
                message_content_quill = new Quill(message_content_field, {theme: 'snow'});
                const defaults = await fetch_get("incident.message", {"id": ids[0]})
                if (defaults) {
                    await message_content_quill.clipboard.dangerouslyPasteHTML(defaults.message_content);
                    message_subject_field.value = defaults.message_subject;
                    default_message_field.checked = true;
                }
                default_message_field.addEventListener("click", async e => {
                    if (e.target.checked) {
                        await message_content_quill.clipboard.dangerouslyPasteHTML(defaults.message_content);
                        message_subject_field.value = defaults.message_subject;
                    } else {
                        await message_content_quill.clipboard.dangerouslyPasteHTML("");
                        message_subject_field.value = "";
                    }
                });

            },
        });
    }
}

const __update_toolbar_fields = () => {
    document.getElementById("default-location").value = meta.label.location[meta.default.location];
}

const button_menu_items = [
    {
        type: 'button',
        id: 'repair-new',
        label: 'Nieuwe herstelling',
        cb: () => __repair_form()
    },
    {
        type: 'button',
        id: 'laptoploan-new',
        label: 'Laptop uitlenen',
        cb: () => __loan_form()
    },
    {
        type: 'button',
        id: 'return-new',
        label: 'Laptop retourneren',
        cb: () => __return_form()
    },
    {
        type: 'button',
        id: 'laptopgone-new',
        label: 'Laptop verdwenen',
        cb: () => __gone_form()
    },
    {
        type: 'text',
        id: 'default-location',
        label: 'Locatie',
        align: "right",
        width: "15ch"
    },
    {
        type: 'button',
        id: 'settings',
        label: 'Instellingen',
        cb: () => __setting_form(),
    },
]

const context_menu_items = [
    {type: "item", label: 'Historiek', iconscout: 'history', cb: __history_form},
]

const __filter_scan_lis_badge = () => {
    bootbox.prompt({
        title: "Scan de LIS badge",
        callback: async res => {
            if (res !== null) {
                const [valid_code, code] = badge_raw2hex(res);
                let lis_id = null;
                if (valid_code) {
                    const badges = await fetch_get("lisbadge.lisbadge", {filters: `rfid$=$${code}`})
                    if (badges && badges.length > 0) lis_id = badges[0].id;
                } else {
                    lis_id = code;  // it is assumed a valid lis code is entered
                }

                const dt_search = document.querySelector(".dt-search .dt-input");
                if (dt_search) {
                    dt_search.value = lis_id;
                    dt_search.dispatchEvent(new Event("input"));
                }
            }
        }
    });
}

const filter_menu_items = [
    {
        type: 'select',
        id: 'incident-owner-id',
        label: 'Hersteller',
        persistent: true
    },
    {
        type: 'select',
        id: 'location',
        label: 'Locatie',
        persistent: true
    },
    {
        type: 'select',
        id: 'incident-state',
        label: 'Status',
        persistent: true
    },
    {
        type: 'checkbox',
        id: 'incident-state-closed',
        label: 'Afgehandeld?',
        default: false,
        persistent: true
    },
    {
        type: 'checkbox',
        id: 'incident-state-cancelled',
        label: 'Geannuleerd?',
        default: false,
        persistent: true
    },
    {
        type: 'select',
        id: 'incident-type',
        label: 'Type',
        persistent: true
    },
]

const __table_loaded = () => {
    document.querySelectorAll(".btn-incident-update").forEach(s => s.addEventListener("click", async e => {
        const row = datatable_row_data_from_target(e);
        const incidents = await fetch_get("incident.incident", {filters: `id$=$${row.id}`});
        const incident = incidents && incidents.length > 0 ? incidents[0] : null;
        const histories = await fetch_get("history.history", {filters: `incident_id$=$${row.id}`});
        const history = histories.map(e => e.info).filter(e => e !== "").join("<br>");
        if (incident.category === "repair") {
            await __repair_form(incident, history);
        } else if (incident.category === "return") {
            await __return_form(incident, history);
        } else if (incident.category === "gone") {
            await __gone_form(incident, history);
        } else {
            await __loan_form(incident, history)
        }
    }));
    document.querySelectorAll(".btn-show-history").forEach(s => s.addEventListener("click", async e => {
        const row = datatable_row_data_from_target(e);
        await __history_form([row.id]);
    }));
    document.querySelectorAll(".btn-send-message").forEach(s => s.addEventListener("click", async e => {
        const row = datatable_row_data_from_target(e);
        await __send_message([row.id])
    }));
    document.querySelectorAll(".btn-incident-close").forEach(s => s.addEventListener("click", async e => {
        const row = datatable_row_data_from_target(e);
        await fetch_update("incident.incident", {id: row.id, incident_state: "closed", info: "Incident gesloten"});
        datatable_reload_table();
    }));
}

const __row_created = (row, data, data_index, cells) => {
    if (data.flags && data.flags.split(",").includes("state-timeout")) {
        $(row).attr("style", `background-color: #ffa5006b;`);
    }
}

$(document).ready(async () => {
    let owners = await fetch_get("incident.incident", {fields: "home_incident_owner"});
    owners = owners ? [...new Set(owners.map(e => e.home_incident_owner))] : [];
    owners = owners.map(e => ({label: e, value: e}));
    const incident_owner_options = [{label: current_user.username, value: current_user.username}, {label: "Iedereen", value: "all"}].concat(owners);
    const state_options = [{label: "Alles", value: "all"}].concat(meta.option.incident_state);
    const type_options = [{label: "Alles", value: "all"}].concat(meta.option.incident_type);
    const filtered_location = meta.option.location.filter(i => i.value !== meta.default.location);
    const location_options = [{label: meta.label.location[meta.default.location], value: meta.default.location}, {label: "Alle", value: "all"}].concat(filtered_location);
    filter_menu_items.filter((e, i, a) => {
        if (e.id === "incident-owner-id") {
            a[i].options = incident_owner_options;
            a[i].default = "all";
            return true
        }
        if (e.id === "incident-type") {
            a[i].options = type_options;
            a[i].default = "all";
            return true
        }
        if (e.id === "incident-state") {
            a[i].options = state_options;
            a[i].default = "all";
            return true
        }
        if (e.id === "location") {
            a[i].options = location_options;
            a[i].default = meta.default.location;
            return true
        }
        return false;
    });
    const callbacks = {table_loaded: __table_loaded, created_row: __row_created};
    datatables_init({button_menu_items, context_menu_items, filter_menu_items, callbacks});
    __update_toolbar_fields();
    if (current_user.level < 3) document.querySelector(".button-menu-placeholder").hidden = true;
});

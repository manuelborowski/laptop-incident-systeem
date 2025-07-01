import {badge_raw2hex} from "../common/rfid.js";
import {busy_indication_off, busy_indication_on, fetch_delete, fetch_get, fetch_post, fetch_update, form_populate} from "../common/common.js";
import {AlertPopup} from "../common/popup.js";
import {qr_decode} from "../common/qr.js";

export class IncidentGone {
    constructor({meta = null, incident = null, history = "", dropdown_parent = null, callbacks = {}}) {
        this.incident_update = incident !== null;
        this.incident = incident;
        this.history = history;
        this.meta = meta;
        this.dropdown_parent = dropdown_parent;
        this.callbacks = callbacks;
        this.attachments = [];
        this.attachments_to_delete = [];
    }

    ATTACHMENT_LINE_TEMPLATE = (file) => {
        let line = `<div class="form-element group-spare-laptop">
                    <input type="checkbox" data-id=${file.name.replaceAll(" ", "")} style="padding:2px;line-height:1;">M4S?&nbsp;
                    <a type="button" class="btn-attachment-remove btn btn-danger" data-id=${file.name.replaceAll(" ", "")} style="padding:2px;line-height:1;">
                    <i class="fa-solid fa-xmark" title="Bijlage verwijderen"></i></a>&nbsp;`
        if ("id" in file) {
            line += `<a class="attachment-view">${file.name}</a><br><div>`;
        } else {
            line += file.name + "<br><div>";
        }
        return line
    }

    display = async () => {
        this.location_field = document.getElementById("location-field");
        this.incident_state_field = document.getElementById("incident-state-field");
        this.lis_type_field = document.getElementById("lis-type-field");
        this.info_field = document.getElementById("info-field");
        this.spare_field = document.getElementById("spare-field");
        this.m4s_category_field = document.getElementById("m4s-category-field");
        this.m4s_problem_type_guid_field = document.getElementById("m4s-problem-type-guid-field");
        this.owner_field = $("#owner-field");
        this.attachment_list = document.getElementById("attachment-list");

        const __attachment_add_view_event_listener = () => {
            this.attachment_list.querySelectorAll(".attachment-view").forEach(a => a.addEventListener("click", async e => {
                busy_indication_on();
                const filename = e.target.innerHTML;
                const attachment = this.attachments.find(a => a.name === filename);
                const data = await fetch_get("incident.attachment", {id: attachment.id});
                if (attachment.type.includes("image")) {
                    const base64_image = `data:${attachment.type};base64, ` + data.data.file;
                    const new_tab = window.open();
                    if (new_tab) {
                        new_tab.document.write(`<img src="${base64_image}" alt="Base64 Image">`);
                        new_tab.document.write(`<title>${filename}</title>`);
                    } else {
                        alert("Popup blocked! Please allow popups for this site.");
                    }
                } else if (attachment.type.includes("video")) {
                    const new_tab = window.open();
                    if (new_tab) {
                        const base64_mp4 = `data:${attachment.type};base64, ` + data.data.file;
                        new_tab.document.write(`<title>${filename}</title>`);
                        new_tab.document.write(`
                                <html>
                                  <body style="margin:0; display:flex; justify-content:center; align-items:center; height:100vh; background-color:#000;">
                                    <video controls autoplay style="max-width:100%; max-height:100vh;">
                                      <source src="${base64_mp4}" type="${attachment.type}">
                                      Your browser does not support the video tag.
                                    </video>
                                  </body>
                                </html>
                              `);
                        new_tab.document.close();
                    } else {
                        alert("Popup blocked! Please allow popups for this site.");
                    }
                } else { // default: download
                    const linkSource = `data:application/pdf;base64,${data.data.file}`;
                    const downloadLink = document.createElement("a");
                    downloadLink.href = linkSource;
                    downloadLink.download = filename;
                    downloadLink.click();
                }
                busy_indication_off();
            }));
        }

        const __attachment_add_delete_event_listener = () => {
            this.attachment_list.querySelectorAll(".btn-attachment-remove").forEach(i => i.addEventListener("click", e => {
                    e.preventDefault();
                    const filename = e.target.closest("a").dataset.id;
                    const find_file = this.attachments.find(i => i.name.replaceAll(" ", "") === filename);
                    if (find_file && "id" in find_file) this.attachments_to_delete.push(find_file.id);
                    this.attachments = this.attachments.filter(i => i.name.replaceAll(" ", "") !== filename);
                    this.attachment_list.innerHTML = "";
                    for (const file of this.attachments) {
                        this.attachment_list.innerHTML += this.ATTACHMENT_LINE_TEMPLATE(file);
                        // if ("id" in file) {
                        //     this.attachment_list.innerHTML += `<a class="attachment-view">${file.name}</a><br>`;
                        // } else {
                        //     this.attachment_list.innerHTML += file.name + "<br>";
                        // }
                    }
                    __attachment_add_delete_event_listener();
                    __attachment_add_view_event_listener();
                })
            );
        }

        // Scan laptop owner badge
        document.getElementById("owner-badge-scan").addEventListener("click", (e) => {
            e.preventDefault();
            bootbox.prompt({
                title: "Scan de badge van de eigenaar",
                locale: "dutch",
                callback: async res => {
                    if (res !== null) {
                        const [valid_code, code] = badge_raw2hex(res);
                        if (valid_code) {
                            let loaners = await fetch_get("student.student", {filters: `rfid$=$${code}`, fields: "leerlingnummer"});
                            if (loaners && loaners.length > 0) {
                                this.owner_field.val("leerling-" + loaners[0].leerlingnummer).trigger("change");
                                return true
                            } else {
                                const loaners = await fetch_get("staff.staff", {filters: `rfid$=$${code}`, fields: "code"});
                                if (loaners && loaners.length > 0) {
                                    this.owner_field.val("personeel-" + loaners[0].code).trigger("change");
                                    return true
                                }
                            }
                        }
                        new AlertPopup("warning", "Ongeldige badge");
                    }
                }
            })
        });

        // type owner laptop label
        document.getElementById("laptop-code-input").addEventListener("click", (e) => {
            e.preventDefault();
            bootbox.prompt({
                title: "Typ het label van de laptop, schuine streep, serienummer.<br>" +
                    "Het serienummer is <b>verplicht</b> als dit incident voor Signpost is!!<br>" +
                    "bv: SPB2023-0234/LMT344FD",
                locale: "dutch",
                callback: async res => {
                    if (res !== null) {
                        const laptop_field = document.getElementById("laptop-field");
                        laptop_field.innerHTML = "";
                        const [_, serial] = res.split("/");
                        laptop_field.add(new Option(res, serial, true, true));
                    }
                }
            })
        });

        // Scan spare badge
        document.getElementById("spare-badge-scan").addEventListener("click", (e) => {
            e.preventDefault();
            if ("spare-badge-scan" in this.callbacks) {
                this.callbacks["spare-badge-scan"]();
            } else {
                bootbox.prompt({
                    title: "Scan de badge van de reservelaptop",
                    locale: "dutch",
                    callback: async res => {
                        if (res !== null) {
                            const [valid_code, code] = badge_raw2hex(res);
                            if (valid_code) {
                                const spares = await fetch_get("spare.spare", {filters: `rfid$=$${code}`, fields: "id"});
                                if (spares && spares.length > 0) this.spare_field.value = spares[0].id;
                            } else {
                                this.spare_field.value = code;
                            }
                        }
                    }
                });
            }
        });

        //upload attachments, simulate a click on the hidden file-input
        document.getElementById("upload-attachment-btn").addEventListener("click", e => {
            e.preventDefault();
            document.getElementById("attachment-field").click();
        });

        // upload attachments, called when the file select dialog closes.
        document.getElementById("attachment-field").addEventListener("change", e => {
            for (const file of e.target.files) {
                this.attachment_list.innerHTML += this.ATTACHMENT_LINE_TEMPLATE(file);
                // this.attachment_list.innerHTML += file.name + "<br>";
                this.attachments.push(file);
            }
            __attachment_add_delete_event_listener();
            __attachment_add_view_event_listener();
        });

        // when the owner field changes, get the associated laptops and populate the laptop field
        this.owner_field.on('change', async e => {
            const [laptop_type, laptop_owner_id] = e.target.value.split("-");
            const laptop_field = document.getElementById("laptop-field");
            if (laptop_owner_id && laptop_owner_id !== "") {
                const devices = await fetch_get("incident.laptop", {type: laptop_type, id: laptop_owner_id});
                if (devices) {
                    laptop_field.innerHTML = "";
                    for (const device of devices) {
                        const label_list = [...new Set([device.m4s_csu_label, device.m4s_signpost_label, device.device_name])].filter(e => e !== null);
                        const label = label_list.join(" / ");
                        const option = document.createElement("option");
                        option.innerHTML = label;
                        option.value = device.serial_number;
                        if (device.active === true) option.selected = true;
                        laptop_field.appendChild(option);
                    }
                }
            } else {
                laptop_field.innerHTML = "";
            }
        });

        // if history is available, show the history list
        if (this.history !== "") {
            const previous_info_field = document.getElementById("info_previous");
            previous_info_field.innerHTML = this.history;
            previous_info_field.closest(".form-row").hidden = false;
        }

        // set default values, create the select2 for the laptop-owners and populate with a single student/staff (update) or a list of all students and staffs
        // other default values
        if (this.incident_update) {
            this.incident.info = "";
            // set the owner-laptop value
            this.meta.option.laptop_serial = [{value: this.incident.laptop_serial, label: this.incident.laptop_name}];

            this.incident.location = this.incident.current_location;
            await form_populate(this.incident, this.meta);
            this.owner_field_options = [{id: this.incident.laptop_owner_id, text: this.incident.laptop_owner_name}];

            // Get attachments
            const attachments = await fetch_get("incident.attachment_meta", {incident_id: this.incident.id});
            if (attachments.data.length > 0) {
                this.attachments = [...attachments.data];

                for (const file of this.attachments) {
                    this.attachment_list.innerHTML += this.ATTACHMENT_LINE_TEMPLATE(file);
                    // this.attachment_list.innerHTML += `<a class="attachment-view">${file.name}</a><br>`;
                }
                __attachment_add_delete_event_listener();
                __attachment_add_view_event_listener();
            }

            document.querySelectorAll(".required").forEach(i => i.classList.toggle("required"));
        } else { // new gone
            const defaults = Object.assign(this.meta.default, {incident_state: "created", incident_type: "lost", category: "gone"}); // clear password and lis field
            await form_populate(defaults, this.meta);
            const students = await fetch_get("student.student", {fields: "naam,voornaam,klasgroepcode,leerlingnummer"})
            const student_data = students ? students.map(e => ({id: "leerling-" + e.leerlingnummer, text: `${e.naam} ${e.voornaam} ${e.klasgroepcode}`})) : []
            const staff = await fetch_get("staff.staff", {fields: "naam,voornaam,code"})
            const staff_data = staff ? staff.map(e => ({id: "personeel-" + e.code, text: `${e.naam} ${e.voornaam}`})) : []
            this.owner_field_options = [{id: "", text: "Selecteer een leerling of leerkracht"}].concat(student_data.concat(staff_data));
        }

        // select2 field has it's own way of adding options
        if (this.owner_field.hasClass("select2-hidden-accessible")) await this.owner_field.empty().select2('destroy').trigger("change")
        let select2_config = {data: this.owner_field_options, width: "resolve"};
        if (this.dropdown_parent) select2_config.dropdownParent = this.dropdown_parent;
        await this.owner_field.select2(select2_config);
    }

    save = async () => {
        busy_indication_on();
        this.owner_field = $("#owner-field");
        const form_data = new FormData(document.getElementById("gone-form"));
        const data = Object.fromEntries(form_data)
        // checkboxes are present only when selected and have the value "on" => convert
        document.getElementById("gone-form").querySelectorAll("input[type='checkbox']").forEach(c => data[c.name] = c.name in data)
        if (this.incident_update) {
            if (data.laptop_owner_id === "" || data.laptop_name === "" || data.incident_type === "stolen" && data.info === "" && this.incident.m4s_guid === null) {
                new AlertPopup("warning", "Roodgekleurde velden invullen aub.");
                busy_indication_off();
                return false
            }
            data.id = this.incident.id;
            if (data.incident_type !== "stolen") data.m4s_problem_type_guid = "";  // make sure to clear this field, else it pops up in different places
            const laptop_select_option = document.getElementById("laptop-field").selectedOptions[0];
            data.laptop_name = laptop_select_option ? laptop_select_option.label : "";
            await fetch_update("incident.incident", data);

            // check for new or deleted attachments
            if (this.attachments_to_delete.length > 0) await fetch_delete("incident.attachment", {ids: this.attachments_to_delete.join(",")})
            if (this.attachments.length > 0) {
                const data = new FormData();
                data.append("incident_id", this.incident.id);
                for (const file of this.attachments) {
                    if ("id" in file) continue; // skip, already in database
                    data.append("attachment_file", file);
                }
                if (data.has("attachment_file")) {
                    const resp1 = await fetch(Flask.url_for("incident.attachment"), {method: 'POST', body: data});
                    await resp1.json();
                }
            }

        } else {  // new gone
            const owner_data = this.owner_field.select2("data")[0];
            data.laptop_owner_name = owner_data.text;
            const laptop_select_option = document.getElementById("laptop-field").selectedOptions[0];
            data.laptop_name = laptop_select_option ? laptop_select_option.label : "";
            if (data.laptop_owner_id === "" || data.laptop_name === "") {
                new AlertPopup("warning", "Roodgekleurde velden invullen aub.");
                busy_indication_off();
                return false
            }
            [data.laptop_type, data.laptop_owner_id] = data.laptop_owner_id.split("-");
            data.category = "gone";
            data.incident_type = "lost"
            data["m4s_problem_type_guid"] = ""
            var resp = await fetch_post("incident.incident", data);
            if (this.attachments.length > 0) {
                document.getElementById("incident-id-field").value = resp.data.id;
                const data = new FormData();
                data.append("incident_id", resp.data.id);
                for (const file of this.attachments) data.append("attachment_file", file);
                const resp1 = await fetch(Flask.url_for("incident.attachment"), {method: 'POST', body: data});
                await resp1.json()
            }
            new AlertPopup(resp.data.status, resp.data.msg)
        }
        busy_indication_off();
        return true
    }
}

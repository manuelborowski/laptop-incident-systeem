import {badge_raw2hex} from "../common/rfid.js";
import {busy_indication_off, busy_indication_on, fetch_delete, fetch_get, fetch_post, fetch_update, form_populate} from "../common/common.js";
import {AlertPopup} from "../common/popup.js";

export class IncidentRepair {
    constructor({meta = null, incident = null, history = "", dropdown_parent = null, callbacks = {}}) {
        this.incident_update = incident !== null;
        this.incident = incident;
        this.history = history;
        this.meta = meta;
        this.dropdown_parent = dropdown_parent;
        this.callbacks = callbacks;
        this.__stored_password = this.incident ? this.incident.laptop_owner_password : "";
        this.attachments = [];
        this.attachments_to_delete = [];
    }

    __attachment_add_view_event_listener = () => {
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

    __attachment_add_delete_event_listener = () => {
        this.attachment_list.querySelectorAll(".btn-attachment-remove").forEach(i => i.addEventListener("click", e => {
                e.preventDefault();
                const filename = e.target.closest("a").dataset.id;
                const find_file = this.attachments.find(i => i.name.replaceAll(" ", "") === filename);
                if (find_file && "id" in find_file) this.attachments_to_delete.push(find_file.id);
                this.attachments = this.attachments.filter(i => i.name.replaceAll(" ", "") !== filename);
                // this.attachment_list.innerHTML = "";
                this.__show_attachment_list(this.attachments, true)
                // for (const file of this.attachments) {
                //     this.attachment_list.innerHTML += this.ATTACHMENT_LINE_TEMPLATE(file)
                // }
                // __attachment_add_delete_event_listener();
                // __attachment_add_view_event_listener();
                // __attachment_add_m4s_check_event_listener();
            })
        );
    }

    __attachment_add_m4s_check_event_listener = () => {
        this.attachment_list.querySelectorAll(".check-attachment-m4s").forEach(i => i.addEventListener("click", e => {
                const filename = e.target.dataset.id;
                const find_file = this.attachments.find(i => i.name.replaceAll(" ", "") === filename);
                if (find_file) {
                    if (e.target.checked) {
                        find_file.to_m4s = "YES";
                    } else {
                        delete find_file.to_m4s;
                    }
                }
            }
        ));
    }

    ATTACHMENT_LINE_TEMPLATE = (file) => {
        const in_m4s_database = "m4s_reference" in file && file.m4s_reference !== "";
        const m4s_enable = this.lis_type_field.value === "hardware";
        let line = `<div class="form-element group-spare-laptop">
                    <input type="checkbox" class="check-attachment-m4s" data-id=${file.name.replaceAll(" ", "")} style="padding:2px;line-height:1;" ${in_m4s_database ? "checked" : ""} ${(in_m4s_database || !m4s_enable) ? "disabled" : ""}>M4S?&nbsp;`
        if (!in_m4s_database) line += `<a type="button" class="btn-attachment-remove btn btn-danger" data-id=${file.name.replaceAll(" ", "")} style="padding:2px;line-height:1;" : ""}>
                    <i class="fa-solid fa-xmark" title="Bijlage verwijderen"></i></a>&nbsp;`
        if ("id" in file) {
            line += `<a class="attachment-view">${file.name}</a><br><div>`;
        } else {
            line += file.name + "<br><div>";
        }
        return line
    }

    __show_attachment_list = (list, clear_list = false) => {
        if (clear_list) this.attachment_list.innerHTML = "";
        for (const attachment of list) {
            this.attachment_list.innerHTML += this.ATTACHMENT_LINE_TEMPLATE(attachment)
        }
        this.__attachment_add_delete_event_listener();
        this.__attachment_add_view_event_listener();
        this.__attachment_add_m4s_check_event_listener();
    }

    // Depending on the incident type hide/display specific elements of the form
    __display_elements = async (incident_type) => {
        // Update harware specific fields
        document.getElementById("hardware-repair-group").hidden = incident_type !== "hardware"
        if (incident_type === "hardware") { // make sure that a valid location is displayed, and highlight if it is changed.  Make clear the info field is required
            if (!(this.incident && this.incident.m4s_guid !== null)) {
                // hardware incident, but no info or m4s error added yet
                this.info_field.parentElement.classList.add("required");
                this.m4s_category_field.parentElement.classList.add("required");
                this.m4s_problem_type_guid_field.parentElement.classList.add("required");
            }
        } else { // not a hardware incident
            this.info_field.parentElement.classList.remove("required"); // info field is not required
            this.m4s_category_field.parentElement.classList.remove("required");
            this.m4s_problem_type_guid_field.parentElement.classList.remove("required");
            this.location_field.style.background = "white";
        }
        // rebuild the list of attachments, i.e. enable or disable checkboxes
        this.__show_attachment_list(this.attachments, true);
    }

    __password_field_hide = (hide = true) => {
        const password_field = document.getElementById("password-field");
        const password_show_field = document.getElementById("password-show-field");
        if (hide) {
            password_show_field.classList.replace("fa-eye", "fa-eye-slash");
            password_field.value = "**";
            password_field.disabled = true;
        } else {
            password_show_field.classList.replace("fa-eye-slash", "fa-eye");
            password_field.disabled = false;
            password_field.value = this.__stored_password;
        }
    }

    __password_field_toggle = () => {
        const password_field = document.getElementById("password-field");
        const password_show_field = document.getElementById("password-show-field");
        if (password_show_field.classList.contains("fa-eye-slash")) {
            // hidden to visible
            this.__password_field_hide(false);

        } else {
            // visible to hidden
            this.__stored_password = password_field.value;
            this.__password_field_hide(true)
        }
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

        // Scan LIS badge
        document.getElementById("lis-badge-scan").addEventListener("click", (e) => {
            e.preventDefault();
            bootbox.prompt({
                title: "Scan de LIS badge",
                locale: "dutch",
                callback: async res => {
                    if (res !== null) {
                        const [valid_code, code] = badge_raw2hex(res);
                        if (valid_code) {
                            const badges = await fetch_get("lisbadge.lisbadge", {filters: `rfid$=$${code}`})
                            if (badges && badges.length > 0) document.getElementById("lis-badge-field").value = badges[0].id;
                        }
                    }
                }
            })
        });

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
                this.attachments.push(file);
            }
            this.__show_attachment_list(e.target.files)
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

        // Incident is for spare laptop
        document.getElementById("type-spare-laptop-chk").addEventListener("click", e => {
            document.querySelectorAll(".group-spare-laptop").forEach(i => i.hidden = e.target.checked);
            this.spare_field.parentElement.classList.toggle("required", e.target.checked);
            document.getElementById("spare-comment-field").hidden = !e.target.checked;
        });

        // if default password checked, disable the password field
        const password_field = document.getElementById("password-field");
        document.getElementById("password-default-chk").addEventListener("click", e => {
            password_field.disabled = e.target.checked;
            if (e.target.checked) bootbox.alert(`Opgelet, het paswoord wordt aangepast naar <b>${this.meta.default_password}</b>`)
        });
        const password_show_field = document.getElementById("password-show-field");
        password_show_field.addEventListener("click", e => this.__password_field_toggle());

        // if the location is updated, change the event to transition
        this.location_field.addEventListener("change", e => {
            this.incident_state_field.value = "transition";
        });

        // hardware incident specific, update m4s-id options when m4s-category has changed
        document.getElementById("m4s-category-field").addEventListener("change", (e) => {
            e.preventDefault();
            const options = this.meta.m4s[e.target.value];
            const m4s_id_field = document.getElementById("m4s-problem-type-guid-field");
            m4s_id_field.innerHTML = "";
            for (const item of options) m4s_id_field.add(new Option(item.label, item.value));
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
            // Just in case, populate the m4s category
            this.incident.m4s_category = this.meta.default.m4s_category;
            // in case of hardware incident, get the configured m4s category and guid and populate the respective fields
            for (const [category, problems] of Object.entries(this.meta.m4s)) {
                for (const problem of problems) {
                    if (problem.value === this.incident.m4s_problem_type_guid) {
                        this.incident.m4s_category = category;
                        this.meta.option.m4s_problem_type_guid = this.meta.m4s[category];
                        break;
                    }
                }
            }
            // disable the m4s category and type when the incident is not of the hardware-repair type
            document.querySelectorAll("#hardware-repair-group select").forEach(item => item.disabled = this.incident.m4s_guid !== null);
            // hide some fields when the repair concerns a spare laptop
            document.querySelectorAll(".group-spare-laptop").forEach(i => i.hidden = this.incident.laptop_type === "reserve");
            // set the owner-laptop value
            this.meta.option.laptop_serial = [{value: this.incident.laptop_serial, label: this.incident.laptop_name}];

            this.incident.location = this.incident.current_location;
            await form_populate(this.incident, this.meta);
            this.owner_field_options = [{id: this.incident.laptop_owner_id, text: this.incident.laptop_owner_name}];

            // Get attachments
            const attachments = await fetch_get("incident.attachment_meta", {incident_id: this.incident.id});
            if (attachments.data.length > 0) {
                this.attachments = [...attachments.data];
                this.__show_attachment_list(this.attachments)
            }

            document.querySelectorAll(".repair-update-hidden").forEach(i => i.hidden = true);
            document.querySelectorAll(".repair-update-visible").forEach(i => i.hidden = false);
            document.querySelectorAll(".repair-update-disabled").forEach(i => i.disabled = true);
            document.querySelectorAll(".required").forEach(i => i.classList.toggle("required"));
            this.__display_elements(this.incident.incident_type);
        } else { // new repair
            const defaults = Object.assign(this.meta.default, {incident_state: "transition", incident_type: "software", laptop_owner_password: "", category: "repair"}); // clear password and lis field
            await form_populate(defaults, this.meta);
            const students = await fetch_get("student.student", {fields: "naam,voornaam,klasgroepcode,leerlingnummer"})
            const student_data = students ? students.map(e => ({id: "leerling-" + e.leerlingnummer, text: `${e.naam} ${e.voornaam} ${e.klasgroepcode}`})) : []
            const staff = await fetch_get("staff.staff", {fields: "naam,voornaam,code"})
            const staff_data = staff ? staff.map(e => ({id: "personeel-" + e.code, text: `${e.naam} ${e.voornaam}`})) : []
            this.owner_field_options = [{id: "", text: "Selecteer een leerling of leerkracht"}].concat(student_data.concat(staff_data));
            this.__display_elements("software");
        }

        // select2 field has it's own way of adding options
        if (this.owner_field.hasClass("select2-hidden-accessible")) await this.owner_field.empty().select2('destroy').trigger("change")
        let select2_config = {data: this.owner_field_options, width: "resolve"};
        if (this.dropdown_parent) select2_config.dropdownParent = this.dropdown_parent;
        await this.owner_field.select2(select2_config);

        // default hide the password when the incident is being updated
        this.__password_field_hide(this.incident_update);

        // Type of repair changed
        this.lis_type_field.addEventListener("change", async e => {
            this.__display_elements(e.target.value);
            // Update state-select-optionss, depending on type
            form_populate({incident_state: this.meta.type[this.lis_type_field.value].incident_state[0], incident_type: this.lis_type_field.value}, this.meta);

        });
    }

    save = async () => {
        busy_indication_on();
        this.owner_field = $("#owner-field");
        const form_data = new FormData(document.getElementById("incident-form"));
        const data = Object.fromEntries(form_data)
        // checkboxes are present only when selected and have the value "on" => convert
        document.getElementById("incident-form").querySelectorAll("input[type='checkbox']").forEach(c => data[c.name] = c.name in data)
        data.laptop_owner_password = data.laptop_owner_password || this.__stored_password;
        if (this.incident_update) {
            if (data.lis_badge_id === "" || data.laptop_owner_id === "" || data.laptop_name === "" || data.incident_type === "hardware" && data.info === "" && this.incident.m4s_guid === null) {
                new AlertPopup("warning", "Roodgekleurde velden invullen aub.");
                busy_indication_off();
                return false
            }
            data.id = this.incident.id;
            if (data.incident_type !== "hardware") data.m4s_problem_type_guid = "";  // make sure to clear this field, else it pops up in different places
            const laptop_select_option = document.getElementById("laptop-field").selectedOptions[0];
            data.laptop_name = laptop_select_option ? laptop_select_option.label : "";
            await fetch_update("incident.incident", data);

            // check for new or deleted attachments
            if (this.attachments_to_delete.length > 0) await fetch_delete("incident.attachment", {ids: this.attachments_to_delete.join(",")})
            if (this.attachments.length > 0) {
                document.getElementById("incident-id-field").value = this.incident.id;
                for (const attachment of this.attachments) {
                    if (!("id" in attachment)) { //New attachment, save to db and m4s (if appropriate)
                        const data = new FormData();
                        data.append("incident_id", this.incident.id);
                        data.append("to_m4s", ("to_m4s" in attachment).toString())
                        data.append("attachment_file", attachment);
                        const resp1 = await fetch(Flask.url_for("incident.attachment"), {method: 'POST', body: data});
                        await resp1.json()
                    } else if ("to_m4s" in attachment) { // Attachment already in db, put in m4s as well
                        const data = {id: attachment.id, to_m4s: true}
                        await fetch_update("incident.attachment", data);

                    }
                }
            }
        } else {  // new incident
            let lis_badge_id_exist = [];
            if (data.lis_badge_id !== "") {
                lis_badge_id_exist = await fetch_get("incident.incident", {filters: `lis_badge_id$=$${data.lis_badge_id},incident_state$!$closed,incident_state$!$repaired,incident_state$!$cancelled`});
                if (lis_badge_id_exist.length > 0) {
                    new AlertPopup("warning", "LIS badgenummer is al in gebruik")
                    busy_indication_off();
                    return false
                }
            }
            if (document.getElementById("type-spare-laptop-chk").checked) {  // spare laptop
                data.laptop_owner_name = this.meta.label.location[data.location];
                data.laptop_owner_id = data.location;
                if (data.spare_laptop_name.includes("/")) {
                    [data.laptop_name, data.laptop_serial] = data.spare_laptop_name.split("/");
                } else {
                    data.laptop_name = data.spare_laptop_name;
                }
                data.spare_laptop_name = "NVT";

                if (data.lis_badge_id === "" || data.laptop_owner_id === "" || data.laptop_name === "" || data.incident_type === "hardware" && (data.info === "" || data.m4s_category === "none")) {
                    new AlertPopup("warning", "Roodgekleurde velden invullen aub.")
                    busy_indication_off();
                    return false
                }
                data.laptop_type = "reserve";
            } else { // regular laptop
                const owner_data = this.owner_field.select2("data")[0];
                data.laptop_owner_name = owner_data.text;
                const laptop_select_option = document.getElementById("laptop-field").selectedOptions[0];
                data.laptop_name = laptop_select_option ? laptop_select_option.label : "";
                if (data.lis_badge_id === "" || data.laptop_owner_id === "" || data.laptop_name === "" || data.incident_type === "hardware" && (data.info === "" || data.m4s_category === "none")) {
                    new AlertPopup("warning", "Roodgekleurde velden invullen aub.");
                    busy_indication_off();
                    return false
                }
                [data.laptop_type, data.laptop_owner_id] = data.laptop_owner_id.split("-");
            }
            data.category = "repair";
            data.lis_badge_id = parseInt(data.lis_badge_id);
            if (data["incident_type"] !== "hardware") data["m4s_problem_type_guid"] = ""
            const resp = await fetch_post("incident.incident", data);
            if (this.attachments.length > 0) {
                document.getElementById("incident-id-field").value = resp.data.id;
                for (const attachment of this.attachments) {
                    const data = new FormData();
                    data.append("incident_id", resp.data.id);
                    data.append("to_m4s", ("to_m4s" in attachment).toString())
                    data.append("attachment_file", attachment);
                    const resp1 = await fetch(Flask.url_for("incident.attachment"), {method: 'POST', body: data});
                    await resp1.json()
                }
            }
            new AlertPopup(resp.data.status, resp.data.msg)
        }
        busy_indication_off();
        return true
    }
}

import {fetch_get} from "../common/common.js";
import {IncidentRepair} from "../forms/incident_repair.js";

const __populate_table = (placeholder, meta) => {
    placeholder.innerHTML = "";
    const tr = document.createElement("tr");
    placeholder.appendChild(tr);
    const header = ["Tijd", "Id", "Eigenaar"];
    for (const h of header) {
        const th = document.createElement("th");
        th.innerHTML = h;
        tr.appendChild(th);
    }
    // incidents.sort((a, b) => a.laptop_owner_name < b.laptop_owner_name ? -1 : 1);
    incidents.sort((a, b) => a.time > b.time ? -1 : 1);
    const row = ["time", "lis_badge_id", "laptop_owner_name"];
    for (const incident of incidents) {
        const tr = document.createElement("tr");
        tr.dataset.id = incident.id;
        tr.style.background = meta.state[incident.incident_state].color;
        placeholder.appendChild(tr);
        for (const r of row) {
            const td = document.createElement("td");
            td.innerHTML = incident[r];
            tr.appendChild(td);
        }
    }
}

$(document).ready(async () => {
    const meta = await fetch_get("incident.meta")
    if (document.getElementById("incident-table")) {  // show the list with incidents
        const incident_table = document.getElementById("incident-table");
        const search_input = document.getElementById("search-input");
        const repair_new_btn = document.getElementById("repair-new-btn");

        __populate_table(incident_table, meta);

        // On every keypress, filter the table
        search_input.addEventListener("keyup", () => {
            const search_value = search_input.value.toLowerCase();
            for (const row of incident_table.children) {
                let found = false;
                for (const cell of row.children) {
                    if (cell.innerHTML.toLowerCase().includes(search_value)) {
                        found = true;
                        break;
                    }
                }
                row.hidden = !found;
            }
        })

        // Detailed info on a repair incident
        incident_table.addEventListener("click", async e => {
            const id = e.target.closest("tr").dataset.id;
            window.location.href = Flask.url_for("incident.m_detail", {id: id.toString()});
        })

        // New repair incident
        repair_new_btn.addEventListener("click", async () => {
            window.location.href = Flask.url_for("incident.m_detail");
        });

    } else if (document.getElementById("location-field")) { // update repair incident

        const __scan_spare_laptop = () => {
            const modal = document.getElementById("qr-modal");
            modal.style.display = "block";
            document.getElementById("qr-scanner-out").innerHTML = "";
            const qr_scanner = new QrScanner(
                document.getElementById("qr-scanner-video"),
                result => {
                    document.getElementById("qr-scanner-out").innerHTML = result.data;
                },
                {
                    highlightScanRegion: true,
                    highlightCodeOutline: true,
                }
            );
            qr_scanner.start();
            modal.addEventListener("click", () => {
                document.getElementById("spare-field").value = document.getElementById("qr-scanner-out").innerHTML;
                qr_scanner.stop();
                modal.style.display = "none";
            })
        }

        const history = histories.map(e => e.info).filter(e => e !== "").join("<br>");
        const callbacks = {"spare-badge-scan": __scan_spare_laptop};
        const repair = new IncidentRepair({meta, incident, history, callbacks});
        await repair.display();
        const cancel_btn = document.getElementById("cancel-btn");
        const save_btn = document.getElementById("save-btn");
        document.querySelectorAll(".repair-update-hidden").forEach(i => i.hidden = true);
        document.querySelectorAll(".repair-update-visible").forEach(i => i.hidden = false);

        cancel_btn.addEventListener("click", () => {
            window.location.href = Flask.url_for("incident.m_show");
        });
        // save button
        save_btn.addEventListener("click", async () => {
            await repair.save();
            window.location.href = Flask.url_for("incident.m_show");
        });

    }
});

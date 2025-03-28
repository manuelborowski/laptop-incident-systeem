import {ButtonMenu} from "./common/button_menu.js";

var menu = [
    ["incident.show", "Overzicht", 1],
    ["history.show", "Historiek", 1],
    ["spare.show", "Reserves", 3],
    ["lisbadge.show", "LIS badges", 3],
    ["user.show", "Gebruikers", 5],
    ["settings.show", "Instellingen", 5],
    [() => window.open("https://wiki.ict.campussintursula.be/nl/home/laptop-incident-systeem", "_blank"), "Help", 1],
]

export const inject_menu = new_menu => {
    menu = new_menu;
}

export const base_init = ({button_menu_items = []}) => {
    if (suppress_navbar) return;

    if (default_view) { // after login, go to default (= first) page
        document.location.href = Flask.url_for(menu[0][0])
    }
    const navbar_element = document.querySelector("#navbar");
    let dd_ctr = 0;
    for (const item of menu) {
        if (current_user.level >= item[2]) {
            const li = document.createElement("li");
            if (Array.isArray(item[0])) {
                // dropdown menu-item
                li.classList.add("nav-item", "dropdown");
                const a = document.createElement("a");
                li.appendChild(a)
                a.classList.add("nav-link", "dropdown-toggle");
                a.href = "#";
                a.id = `dd${dd_ctr}`
                a.setAttribute("role", "button");
                a.setAttribute("data-toggle", "dropdown");
                a.setAttribute("aria-haspopup", true);
                a.setAttribute("aria-expanded", true);
                a.innerHTML = item[1];
                const div = document.createElement("div");
                li.appendChild(div)
                div.classList.add("dropdown-menu");
                div.setAttribute("aria-labelledby", `dd${dd_ctr}`)
                for (const sitem of item[0]) {
                    if (sitem[0] === "divider") {
                        const divd = document.createElement("div");
                        divd.classList.add("dropdown-divider");
                        div.appendChild(divd)
                    } else {
                        if (current_user.level >= sitem[2]) {
                            const a = document.createElement("a");
                            div.appendChild(a)
                            a.classList.add("dropdown-item");
                            if (typeof sitem[0] === "function") {
                                a.onclick = sitem[0];
                            } else {
                                a.href = Flask.url_for(sitem[0]);
                            }
                            a.innerHTML = sitem[1]
                        }
                    }
                }
                dd_ctr++;
            } else {
                // regular menu-item
                li.classList.add("nav-item");
                const a = document.createElement("a");
                a.classList.add("nav-link");
                if (typeof item[0] === "function") {
                    a.onclick = item[0];
                } else {
                    const url_path = Flask.url_for(item[0]);
                    if (window.location.href.includes(url_path)) {
                        a.classList.add("active");
                    }
                    a.href = url_path;
                }
                a.innerHTML = item[1];
                li.appendChild(a);
            }
            navbar_element.appendChild(li);
        }
    }

    if (stand_alone) {
        const btn_div = document.createElement("div");
        btn_div.classList.add("nav-buttons");
        const sync_btn = document.createElement("button");
        sync_btn.classList.add("btn", "btn-warning");
        sync_btn.type = "button";
        sync_btn.onclick = start_sync;
        sync_btn.innerHTML = "Sync";
        btn_div.appendChild(sync_btn);
        navbar_element.appendChild(btn_div);

        // const upgrade_div = document.createElement("div");
        // upgrade_div.classList.add("nav-buttons");
        // const upgade_btn = document.createElement("button");
        // upgade_btn.classList.add("btn", "btn-warning");
        // upgade_btn.type = "button";
        // upgade_btn.onclick = start_upgrade;
        // upgade_btn.innerHTML = "Upgrade";
        // upgrade_div.appendChild(upgade_btn);
        // navbar_element.appendChild(upgrade_div);
    }

    const button_menu = new ButtonMenu(document.querySelector(".button-menu-placeholder"), button_menu_items);

    // used throughout all modules
    const locale_dutch = {
        OK: 'Ok',
        CONFIRM: 'Bewaar',
        CANCEL: 'Annuleer'
    };
    bootbox.addLocale('dutch', locale_dutch);

}

var logout_enabled = true;
export const autologout_disable = () => logout_enabled = false;

export const autologout_enable = () => logout_enabled = true;

if (logout && logout.to > 0) {
    var timeout_timer = null;
    const __reset_timer = () => {
        if (timeout_timer) clearTimeout(timeout_timer);
        timeout_timer = setTimeout(() => {
            if (logout_enabled) window.location.href = Flask.url_for("auth.logout")
        }, logout.to * 1000
        );
    }
    // Reset timer on user activity
    document.addEventListener('mousemove', __reset_timer);
    document.addEventListener('keydown', __reset_timer);
    document.addEventListener('click', __reset_timer);
    __reset_timer();
}



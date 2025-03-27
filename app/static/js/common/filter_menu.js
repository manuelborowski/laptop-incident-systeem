export class FilterMenu {
    constructor(placeholder, menu, changed_cb, id) {
        this.id = id;
        this.menu = menu;
        this.filters = [];

        const __add_label = (placeholder, item) => {
                const label = document.createElement("label");
                placeholder.appendChild(label);
                label.classList.add("control-label")
                label.setAttribute("for", item.id);
                label.innerHTML = item.label;
        }

        if (menu.length > 0) {
            for (const item of menu) {
                const form_group = document.createElement("div");
                form_group.classList.add(".filter-form-group");
                if (item.type === "select") {
                    __add_label(form_group, item);
                    const select = document.createElement("select");
                    form_group.appendChild(select);
                    select.classList.add("filter-form-control", "table-filter");
                    select.addEventListener("change", () => {
                        this.store_settings();
                        changed_cb();
                    })
                    select.id = item.id;
                    for (const o of item.options) {
                        const option = document.createElement("option");
                        select.appendChild(option);
                        if (o.value === item.default) option.setAttribute("selected", true);
                        option.value = o.value;
                        option.innerHTML = o.label;
                    }
                } else if (item.type === "checkbox") {
                    __add_label(form_group, item);
                    const checkbox = document.createElement("input");
                    form_group.appendChild(checkbox);
                    checkbox.type = "checkbox";
                    checkbox.id = item.id;
                    checkbox.classList.add("filter-form-control", "table-filter");
                    checkbox.addEventListener("click", () => {
                        this.store_settings();
                        changed_cb();
                    });
                } else if (item.type === "button") {
                    const button = document.createElement("a");
                    form_group.appendChild(button);
                    button.type = "button";
                    button.id = item.id;
                    button.classList.add("filter-form-control", "table-filter", "btn", "btn-success");
                    button.innerHTML = item.label;
                    button.addEventListener("click", item.callback);
                }
                placeholder.appendChild(form_group);
            }
            const button = document.createElement("button");
            placeholder.appendChild(button);
            button.classList.add("btn", "btn-danger");
            button.type = "button";
            button.innerHTML = "Reset";
            button.addEventListener("click", () => {
                localStorage.clear(`Filter-${this.id}`);
                let url = location.href.split("?")[0]; // remove trailing arguments
                location.replace(url);
            });
            this.load_settings();
            this.store_settings();
            placeholder.style.display = "flex";
        }
    }

    //All filters are stored, even the non-persistent.  In the latter case, the default value is stored iso actual value
    store_settings() {
        let store = [];
        this.filters = [];
        for (const f of this.menu) {
            let value = null;
            if (f.type === "select") value = document.querySelector(`#${f.id} option:checked`).value;
            if (f.type === "checkbox") value = document.querySelector(`#${f.id}`).checked;
            store.push({id: f.id, type: f.type, value: f.persistent ? value : f.default});
            this.filters.push({id: f.id, type: f.type, value});
        }
        localStorage.setItem(`Filter-${this.id}`, JSON.stringify(store));
    }

    load_settings() {
        const store = JSON.parse(localStorage.getItem(`Filter-${this.id}`));
        if (store === null || store === []) return false
        for(const f of store) {
            const element = document.querySelector(`#${f.id}`);
            if (element) element.value = f.value;
        }
        return true;
    }


}
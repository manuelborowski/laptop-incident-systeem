import {datatables_init} from "../datatables/dt.js";
import {fetch_get} from "../common/common.js";

$(document).ready(async () => {
    const meta = await fetch_get("incident.meta");
    if (!meta) return;
    const warranty_states = meta.option.warranty_state.filter(state => state.value !== meta.warranty.none);
    const filter_menu_items = [{
        type: "select",
        id: "warranty-state",
        label: "Garantie",
        options: [{value: "all", label: "Alles"}, ...warranty_states],
        default: "all",
        persistent: true
    }];
    datatables_init({filter_menu_items});
});

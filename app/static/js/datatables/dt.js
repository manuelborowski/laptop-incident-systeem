import {return_render_ellipsis} from "./ellipsis.js";
import {socketio} from "../common/socketio.js";
import {AlertPopup} from "../common/popup.js";
import {busy_indication_off, busy_indication_on} from "../common/common.js";
import {base_init} from "../base.js";
import {ContextMenu} from "../common/context_menu.js";
import {FilterMenu} from "../common/filter_menu.js";
import {CellEdit} from "./cell_edit.js";
import {ColumnVisibility} from "../common/column_visibility.js";

export let datatable_column2index = {};
// The index in the array is the index of the datacolumn in datatable.
// The value is the index of the visible column.
// [0, 1, 2, null, 3, 4] => datacolumn 3 is NOT visible, datacolumn 4 is visible as the 3rd column
export let datatable_column_shifter = [];
export let ctx = null;

//If not exactly one checkbox is selected, display warning and return false, else return true
function checkbox_is_exactly_one_selected() {
    let nbr_checked = 0;
    $(".chbx_all").each(function () {
        if (this.checked) nbr_checked++;
    });
    if (nbr_checked !== 1) new AlertPopup("warning", "U moet minstens één lijn selecteren")
    return nbr_checked === 1
}

//If one or more checkboxes are checked, return true.  Else display warning and return false
function checkbox_is_at_least_one_selected() {
    let nbr_checked = 0;
    $(".chbx_all").each(function () {
        if (this.checked) nbr_checked++;
    });
    if (nbr_checked === 0) new AlertPopup("warning", "U hebt niets geselecteerd, probeer nogmaals");
    return nbr_checked !== 0
}

export function checkbox_get_ids() {
    return Array.from(document.querySelectorAll(".chbx_all:checked")).map(c => c.value);
}

export function clear_checked_boxes() {
    $(".chbx_all").prop('checked', false);
    $("#select_all").prop('checked', false);
}

// If checkboxes are checked, return the ids of the selected rows
// Else, return the id of row the mouse pointer is on.
export const mouse_get_ids = mouse_event => {
    let ids = checkbox_get_ids();
    if (ids.length === 0) ids = [mouse_event.target.closest("tr").id];
    return ids;
}

export function datatable_row_data_from_id(id) {
    return ctx.table.row(`#${id}`).data();
}

export const datatable_row_data_from_target = target => {
    return ctx.table.row(target.target.closest("tr")).data();
}

export function update_cell(row_id, column_name, value) {
    let row_idx = ctx.table.row(`#${row_id}`).index();
    let column_idx = datatable_column2index[column_name];
    ctx.table.cell(row_idx, column_idx).data(value);
}

export function datatable_reload_table() {
    ctx.table.ajax.reload();
}

export const datatables_init = ({context_menu_items = [], filter_menu_items = [], button_menu_items = [], callbacks = {}}) => {
    ctx = {table_config, reload_table: datatable_reload_table}
    ctx.cell_to_color = "color_keys" in table_config ? table_config.cell_color.color_keys : null;
    ctx.suppress_cell_content = "color_keys" in table_config ? table_config.cell_color.supress_cell_content : null;

    const context_menu = new ContextMenu(document.querySelector("#datatable"), context_menu_items);
    context_menu.subscribe_get_ids(mouse_get_ids);
    const filter_menu = new FilterMenu(document.querySelector(".filter-menu-placeholder"), filter_menu_items, datatable_reload_table, ctx.table_config.view);

    // when columns are hidden, this array maps the real column index on the visible column index
    const __calc_column_shift = () => {
        datatable_column_shifter = [];
        let shift = 0;
        for (let i = 0; i < ctx.table.columns().count(); i++) {
            if (ctx.table.column(i).visible()) {
                datatable_column_shifter.push(i - shift);
            } else {
                shift++;
                datatable_column_shifter.push(null);
            }
        }
    }

    //Bugfix to repeat the table header at the bottom
    $("#datatable").append(
        $('<tfoot/>').append($("#datatable thead tr").clone())
    );

    const render_display = (data, typen, full, meta, v) => {
        let values = [];
        let color = null;
        for (const f of v.fields) {
            let value = full[f.field];
            if ("colors" in f) color = f.colors[value];
            if ("labels" in f) value = f.labels[value];
            if ("bool" in f) value = value === true ? "&#10003;" : "";
            values.push(value);
        }
        var template = values[0];
        if ("template" in v) {
            template = v.template;
            for (let i = 0; i < values.length; i++) template = template.replaceAll(`%${i}%`, values[i]);
        }
        if (color) {
            return `<div style="background:${color};">${template}</div>`
        } else {
            return template
        }
    }

    const render = (v) => {
        if ("ellipsis" in v) return_render_ellipsis(v.ellipsis.cutoff, v.ellipsis.wordbreak, true);

        if ("bool" in v) return (data, type, full, meta) => {
            return data === true ? "&#10003;" : "";
        };
        if ("label" in v) return (data, type, full, meta) => {
            return v.label.labels[data];
        }
        if ("color" in v) {
            const render = "render" in v ? v.render : null;
            v.render = function (data, type, full, meta) {
                if (render) data = render(data);
                return `<div style="background:${v.color.colors[ctx.table.cell(meta.row, meta.col).data()]};">${data}</div>`
            }
        }
        if ("less" in v) return (data, type, full, meta) => {
            return data < v.less.than ? ("then" in v.less ? v.less.then : data) : ("else" in v.less ? v.less.else : data);
        }

        if ("display" in v) {
            return (data, type, full, meta) =>  render_display(data, type, full, meta, v.display);
        }

        if ("equal" in v) {
            return (data, type, full, meta) => data === v.equal.to ? render_display(data, type, full, meta, v.equal.then) : render_display(data, type, full, meta, v.equal.else);
            }
    };


    // check special options in the columns
    $.each(ctx.table_config.template, (i, v) => {
        v.render = render(v);
        datatable_column2index[v.data] = i;
    })

    // get data from server and send to datatables to render it
    let __datatable_data_cb = null;
    const data_from_server = (type, data) => {
        busy_indication_off();
        __datatable_data_cb(data);
    }
    socketio.subscribe_on_receive(`${ctx.table_config.view}-datatable-data`, data_from_server);

    let datatable_config = {
        autoWidth: false,
        serverSide: true,
        stateSave: true,
        stateDuration: 0,
        ajax: function (data, cb, settings) {
            busy_indication_on();
            let filters = filter_menu.filters;
            if ("filters" in view_data) filters = filters.concat(view_data.filters);
            socketio.send_to_server(`${ctx.table_config.view}-datatable-data`, $.extend({}, data, {filters}));
            __datatable_data_cb = cb;
        },
        pagingType: "full_numbers",
        columns: ctx.table_config.template,
        language: {url: "static/datatables/dutch.json"},
        layout: {
            topStart: ["pageLength", "paging", "info"],
            topEnd: "search",
            bottomStart: ["pageLength", "paging"],
            bottomEnd: null
        },
        lengthMenu: [100, 500, 1000],
        pageLength: 500,
        // Called first. This callback is executed when a TR element is created (and all TD child elements have been inserted)
        createdRow: function (row, data, dataIndex, cells) {
            // in format_data, it is possible to tag a line with a different backgroundcolor
            if (data.overwrite_row_color && data.overwrite_row_color !== "") $(row).attr("style", `background-color:${data.overwrite_row_color};`);
            if (data.overwrite_cell_color) {
                for (const [cn, cc] of Object.entries(data.overwrite_cell_color)) {
                    const ci = datatable_column2index[cn];
                    $(cells[ci]).attr("style", `background-color: ${cc};`);
                }
            }
            if (callbacks.created_row) callbacks.created_row(row, data, dataIndex, cells);
        },
        // Called second. This callback allows you to 'post process' each row after it have been generated for each table draw, but before it is rendered into the document
        rowCallback: function (row, data, displayNum, displayIndex, dataIndex) {
            if (data.row_action !== null) row.cells[0].innerHTML = `<input type='checkbox' class='chbx_all' name='chbx' value='${data.row_action}'>`
            // celledit of type select: overwrite cell content with label from optionlist
            if (cell_edit.select_options) {
                for (const [column, select] of Object.entries(cell_edit.select_options)) {
                    if (datatable_column_shifter[column] !== null) {
                        row.cells[datatable_column_shifter[column]].innerHTML = select[row.cells[datatable_column_shifter[column]].innerHTML];
                    }
                }
            }
        },
        preDrawCallback: function (settings) {
            __calc_column_shift();
        },

        drawCallback: function (settings) {
            if (ctx.cell_to_color) {
                ctx.table.cells().every(function () {
                    if (this.data() in ctx.cell_to_color) {
                        $(this.node()).css("background-color", ctx.cell_to_color[this.data()]);
                        if (ctx.suppress_cell_content) $(this.node()).html("");
                    }
                });
            }
            if (callbacks.table_loaded) callbacks.table_loaded();
        },
        initComplete: function () {
            new ColumnVisibility(document.querySelector('.column-visible-placeholder'), table_config.template, (column, visible) => ctx.table.column(column).visible(visible), table_config.view);
        },
    }

    if ("default_order" in table_config) {
        datatable_config["order"] = [[table_config.default_order[0], table_config.default_order[1]]];
    }

    if ("width" in table_config) {
        $("#datatable").attr("width", table_config.width);
    }

    DataTable.type('num', 'className', 'dt-left');
    DataTable.type('date', 'className', 'dt-left');
    DataTable.defaults.column.orderSequence = ['desc', 'asc'];
    ctx.table = new DataTable('#datatable', datatable_config);

    // if columns are invisible, the column index in rowCallback is reduced, depending on the invisible columns.
    // create a translation table to go from actual column index to the reduced (with invisible columns) column index
    // the table is redrawn because hiding/displaying columns has impact on columns with ellipses
    ctx.table.on('column-visibility.dt', (e, settings, column, state) => {
        __calc_column_shift();
        ctx.table.draw();
    });

    const update_cell_changed = data => {
        socketio.send_to_server(`${ctx.table_config.view}-cell-update`, data);
    }

    const __cell_edit_changed_cb = ($dt_row, column_index, new_value, old_value) => {
        const value = ctx.table_config.template[column_index].celledit.value_type === 'int' ? parseInt(new_value) : new_value;
        const column_name = ctx.table.column(column_index).dataSrc()
        update_cell_changed({id: $dt_row.data().DT_RowId, column: column_name, value});
    }

    function cell_toggle_changed_cb(cell, row, value) {
        const data = {
            'id': row.data().DT_RowId,
            'column': cell.index().column,
            'value': value
        }
        update_cell_changed(data);
    }

    const cell_edit = new CellEdit(ctx.table, table_config.template, __cell_edit_changed_cb);

    if ("row_detail" in table_config) {
        //For an extra-measure, show the associated remarks as a sub-table
        let d_table_start = '<table cellpadding="5" cellspacing="0" border="2" style="padding-left:50px;">'
        let d_table_stop = '</table>'
        let d_header = '<tr><td>Datum</td><td>Leerling</td><td>LKR</td><td>KL</td><td>Les</td><td>Opmerking</td><td>Maatregel</td></tr>'

        function format_row_detail(data) {
            let s = d_table_start;
            s += d_header;
            if (data) {
                for (let i = 0; i < data.length; i++) {
                    s += '<tr>'
                    s = s + '<td>' + data[i].date + '</td>';
                    s = s + '<td>' + data[i].student.full_name + '</td>';
                    s = s + '<td>' + data[i].teacher.code + '</td>';
                    s = s + '<td>' + data[i].grade.code + '</td>';
                    s = s + '<td>' + data[i].lesson.code + '</td>';
                    s = s + '<td>' + data[i].subjects + '</td>';
                    s = s + '<td>' + data[i].measures + '</td>';
                    s += '</tr>'
                }
                s += d_table_stop;
                return s;
            }
            return 'Geen gegevens';
        }

        // Array to track the ids of the details displayed rows
        let detail_rows_cache = [];

        $('#datatable tbody').on('click', 'tr td.details-control', function () {
            let tr = $(this).closest('tr');
            let row = ctx.table.row(tr);
            let idx = $.inArray(tr.attr('DT_RowId'), detail_rows_cache);

            if (row.child.isShown()) {
                tr.removeClass('details');
                row.child.hide();
                detail_rows_cache.splice(idx, 1);
            } else {
                let tx_data = {"id": row.data().DT_RowId};
                $.getJSON(Flask.url_for('reviewed.get_row_detail', {'data': JSON.stringify(tx_data)}),
                    function (rx_data) {
                        if (rx_data.status) {
                            row.child(format_row_detail(rx_data.details)).show();
                            tr.addClass('details');
                            if (idx === -1) {
                                detail_rows_cache.push(tr.attr('DT_RowId'));
                            }
                        } else {
                            bootbox.alert('Fout: kan details niet ophalen');
                        }
                    });
            }
        });
    }

    if ("row_detail" in table_config) {
        //This function is called, each time the table is drawn
        ctx.table.on('draw', function () {
            //Row details
            $.each(detail_rows_cache, function (i, id) {
                $('#' + id + ' td.details-control').trigger('click');
            });
        });
    }

    //checkbox in header is clicked
    $("#select_all").change(function () {
        $(".chbx_all").prop('checked', this.checked);
    });
    base_init({button_menu_items});
}


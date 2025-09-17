from sqlalchemy import desc, text
from app.data.settings import get_datatables_config

class DatatableConfig:
    def __init__(self, view, title):
        self.view = view
        self.title = title

    buttons = []
    href = []
    cell_to_color = None
    suppress_cell_content = None
    enable_column_visible_selector = True
    enable_persistent_filter_settings = True

    def show_filter_elements(self):
        return []

    def pre_sql_query(self):
        return None

    def pre_sql_filter(self, q, filters):
        return q

    def pre_sql_search(self, search):
        return []

    def pre_sql_column_search(self, column, search):
        return []

    def pre_sql_order(self, q, on, direction):
        return q.order_by(desc(text(on))) if direction == 'desc' else q.order_by(text(on))

    def pre_sql_paginate(self, q, start, stop):
        return q.slice(start, stop)

    def format_data(self, db_list, total_count=None, filtered_count=None):
        out = []
        for i in db_list:
            em = i.to_dict()
            em.update({"row_action": i.id, "DT_RowId": i.id})
            out.append(em)
        return total_count, filtered_count, out

    def post_sql_filter(self, l, filter, count):
        return count, l

    def post_sql_search(self, l, search, count):
        return count, l

    def post_sql_order(self, l, on, direction):
        return l

    def post_sql_paginate(self, l, start, length):
        return l[start:length]

    def post_process_template(self, template):
        return template

    @property
    def template(self):
        return get_datatables_config(self.view)

    def create_table_config(self):
        template = self.post_process_template(self.template)
        return {
            "href": self.href,
            "template": template,
            "cell_to_color": self.cell_to_color,
            "suppress_cell_content": self.suppress_cell_content,
            "title": self.title,
            "view": self.view,
        }

    def pre_sql_standard_order(self, q, on, direction):
        return q.order_by(desc(text(on))) if direction == 'desc' else q.order_by(text(on))


import ast
from pathlib import Path
from types import SimpleNamespace


def extract(path, name, class_name=None):
    tree = ast.parse(Path(path).read_text(encoding='utf-8-sig'))
    body = tree.body
    if class_name:
        body = next(n for n in body if isinstance(n, ast.ClassDef) and n.name == class_name).body
    fn = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
    fn.decorator_list = []
    fn.returns = None
    fn.args.defaults = []
    for arg in fn.args.args:
        arg.annotation = None
    ns = {'RealDictCursor': object, 'company_code': lambda code: code or 'MSL-CR'}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), path, 'exec'), ns)
    return ns[name]


class Cursor:
    def execute(self, sql, params):
        self.sql, self.params = sql, params

    def fetchall(self):
        return []

    def close(self):
        self.closed = True


board = extract('backend_api/routers/comercial.py', 'comercial_board')
for company in ('MCI-CR', 'MSL-CR'):
    for year in (None, 2026):
        cursor = Cursor()
        conn = SimpleNamespace(cursor=lambda **kwargs: cursor)
        board(None, None, None, None, None, [' Confirmado ', 'En Operación'], year, company, conn)
        assert cursor.params['company'] == company
        assert cursor.params['estados'] == ['confirmado', 'en operación']
        assert "COALESCE(NULLIF(TRIM(company_code), ''), 'MSL-CR') = %(company)s" in cursor.sql
        assert 'LOWER(TRIM(estado))' in cursor.sql
        assert 'y_start' not in cursor.params
        assert ('year_start' in cursor.params) == bool(year)
        assert cursor.closed

class Var:
    def __init__(self, value):
        self.value = value
    def get(self):
        return self.value
    def set(self, value):
        self.value = value

path = 'Modulos/Comercial/comercial_home_ui.py'
clear = extract(path, '_clear', 'ComercialHomeUI')
filters = extract(path, '_build_filters', 'ComercialHomeUI')
view = SimpleNamespace(**{name: Var('old') for name in (
    'f_cliente', 'f_pais', 'f_puerto', 'f_surveyor', 'f_year',
    'f_estado_confirmado', 'f_estado_por_confirmar', 'f_estado_finalizado', 'f_estado_cancelado')})
view.tabla = SimpleNamespace(get_children=lambda: [])
view.lbl_page = SimpleNamespace(config=lambda **kw: None)
calls = []
view._search = lambda: calls.append(filters(view))
clear(view)
assert len(calls) == 1
assert calls[0]['estados'] == ['Confirmado', 'En Operación']
assert calls[0]['year'] is None
print('PASS: both companies, both active states, explicit years, clear reload, cursor cleanup')

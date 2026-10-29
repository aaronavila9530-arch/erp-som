import ast
from pathlib import Path
from types import SimpleNamespace

path = Path('Modulos/HHRR/views/vista_solicitudes.py')
tree = ast.parse(path.read_text(encoding='utf-8'))
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef))
method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_build_export_rows')
namespace = {}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
rows = [dict(id=13, event_type='VACACIONES', event_date='2026-10-24', status='PENDING',
             payload=dict(fecha_inicio='2026-12-11', fecha_fin='2026-12-12', dias_solicitados=2)),
        dict(id=14, event_type='CONSTANCIA_LABORAL', event_date='2026-10-29', payload=None)]
view = SimpleNamespace(_filtered_rows=rows, ESTADO_LABELS={'PENDING':'Pendiente'})
output = namespace['_build_export_rows'](view)
assert output[0]['fecha_inicio'] == '2026-12-11'
assert output[0]['fecha_fin'] == '2026-12-12'
assert output[0]['event_date'] == '2026-10-24'
assert output[1]['fecha_inicio'] == output[1]['fecha_fin'] == ''
render = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_render_rows')
assert 'fecha_inicio' in ast.unparse(render) and 'fecha_fin' in ast.unparse(render)
print('PASS: requested dates distinct from creation date; undated requests remain blank')

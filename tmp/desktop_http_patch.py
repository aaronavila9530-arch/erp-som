import ast
import difflib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
targets = {
    'lashing_certificates_router.py': {'get_lashing_certificate'},
    'sampling_certificates_router.py': {'get_sampling_certificate'},
    'vessel_cargo_condition_router.py': {'get_vessel_cargo_condition'},
    'vessel_holds_inspection_certificates_router.py': {'get_vessel_holds_certificate'},
    'draft_survey_final_router.py': {'generate_unified_final_pdf', 'generate_final_pdf'},
}
patch = ['*** Begin Patch']
for file, functions in targets.items():
    path = root / 'backend_api/routers' / file
    source = path.read_text(encoding='utf-8-sig')
    lines = source.splitlines(keepends=True)
    inserts = []
    for fn in ast.parse(source).body:
        if not isinstance(fn, ast.FunctionDef):
            continue
        if fn.name not in functions:
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Try):
                continue
            if any(isinstance(h.type, ast.Name) and h.type.id == 'HTTPException' for h in node.handlers):
                continue
            for handler in node.handlers:
                if isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                    indent = ' ' * handler.col_offset
                    inserts.append((handler.lineno - 1, indent + 'except HTTPException:\n' + indent + '    raise\n'))
    if not inserts:
        print(json.dumps({'missing': file}))
        continue
    for index, value in sorted(inserts, reverse=True):
        lines.insert(index, value)
    changed = ''.join(lines)
    diff = list(difflib.unified_diff(source.splitlines(), changed.splitlines(), lineterm=''))[2:]
    patch.append('*** Update File: ' + str(path).replace('\\', '/'))
    patch.extend('@@' if line.startswith('@@') else line for line in diff)
patch.append('*** End Patch')
print(json.dumps({'patch': '\n'.join(patch)}))

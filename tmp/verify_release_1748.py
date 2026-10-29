from pathlib import Path
from PyInstaller.archive.readers import ZlibArchiveReader

root = Path(__file__).resolve().parents[1]
build = root.parent / 'som-release-1.7.48'
dist = build / 'client/ERP-SOM'
archive = ZlibArchiveReader(str(build / 'work/main/PYZ-00.pyz'))
version = {}
exec(archive.extract('version'), version)
assert version['APP_VERSION'] == '1.7.48'
for relative in ('Modulos/HHRR/views/vista_solicitudes.py', 'Modulos/Comercial/comercial_home_ui.py', 'version.py'):
    assert (dist / '_internal' / relative).read_bytes() == (root / relative).read_bytes()
for name in ('api_client', 'version', 'backend_api.database', 'Modulos.HHRR.ui_hhrre',
             'Modulos.Comercial.comercial_home_ui', 'Modulos.Informes.Vessel_Draft_Survey.draft_survey_form'):
    assert name in archive.toc, name
for name in ('hr', 'rbac_hhrre', 'rbac_informes', 'rbac_comercial', 'inject_port',
             'inyectar_surveyors', 'crear_usuario_surveyor01_directo', 'create_surveyor01_user'):
    assert 'backend_api.' + name not in archive.toc
    assert not (dist / '_internal/backend_api' / (name + '.py')).exists()
for file in (dist / '_internal/backend_api').rglob('*.py'):
    content = file.read_text(encoding='utf-8-sig', errors='replace')
    assert 'postgresql://' not in content and 'postgres://' not in content, str(file)
assert (dist / 'ERP-SOM.exe').stat().st_size > 1_000_000
print('PASS: packaged version, changed sources, runtime modules and excluded maintenance credentials')

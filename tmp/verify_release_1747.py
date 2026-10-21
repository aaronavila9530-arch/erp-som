from pathlib import Path
import types
from PyInstaller.archive.readers import ZlibArchiveReader

source = Path(__file__).resolve().parents[2] / 'som-release-1.7.47'
dist = source / 'dist-release-1.7.47/ERP-SOM'
archive = ZlibArchiveReader(str(source / 'build-release-1.7.47/main/PYZ-00.pyz'))
version = {}
exec(archive.extract('version'), version)
assert version['APP_VERSION'] == '1.7.47'
for module, cls, names in (
    ('Modulos.Servicios.popup_servicio', 'PopupServicio', {'_advance_save', '_save_steps', '_request_close'}),
    ('Modulos.Servicios.vista_servicios', 'VistaServicios', {'load_data', '_render_data'}),
):
    code = archive.extract(module)
    class_code = next(c for c in code.co_consts if isinstance(c, types.CodeType) and c.co_name == cls)
    actual = {c.co_name for c in class_code.co_consts if isinstance(c, types.CodeType)}
    assert names <= actual
for relative in ('Modulos/Servicios/popup_servicio.py', 'Modulos/Servicios/vista_servicios.py', 'version.py'):
    assert (dist / '_internal' / relative).read_bytes() == (source / relative).read_bytes(), relative
for name in ('api_client', 'version', 'backend_api.database', 'Modulos.HHRR.ui_hhrre',
             'Modulos.Comercial.comercial_home_ui', 'Modulos.Informes.Vessel_Draft_Survey.draft_survey_form'):
    assert name in archive.toc, name
for name in ('hr', 'rbac_hhrre', 'rbac_informes', 'rbac_comercial', 'inject_port',
             'inyectar_surveyors', 'crear_usuario_surveyor01_directo', 'create_surveyor01_user'):
    assert 'backend_api.' + name not in archive.toc
    assert not (dist / '_internal/backend_api' / (name + '.py')).exists()
for file in (dist / '_internal/backend_api').rglob('*.py'):
    contents = file.read_text(encoding='utf-8-sig', errors='replace')
    assert 'postgresql://' not in contents and 'postgres://' not in contents, str(file)
assert (dist / 'ERP-SOM.exe').stat().st_size > 1_000_000
print('PASS: packaged 1.7.47, asynchronous methods, exact sources, required modules and excluded maintenance credentials.')

from pathlib import Path
from PyInstaller.archive.readers import ZlibArchiveReader

root = Path(__file__).resolve().parents[1]
dist = root / 'dist-release-1.7.45/ERP-SOM'
archive = ZlibArchiveReader(str(root / 'build-release-1.7.45/main/PYZ-00.pyz'))
excluded = {'hr', 'rbac_hhrre', 'rbac_informes', 'rbac_comercial', 'inject_port',
            'inyectar_surveyors', 'crear_usuario_surveyor01_directo', 'create_surveyor01_user'}
for name in excluded:
    assert 'backend_api.' + name not in archive.toc, name
    assert not (dist / '_internal/backend_api' / (name + '.py')).exists(), name
for name in ('api_client', 'version', 'Modulos.Comercial.comercial_home_ui', 'Modulos.HHRR.ui_hhrre', 'backend_api.database'):
    assert name in archive.toc, name
version = {}
exec(archive.extract('version'), version)
assert version['APP_VERSION'] == '1.7.45'
for relative in ('Modulos/Comercial/comercial_home_ui.py', 'backend_api/services/notifications.py', 'version.py'):
    assert (dist / '_internal' / relative).read_bytes() == (root / relative).read_bytes(), relative
for file in (dist / '_internal/backend_api').rglob('*.py'):
    contents = file.read_text(encoding='utf-8-sig', errors='replace')
    assert 'postgresql://' not in contents and 'postgres://' not in contents, str(file)
assert (dist / 'ERP-SOM.exe').stat().st_size > 1_000_000
print('Verified 1.7.45, required modules, exact sources, and exclusion of legacy database credentials.')

from pathlib import Path
import sys
import tempfile
import types
from unittest.mock import patch
from docx import Document
from PyInstaller.archive.readers import ZlibArchiveReader

root = Path(__file__).resolve().parents[1]
source = root.parent / 'draft-release-1.7.46'
sys.path.insert(0, str(source))
from backend_api.tests.test_draft_word_difference import load_calculations
from backend_api.services.draft_survey_word_pdf_service import generate_draft_survey_word_pdf

class ConversionBoundary(Exception):
    pass

with tempfile.TemporaryDirectory(prefix='draft-sign-qa-') as directory:
    for index, calculate in enumerate(load_calculations()):
        payload = calculate({'word_draft_figures': '51444.60', 'word_bl_figures': '51442.00',
                             'draft_report_number': 'SIGN-QA-' + str(index)})
        with patch('tempfile.gettempdir', return_value=directory), patch(
            'backend_api.services.draft_survey_word_pdf_service.subprocess.run',
            side_effect=ConversionBoundary):
            try:
                generate_draft_survey_word_pdf(payload)
            except ConversionBoundary:
                pass
        doc = Document(str(Path(directory) / (payload['draft_report_number'] + '.docx')))
        text = '\n'.join(node.text or '' for node in doc.element.iter()
                         if node.tag.endswith('}t'))
        assert '2.60' in text and '0.0051' in text, text
        assert '-2.60' not in text and '-0.0051' not in text, text
print('Actual Word template contains positive 2.60 MT and 0.0051%; PDF conversion not run.')

dist = source / 'dist-release-1.7.46/ERP-SOM'
archive = ZlibArchiveReader(str(source / 'build-release-1.7.46/main/PYZ-00.pyz'))
version = {}
exec(archive.extract('version'), version)
assert version['APP_VERSION'] == '1.7.46'
module_code = archive.extract('Modulos.Informes.Vessel_Draft_Survey.draft_survey_form')
class_code = next(c for c in module_code.co_consts if isinstance(c, types.CodeType)
                  and c.co_name == 'DraftSurveyForm')
method_names = {'_coerce_draft_number', '_fmt_calc_number', '_fmt_calc_percent',
                '_apply_word_report_calculations_to_data'}
methods = {c.co_name: types.FunctionType(c, {}) for c in class_code.co_consts
           if isinstance(c, types.CodeType) and c.co_name in method_names}
packed_form = type('PackedCalculations', (), methods)()
result = packed_form._apply_word_report_calculations_to_data(
    {'word_draft_figures': '51444.60', 'word_bl_figures': '51442.00'})
assert result['word_difference'] == '2.60' and result['word_percentage'] == '0.0051'
for relative in ('Modulos/Informes/Vessel_Draft_Survey/draft_survey_form.py',
                 'backend_api/routers/draft_survey_extra_router.py', 'version.py'):
    assert (dist / '_internal' / relative).read_bytes() == (source / relative).read_bytes()
for relative in ('Modulos/Comercial/comercial_servicios_analytics_ui.py',
                 'Modulos/HHRR/popups/popup_liquidacion.py', 'api_client.py'):
    assert (source / relative).read_bytes() != (root / relative).read_bytes(), relative
for name in ('api_client', 'version', 'Modulos.Comercial.comercial_home_ui',
             'Modulos.HHRR.ui_hhrre', 'backend_api.database',
             'Modulos.Informes.Vessel_Draft_Survey.draft_survey_form'):
    assert name in archive.toc, name
for name in ('hr', 'rbac_hhrre', 'rbac_informes', 'rbac_comercial', 'inject_port',
             'inyectar_surveyors', 'crear_usuario_surveyor01_directo', 'create_surveyor01_user'):
    assert 'backend_api.' + name not in archive.toc, name
    assert not (dist / '_internal/backend_api' / (name + '.py')).exists(), name
for file in (dist / '_internal/backend_api').rglob('*.py'):
    contents = file.read_text(encoding='utf-8-sig', errors='replace')
    assert 'postgresql://' not in contents and 'postgres://' not in contents, str(file)
assert (dist / 'ERP-SOM.exe').stat().st_size > 1_000_000
print('Verified packaged version, fixed sources, required modules and exclusion of unrelated edits/legacy credentials.')

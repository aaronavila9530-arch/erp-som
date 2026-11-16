"""Generate only from retained MCI references; never rewrite source templates."""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from services.mci_survey_schema import SurveyContent, export_sections
from services.mci_report_language import translate, localize_document, localize_template

TEMPLATES = Path(__file__).resolve().parents[1] / 'templates'
MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December')


def english_date(value, time=False):
    if not value:
        return ''
    result = f'{MONTHS[value.month-1]} {value.day}, {value.year}'
    return result + (value.strftime(' %H:%M') + ' LT' if time else '')


def set_text(p, value):
    """Keep paragraph/run formatting; replace text without carrying sample facts."""
    p = p if isinstance(p, Paragraph) else Paragraph(p, None)
    runs = list(p.runs)
    if runs:
        runs[0].text = str(value or '')
        for run in runs[1:]:
            run.text = ''
    else:
        p.add_run(str(value or ''))
    return p._p


def build_word(row):
    if row.get('company_code') != 'MCI-CR':
        raise ValueError('MCI document requires MCI context')
    content = SurveyContent.model_validate(row['content'])
    tr = lambda text: translate(text, content.language)
    def date_text(value, time=False):
        if content.language != 'ES' or not value:
            return english_date(value, time)
        months = ('enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre')
        return f'{value.day} de {months[value.month-1]} de {value.year}' + (value.strftime(' %H:%M') + ' hora local' if time else '')
    source = Document(TEMPLATES / 'mci_general_original.docx')
    doc = Document(TEMPLATES / 'mci_letterhead_original.docx')
    localize_document(doc, content.language)
    body = doc.element.body
    insertion = body[0]
    existing_styles = {s.style_id for s in doc.styles}
    for style in source.styles:
        if style.style_id not in existing_styles:
            doc.styles.element.append(deepcopy(style.element))
    def add(element):
        insertion.addprevious(element)
    def clone(text, value=None):
        p = next(p for p in source.paragraphs if p.text.strip() == text)
        element = deepcopy(p._p)
        for sect in list(element.xpath('.//w:sectPr')):
            sect.getparent().remove(sect)
        if value is not None:
            set_text(element, value)
        elif content.language == 'ES':
            set_text(element, tr(p.text))
        return element
    add(clone('PROFESSIONAL TECHNICAL REPORT'))
    add(clone('M/V LINA AKSOY', row['vessel']))
    report_type = {'vessel':'Vessel Survey', 'condition':'Vessel Condition Survey', 'cargo':'Cargo Condition Survey', 'logistics':'Logistics Supervision', 'port_captancy':'Port Captancy', 'crane':'Crane Inspections'}.get(row.get('kind'), 'Survey Report')
    add(clone('Multiple mooring-line failures during bulk cargo discharge\nBerth No. 4 - Puerto Caldera, Costa Rica', tr(report_type)+'\n'+row.get('location', content.location)))
    table = deepcopy(source.tables[0]._tbl)
    localize_template(table, content.language)
    values = [row['requested_by'], f"{row['vessel']} / IMO {content.imo}", content.length_and_tonnage,
              content.cargo, ' - '.join(date_text(d, time=True) for d in (content.period_start,content.period_end) if d),
              date_text(content.issue_date), tr(content.report_status or 'Draft')]
    for table_row, value in zip(table.xpath('./w:tr'), values):
        cell = table_row.xpath('./w:tc')[1]
        paragraphs = cell.xpath('./w:p')
        set_text(paragraphs[0], value)
        for p in paragraphs[1:]:
            cell.remove(p)
    add(table)
    text='This report is issued exclusively for the client that instructed MSL and its advisers.\nIt does not constitute an admission of liability or a legal opinion.'
    add(clone(text, tr(text.replace('instructed MSL', 'instructed MCI'))))
    heading_sources = {
        'instructions':'INSTRUCTIONS, SCOPE AND METHODOLOGY', 'work':'1.1 Work performed',
        'limitations':'1.2 Main limitations of this report',
        'chronology':'1.3 Time and place of arrival and chronology of events:',
        'representatives':'Representatives', 'findings':'SURVEY FINDINGS', 'visual':'2.1 Visual inspection',
        'provided':'Documentation provided', 'missing':'Documentation not provided',
        'conclusion':'2. CONCLUSION', 'enclosure':'3. ENCLOSURE',
    }
    normal = next(p for p in source.paragraphs if p.text.strip() == 'Master:')
    headings = {'instructions':'1. INSTRUCTIONS, SCOPE AND METHODOLOGY',
                'work':'1.1 Work performed', 'limitations':'1.2 Main limitations of this report',
                'chronology':'1.3 Time and place of arrival and chronology of events:',
                'representatives':'Representatives', 'findings':'2. SURVEY FINDINGS',
                'visual':'2.1 Visual inspection', 'provided':'2.2 Documentation provided',
                'missing':'2.3 Documentation not provided', 'conclusion':'3. CONCLUSION', 'enclosure':'4. ENCLOSURE'}
    sections = export_sections(content)
    if row.get('kind') == 'logistics':
        from services.mci_logistics_schema import TITLES, GROUPS
        parents = {child:parent for parent,children in GROUPS.items() for child in children}
        sections = [(key,TITLES[key],[b.text for b in content.sections[key].blocks if b.text.strip()])
                    for key in TITLES if key in content.sections and content.sections[key].enabled
                    and (key not in parents or (content.sections.get(parents[key]) and content.sections[parents[key]].enabled))]
        heading_sources.update(particulars='SURVEY FINDINGS', process='SURVEY FINDINGS',
                               documentary='2.1 Visual inspection', operational='2.1 Visual inspection', incidents='2.1 Visual inspection')
        headings.update(particulars='2. VESSEL PARTICULARS', process='3. SUPERVISION PROCESS',
                        findings='4. SURVEY FINDINGS', documentary='4.1 Documentary findings',
                        operational='4.2 Operational control findings', incidents='4.3 Incidents',
                        conclusion='5. CONCLUSION', enclosure='6. ENCLOSURE')
    if row.get('kind') == 'port_captancy':
        from services.mci_port_captancy_schema import TITLES, GROUPS
        parents = {child: parent for parent, children in GROUPS.items() for child in children}
        sections = [(key, TITLES[key], [b.text for b in content.sections[key].blocks if b.text.strip()])
                    for key in TITLES if key in content.sections and content.sections[key].enabled
                    and (key not in parents or (content.sections.get(parents[key]) and content.sections[parents[key]].enabled))]
        heading_sources.update(particulars='SURVEY FINDINGS', operation_summary='SURVEY FINDINGS', remarks='SURVEY FINDINGS')
        headings.update(particulars='2. VESSEL PARTICULARS', operation_summary='3. OPERATION SUMMARY',
                        remarks='4. REMARKS', conclusion='5. CONCLUSION', enclosure='6. ENCLOSURE',
                        chronology='1.3 Extract time sheet')
    if row.get('kind') == 'crane':
        from services.mci_crane_schema import TITLES, GROUPS, POINTS
        from services.crane_web_fields import SUFFIXES
        parents={child:parent for parent,children in GROUPS.items() for child in children}
        sections=[]
        for number,(parent,children) in enumerate(GROUPS.items(),1):
            heading_sources[parent]='SURVEY FINDINGS'
            headings[parent]=f'{number}. {TITLES[parent]}'
            for index,child in enumerate(children,1):
                heading_sources[child]='2.1 Visual inspection';headings[child]=f'{number}.{index} {TITLES[child]}'
        for key,title in TITLES.items():
            sec=content.sections.get(key)
            if not sec or not sec.enabled:continue
            if key in parents and not (content.sections.get(parents[key]) and content.sections[parents[key]].enabled):continue
            blocks=[b.text for b in sec.blocks if b.text.strip()]
            if key=='crane_intro' and content.inspection_date:
                blocks.insert(0,tr('Inspection date')+': '+date_text(content.inspection_date)+((' '+content.inspection_time.strftime('%H:%M')+(' hora local' if content.language=='ES' else ' LT')) if content.inspection_time else ''))
            if key=='instructions':
                blocks=[f'{label}: {value}' for label,value in (('GRT',content.grt),('NRT',content.nrt)) if value]+blocks
            if key=='crane_checklist':
                blocks=[]
                for point,label in POINTS.items():
                    check=content.crane_checks.get(point)
                    if not check:continue
                    statuses=[getattr(check,s) for s in SUFFIXES if getattr(check,s)]
                    if check.done or statuses:blocks.append(tr(label)+': '+(', '.join(tr(s) for s in statuses) if statuses else tr('Inspection performed; status not specified'))+'.')
            sections.append((key,title,blocks))
    for key, title, blocks in sections:
        heading = clone(heading_sources[key], tr(headings[key]))
        # Explicit hierarchical labels must not inherit the template's flat list.
        ppr = heading.get_or_add_pPr()
        ppr.get_or_add_keepNext().val = True
        numbering = ppr.get_or_add_numPr()
        numbering.get_or_add_numId().val = 0
        add(heading)
        if key == 'representatives':
            blocks = [f'{tr(label)}: {value}' for label,value in [('Master',content.master),('Chief officer',content.chief_officer),('Surveyor',content.surveyor)]] + blocks
        elif key == 'particulars' and row.get('kind') in ('logistics','port_captancy'):
            blocks = [f'{tr("Vessel")}: {row["vessel"]}', f'{tr("Flag / port of registry")}: {content.flag_port_registry}',
                      f'GRT: {content.grt}', f'NRT: {content.nrt}', f'IMO: {content.imo}',
                      f'{tr("Year built")}: {content.build_year}'] + blocks
        elif key == 'chronology' and row.get('kind') == 'logistics':
            blocks = [f'{tr(label)}: {date_text(value)}' for label,value in (
                ('Arrival',content.arrival_date), ('Inspection',content.inspection_date),
                ('Supervision completed',content.supervision_completed_date)) if value] + blocks
        elif key == 'instructions' and row.get('kind') == 'port_captancy':
            blocks = [f'{tr(label)}: {value}' for label, value in (
                ('Survey scope', content.report_type), ('Operation', content.operation),
                ('Continent', content.continent)) if value] + blocks
        elif key == 'chronology' and row.get('kind') == 'port_captancy':
            from services.port_captancy_web_fields import EVENTS
            events = [('Arrival', content.arrival_date, content.arrival_time),
                      ('Inspection', content.inspection_date, content.inspection_time)]
            events += [(label, getattr(content, f'ts_date_{i}'), getattr(content, f'ts_time_{i}')) for i,label in enumerate(EVENTS)]
            blocks = [f'{tr(label)}: {date_text(d)}' + (' '+t.strftime('%H:%M')+(' hora local' if content.language=='ES' else ' LT') if t else '')
                      for label,d,t in events if d or t] + blocks
        elif key == 'enclosure':
            blocks = [tr('Picture link')+': ' + '\n'.join(blocks)]
        for text in blocks:
            p = deepcopy(normal._p)
            set_text(p, text)
            add(p)
    disclaimer = next(p.text for p in source.paragraphs if p.text.startswith('THIS BONA FIDE'))
    disclaimer_element = clone(disclaimer)
    if content.language == 'ES':
        disclaimer_element.get_or_add_pPr().get_or_add_keepLines().val = True
    add(disclaimer_element)
    # The first section has a clean footer; the separate signature page retains
    # the original footer-anchored seal and logo, and the original body spacers.
    break_p = OxmlElement('w:p')
    ppr = OxmlElement('w:pPr')
    section = deepcopy(doc.sections[0]._sectPr)
    section_type = section.find(qn('w:type'))
    if section_type is None:
        section_type = OxmlElement('w:type'); section.append(section_type)
    section_type.set(qn('w:val'), 'nextPage')
    ppr.append(section); break_p.append(ppr); add(break_p)
    first, last = doc.sections[0], doc.sections[-1]
    original_footer = last.footer
    footer_elements = [deepcopy(e) for e in original_footer._element]
    # Remove only the first section's reference before creating its distinct footer.
    for ref in list(first._sectPr.findall(qn('w:footerReference'))):
        first._sectPr.remove(ref)
    first.footer.is_linked_to_previous = False
    clean_footer = first.footer
    for child in list(clean_footer._element):
        clean_footer._element.remove(child)
    for element in footer_elements:
        for drawing in list(element.xpath('.//w:drawing')):
            drawing.getparent().remove(drawing)
        # Hyperlinks and other referenced objects retain their part relationships.
        for node in element.iter():
            for attr, value in list(node.attrib.items()):
                if attr.startswith('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'):
                    rel = original_footer.part.rels[value]
                    node.set(attr, clean_footer.part.relate_to(rel.target_ref if rel.is_external else rel.target_part, rel.reltype, rel.is_external))
        clean_footer._element.append(element)
    for p in doc.paragraphs:
        if p.text.strip() == '{cert_num}':
            set_text(p, row['report_number'])
        elif 'Pabel' in p.text:
            set_text(p, content.surveyor)
        elif p.text.strip() == 'Marine Surveyors & Logistics Group':
            set_text(p, 'Marine Claims & Risk Intelligence')
    # Place the linked report number into the existing header, not the filename.
    doc.settings.odd_and_even_pages_header_footer = False
    seen_headers=set()
    for section in doc.sections:
        section.different_first_page_header_footer = False
        # Keep section children in OOXML order. Out-of-order references cause
        # converters to create spurious page styles without a running header.
        references=[]
        for tag in ('headerReference','footerReference'):
            refs=section._sectPr.findall(qn('w:'+tag))
            default=next((r for r in refs if r.get(qn('w:type'))=='default'),None)
            if default is not None:
                for ref in refs:
                    section._sectPr.remove(ref)
                references.append(deepcopy(default))
        for ref in reversed(references):
            section._sectPr.insert(0,ref)
        page_type=section._sectPr.find(qn('w:type'))
        if page_type is not None:
            section._sectPr.remove(page_type)
            section._sectPr.insert(len(references),page_type)
        header=section.header
        if header.part.partname in seen_headers:
            continue
        seen_headers.add(header.part.partname)
        for p in header._element.xpath('.//w:p'):
            if tr('CONFIDENTIAL - WITHOUT PREJUDICE') in ''.join(p.xpath('.//w:t/text()')):
                number=deepcopy(p);set_text(number,f"{'Informe No.' if content.language=='ES' else 'Cert. No.'} {row['report_number']}");p.addprevious(number)
                break
    setting = OxmlElement('w:updateFields'); setting.set(qn('w:val'), 'true')
    doc.settings.element.append(setting)
    from services.web_docx_layout import fit_web_docx
    fit_web_docx(doc)
    if row.get('kind') in ('port_captancy','crane'):
        for section in doc.sections:
            for tag in ('headerReference','footerReference'):
                default=next((r for r in section._sectPr.findall(qn('w:'+tag)) if r.get(qn('w:type'))=='default'),None)
                if default is None:continue
                for typ in ('first','even'):
                    ref=deepcopy(default);ref.set(qn('w:type'),typ);default.addnext(ref)
    output = BytesIO(); doc.save(output)
    return output.getvalue()

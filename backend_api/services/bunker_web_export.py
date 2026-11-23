"""Request-local Bunker exports. Original desktop templates are never saved.

MSL retains its workbook artwork. Overflow tanks get explicit continuation
pages; the first calculation page totals every tank. MCI uses its retained
general report letterhead, not the MSL certificate.
"""
from copy import copy, deepcopy
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import tempfile
import re
import textwrap
from datetime import date, datetime

from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.worksheet.pagebreak import RowBreak, ColBreak
from services.bunker_web_fields import SPEC, NUMERIC, normalize
from services.container_web_export import convert

TEMPLATES=Path(__file__).resolve().parents[1]/'templates'


def text(value):
    return '' if value is None else str(value)


def put(sheet,address,value,numeric=False):
    cell=sheet[address]
    if numeric and value is not None and value!='' and value!='EMPTY':
        cell.value=float(Decimal(str(value)))
    else:
        cell.value=text(value);cell.data_type='s'


def clock(data,prefix):
    parts=[text(data.get(prefix+'_'+p)) for p in ('hour','minute')]
    return ':'.join(parts) if all(parts) else ''


def chronology(data):
    """Narrative is populated from facts only; no sample condition findings."""
    typ=text(data.get('certificate')).replace('_',' ')
    arrival=text(data.get('antecedent_arrived_dt'))
    start=text(data.get('antecedent_survey_date_from'))
    end=text(data.get('antecedent_survey_date_to'))
    def stamp(day,hour):return day+(' at '+hour+' LT' if hour else '')
    return {
        'B13':f"Vessel arrived to {text(data.get('antecedent_arrived_port'))} on {stamp(arrival,clock(data,'berthing'))}." if arrival else '',
        'B14':f"On {stamp(start,':'.join(text(data.get('antecedent_survey_'+p+'_from')) for p in ('hour','minute')).strip(':'))}, the undersigned Marine Surveyor started the {typ} Survey." if start else '',
        'B15':f"Survey completed on {stamp(end,':'.join(text(data.get('antecedent_survey_'+p+'_to')) for p in ('hour','minute')).strip(':'))}." if end else '',
        'B17':'The Bunker Survey was carried out jointly with '+text(data['inspection_with'])+'.' if data.get('inspection_with') else '',
        'B26':f"DLOSP at {', '.join(text(data.get(k)) for k in ('dslop_port','dslop_country') if data.get(k))} on {stamp(text(data.get('dslop_date')),clock(data,'dslop'))}." if data.get('dslop_date') else '',
    }


def msl_excel(data,target):
    data,result=normalize(data,strict=True)
    book=load_workbook(TEMPLATES/'on_off_spot_template.xlsx')
    try:
        db=book['Data from DB']
        mapping={str(db.cell(r,1).value):r for r in range(2,db.max_row+1) if db.cell(r,1).value}
        for key,r in mapping.items():
            put(db,f'B{r}',data.get(key),key in NUMERIC)
            if SPEC['fields'].get(key,{}).get('type')=='date' and data.get(key):
                db[f'B{r}']=date.fromisoformat(str(data[key])[:10])
                db[f'B{r}'].number_format='yyyy-mm-dd'
        for fuel in ('vlsfo','mgo'):
            for i in range(1,21):
                prefix=f'{fuel}_tank_{i}_'
                ref=lambda suffix:f"B{mapping[prefix+suffix]}"
                volume,temp,density,gauge=(ref(k) for k in ('volume_m3','temp_c','density_15c','gauge_mtrs'))
                empty=f'OR({volume}="EMPTY",AND(OR({volume}="",{volume}=0),{gauge}="EMPTY"))'
                for suffix,formula in [('temp_f',f'=ROUND({ref("temp_c")}*1.8+32,2)'),
                    ('weight_mt',f'=IF({empty},0,IF(COUNT({volume},{temp},{density})=3,ROUND({volume}*({density}-(0.00063*({temp}-15))),2),NA()))')]:
                    if data.get(prefix+suffix) is not None:db[ref(suffix)]=formula
        calc=book['CALCULATIONS']
        columns=dict(name='A',dist_mtrs='D',gauge_mtrs='E',volume_m3='F',temp_c='G',temp_f='H',density_15c='I',weight_mt='J')
        def map_tanks(sheet,fuel,indices,rows):
            for row,index in zip(rows,indices):
                for suffix,col in columns.items():
                    key=f'{fuel}_tank_{index}_{suffix}'
                    if data.get(key) is None or data.get(key)=='':put(sheet,f'{col}{row}','')
                    else:sheet[f'{col}{row}']=f"='Data from DB'!B{mapping[key]}"
        map_tanks(calc,'vlsfo',range(1,12),range(11,22))
        map_tanks(calc,'mgo',range(1,4),range(29,32))
        for fuel,cell in [('vlsfo','J22'),('mgo','J32')]:
            refs=','.join(f"'Data from DB'!B{mapping[f'{fuel}_tank_{i}_weight_mt']}" for i in range(1,21))
            calc[cell]=f'=ROUND(SUM({refs}),2)'
        calc['E34']='=J22+J32'
        put(calc,'J6','LIST = '+text(data.get('list')))
        put(calc,'I6','TRIM = '+text(data.get('trim')))
        put(calc,'A36','Totals include all tanks and continuation pages.')
        put(calc,'A42',data.get('surveyor_name'))
        put(calc,'E42',data.get('chief_engineer_name'))
        put(calc,'I42',data.get('master_name'))
        # Spreadsheet template has scratchpad interpolation outside A:K; those
        # examples are not connected to measurements and must not be printed.
        continuations=[]
        last={fuel:max([t['index'] for t in result['tanks'] if t['fuel']==fuel] or [0]) for fuel in ('vlsfo','mgo')}
        pages=max((max(0,last['vlsfo']-11)+10)//11,(max(0,last['mgo']-3)+2)//3)
        for page in range(1,pages+1):
            sheet=book.copy_worksheet(calc);sheet.title=f'TANKS {page+1}'
            # openpyxl does not copy images when copying worksheets.
            for image in calc._images:sheet.add_image(deepcopy(image))
            for row in list(range(11,22))+list(range(29,32)):
                for col in columns.values():put(sheet,f'{col}{row}','')
            map_tanks(sheet,'vlsfo',range(page*11+1,min(21,(page+1)*11+1)),range(11,22))
            map_tanks(sheet,'mgo',range(page*3+1,min(21,(page+1)*3+1)),range(29,32))
            sheet['J22']='=SUM(J11:J21)';sheet['J32']='=SUM(J29:J31)'
            put(sheet,'A36',f'Continuation {page}: page subtotal only. Grand totals on CALCULATIONS.')
            continuations.append(sheet)
        cert=book['CERTIFICATE'];typ=text(data.get('certificate')).replace('_',' ')
        put(cert,'C7',typ+' CERTIFICATE')
        put(cert,'A10',f'carried out a {typ} Bunker Survey in the')
        put(cert,'B13',f"Vessel arrived to {text(data.get('antecedent_arrived_port'))} on {text(data.get('antecedent_arrived_dt'))}.")
        put(cert,'B14',f"On {text(data.get('antecedent_survey_date_from'))} at {text(data.get('antecedent_survey_hour_from'))}:{text(data.get('antecedent_survey_minute_from'))} LT, the undersigned Marine Surveyor started the {typ} Survey.")
        if not data.get('antecedent_survey_date_from'):put(cert,'B14','')
        if not data.get('antecedent_survey_date_to'):put(cert,'B15','')
        if not data.get('antecedent_arrived_dt'):put(cert,'B13','')
        put(cert,'I26',typ)
        if data.get('inspection_with'):
            put(cert,'B17','The Bunker Survey was carried out jointly with '+text(data['inspection_with'])+'.')
            put(cert,'B18','')
        for cell,value in chronology(data).items():put(cert,cell,value)
        for cell in ('B18','B19','B20','B37','B38'):put(cert,cell,'')
        put(cert,'A9',f"At the request of {text(data.get('client'))}, the undersigned MSL Marine Surveyor,")
        put(cert,'A40',data.get('surveyor_name'))
        put(cert,'H40',data.get('master_name'))
        put(cert,'B33',data.get('dslop_date'))
        put(cert,'C33',clock(data,'dslop'))
        put(cert,'J29','')
        for i,row in enumerate(range(29,33),1):
            for suffix,col in [('name','A'),('ifo','C'),('vlsfo','F'),('lsmgo','J')]:
                put(cert,f'{col}{row}',data.get(f'bunker_figure_{i}_{suffix}'),suffix!='name')
            put(cert,f'I{row}','')
        for fuel,cell,formula in [('vlsfo','F33','=SUM(F28,F30:F31)'),('mgo','J33','=SUM(J28,J30:J31)')]:
            if result['dlosp'][fuel] is None:put(cert,cell,'')
            else:cert[cell]=formula
        if data.get('certificate')=='OFF_HIRE':
            put(cert,'A35',f"Vessel was redelivered from Charterers ({text(data.get('charterers_name'))}) to Owners ({text(data.get('owner_name'))})")
        elif data.get('certificate')=='ON_HIRE':
            put(cert,'A35',f"Vessel was delivered from Owners ({text(data.get('owner_name'))}) to Charterers ({text(data.get('charterers_name'))})")
        else:put(cert,'A35','')
        log=book['LOG BOOK FIGURES']
        for row,prefix in zip((10,12,14,16,18),('log_eosp','log_pob','log_fwe','log_bunker','log_at_survey')):
            put(log,f'D{row}',data.get(prefix+'_date'))
            put(log,f'E{row}',clock(data,prefix))
            for col,fuel in zip('GHIJ',('vlsfo','hfso','mdo','lsmgo')):put(log,f'{col}{row}',data.get(prefix+'_'+fuel),True)
        log['G18']="='CALCULATIONS'!J22";log['J18']="='CALCULATIONS'!J32"
        for row,prefix in zip((26,27,29,30),('cons_sea_loaded','cons_sea_ballast','cons_port_ship_gear','cons_port_shore_gear')):
            for col,fuel in zip('FGHI',('vlsfo','hfso','mdo','lsmgo')):put(log,f'{col}{row}',data.get(prefix+'_'+fuel),True)
        for cell,key in [('A36','surveyor_name'),('D36','chief_engineer_name'),('H36','master_name')]:put(log,cell,data.get(key))
        visible=[cert,calc,*continuations,log]
        # Preserve all ten free figures, not just the four on the legacy cover.
        if any(data.get(f'bunker_figure_{i}_{s}') not in (None,'') for i in range(5,11) for s in ('name','ifo','vlsfo','lsmgo')):
            annex=book.copy_worksheet(cert);annex.title='FIGURES CONTINUED'
            for image in cert._images:annex.add_image(deepcopy(image))
            for row in range(9,39):
                for cell in annex[row]:
                    if cell.__class__.__name__!='MergedCell':put(annex,cell.coordinate,'')
            put(annex,'A12','ADDITIONAL DECLARED BUNKER FIGURES (MT)')
            for col,label in [('A','Figure'),('D','IFO'),('F','VLSFO'),('J','LSMGO')]:put(annex,col+'14',label)
            for i,row in enumerate(range(16,22),5):
                for suffix,col in [('name','A'),('ifo','D'),('vlsfo','F'),('lsmgo','J')]:put(annex,f'{col}{row}',data.get(f'bunker_figure_{i}_{suffix}'),suffix!='name')
            visible.append(annex)
        remarks=text(data.get('remarks'))
        if len(remarks)>110 or '\n' in remarks:
            put(cert,'B22','See Remarks continuation.')
            lines=[]
            for line in remarks.splitlines():lines.extend(textwrap.wrap(line,width=95,replace_whitespace=False) or [''])
            for start in range(0,len(lines),24):
                note=book.copy_worksheet(cert);note.title=f'REMARKS {start//24+1}'
                for image in cert._images:note.add_image(deepcopy(image))
                for merged in list(note.merged_cells.ranges):
                    if 9<=merged.min_row<=39:note.unmerge_cells(str(merged))
                for row in range(9,40):
                    for cell in note[row]:put(note,cell.coordinate,'')
                put(note,'C7','REMARKS / '+str(start//24+1))
                for row,line in enumerate(lines[start:start+24],10):
                    note.merge_cells(start_row=row,start_column=1,end_row=row,end_column=12)
                    put(note,f'A{row}',line);note.row_dimensions[row].height=17
                    font=copy(note[f'A{row}'].font);font.size=10;font.bold=False;note[f'A{row}'].font=font
                visible.append(note)
        # Wrap only wide narrative cells. Global wrapping would truncate the
        # original unmerged labels and distort the desktop design.
        for address in ('A9:L9','B13:L13','B14:L14','B15:L15','B17:L17','B18:L18','B26:H26','A35:L36'):
            cert.merge_cells(address)
            cell=cert[address.split(':')[0]];alignment=copy(cell.alignment);alignment.wrap_text=True;cell.alignment=alignment
            value=text(cell.value)
            if not value.startswith('='):cert.row_dimensions[cell.row].height=max(cert.row_dimensions[cell.row].height or 15,14*((len(value)+104)//105))
        for sheet in list(book):
            if sheet not in visible and sheet!=db:book.remove(sheet)
        for sheet in [calc,*continuations]:
            # The right-hand scratchpad is sample calibration data, not vessel
            # inputs. It has no dependency from the printed calculations.
            sheet.delete_cols(12,max(1,sheet.max_column-11))
            for row in list(range(11,22))+list(range(29,32)):
                sheet[f'F{row}'].number_format='0.000'
                sheet[f'I{row}'].number_format='0.0000'
                sheet[f'J{row}'].number_format='0.00'
        for sheet in book:
            sheet.sheet_state='visible' if sheet in visible else 'hidden'
        book._sheets=visible+[s for s in book if s not in visible]
        for sheet in visible:
            sheet.print_area='A1:K46' if sheet in [calc,*continuations] else 'A1:J39' if sheet==log else 'A1:L44'
            sheet.row_breaks=RowBreak();sheet.col_breaks=ColBreak()
            sheet.sheet_properties.pageSetUpPr.fitToPage=True
            sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=1
            sheet.page_setup.scale=None
            sheet.oddFooter.left.text=f"{text(data.get('bunker_cert_no'))} / {text(data.get('ship_name'))} / {typ}"
            sheet.oddFooter.center.text=''
            sheet.oddFooter.right.text='Page &P of &N'
            for row in sheet:
                for cell in row:
                    if cell.data_type=='f':
                        match=re.fullmatch(r"=\+?'Data from DB'!B(\d+)",cell.value)
                        if match and db[f'B{match[1]}'].value in (None,''):put(sheet,cell.coordinate,'')
            # Long report identifiers must stay inside the printable area.
            header='J1' if sheet in [calc,*continuations] else 'H1' if sheet==cert or sheet.title=='FIGURES CONTINUED' else 'I1'
            alignment=copy(sheet[header].alignment);alignment.shrinkToFit=True;sheet[header].alignment=alignment
        book.save(target)
    finally:book.close()


def mci_word(data,target,language='EN',presentation=False,*,company='MCI-CR'):
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from services.mci_survey_export import build_word,set_text
    from services.web_docx_layout import fit_web_docx
    from services.bunker_web_language import label
    data,result=normalize(data,strict=True)
    if company=='MSL-CR':
        # The presentation has full-page artwork. The report instead retains
        # the compact letterhead from the MSL calculation/certificate template.
        doc=Document()
        section=doc.sections[0]
        section.page_width=Inches(8.5);section.page_height=Inches(11)
        section.left_margin=section.right_margin=Inches(.7)
        section.top_margin=Inches(1.25);section.bottom_margin=Inches(.65)
        section.header_distance=Inches(.35)
        template=load_workbook(TEMPLATES/'on_off_spot_template.xlsx')
        try:
            artwork=next(im for im in template['CALCULATIONS']._images if im.anchor._from.row==0)
            section.header.paragraphs[0].add_run().add_picture(BytesIO(artwork._data()),width=Inches(4))
        finally:template.close()
        section.footer.paragraphs[0].text=text(data.get('bunker_cert_no'))+' / '+text(data.get('ship_name'))
        doc.add_paragraph(text(data.get('certificate')).replace('_',' ')+' BUNKER SURVEY',style='Heading 1')
        doc.add_paragraph('CERT No. '+text(data.get('bunker_cert_no')))
        for name in ('Table Grid','Heading 2'):
            if name not in doc.styles:
                doc.styles.element.append(deepcopy(Document().styles[name].element))
        info=doc.add_table(rows=0,cols=2);info.style='Table Grid'
        for key in ('ship_name','client','port_of_registry','gross_tonnage','port','country','report_date'):
            cells=info.add_row().cells;cells[0].text=SPEC['fields'][key]['label'];cells[1].text=text(data.get(key))
        anchor=doc.add_paragraph()._p
    else:
        doc=Document(BytesIO(build_word(dict(company_code='MCI-CR',kind='bunker',vessel=text(data.get('ship_name')),
        requested_by=text(data.get('client')),report_number=text(data.get('bunker_cert_no')),
        location=', '.join(text(data.get(k)) for k in ('port','country') if data.get(k)),
        content=dict(language=language,surveyor=text(data.get('surveyor_name')),master=text(data.get('master_name')),
                     issue_date=data.get('report_date'),report_status=text(data.get('status')),length_and_tonnage=text(data.get('gross_tonnage')))))))
        set_text(doc.paragraphs[2],('INSPECCION DE COMBUSTIBLE' if language=='ES' else 'BUNKER SURVEY')+' / '+text(data.get('certificate')).replace('_',' ')+'\n'+', '.join(text(data.get(k)) for k in ('port','country') if data.get(k)))
        anchor=doc.paragraphs[4]._p
        if presentation:
            clean_section=deepcopy(doc.sections[0]._sectPr)
            body=doc._element.body
            keep=list(body).index(doc.tables[0]._tbl)
            for element in list(body)[keep+1:]:body.remove(element)
            body.append(clean_section)
            fit_web_docx(doc);doc.save(target);return
    def table(title,headers,rows):
        p=doc.add_paragraph(title,style='Heading 2');anchor.addprevious(p._p)
        t=doc.add_table(rows=1,cols=len(headers))
        t.style=doc.tables[0].style
        if len(headers)==8:
            widths=(2.2,1,1,1.1,.7,.7,1.3,1)
            section=doc.sections[0];available=int(section.page_width-section.left_margin-section.right_margin)//635
            for col,weight in zip(t._tbl.tblGrid,widths):col.set(qn('w:w'),str(round(available*weight/sum(widths))))
        borders=OxmlElement('w:tblBorders')
        for side in ('top','left','bottom','right','insideH','insideV'):
            border=OxmlElement('w:'+side);border.set(qn('w:val'),'single');border.set(qn('w:sz'),'4');border.set(qn('w:color'),'CCD8DF');borders.append(border)
        t._tbl.tblPr.append(borders)
        for cell,label in zip(t.rows[0].cells,headers):cell.text=label
        for cell in t.rows[0].cells:
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'DCE6F1');cell._tc.get_or_add_tcPr().append(shade)
        repeat=OxmlElement('w:tblHeader');t.rows[0]._tr.get_or_add_trPr().append(repeat)
        for row in rows:
            for cell,value in zip(t.add_row().cells,row):cell.text=text(value)
        for row in t.rows:
            if sum(len(text(v)) for v in (cell.text for cell in row.cells))<600:
                row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.space_after=Pt(3)
                    p.paragraph_format.space_before=Pt(3)
                    for run in p.runs:run.font.size=Pt(8)
        if len(t.rows)<=6:
            for row in t.rows[:-1]:
                for cell in row.cells:
                    for p in cell.paragraphs:p.paragraph_format.keep_with_next=True
        anchor.addprevious(t._tbl)
    if not presentation:
        particulars=[[label(SPEC['fields'][key]['label'],language),data.get(key)] for key in ('port_of_registry','gross_tonnage','report_category') if data.get(key) not in (None,'')]
        if particulars:table('Caracteristicas del buque' if language=='ES' else 'Vessel particulars',[label('Field',language),label('Value',language)],particulars)
        for fuel in ('vlsfo','mgo'):
            rows=[]
            for tank in result['tanks']:
                if tank['fuel']!=fuel:continue
                prefix=f"{fuel}_tank_{tank['index']}_"
                rows.append([data.get(prefix+k) for k in ('name','dist_mtrs','gauge_mtrs','volume_m3','temp_c','temp_f','density_15c','weight_mt')])
            if rows:table(fuel.upper(),['Tanque' if language=='ES' else 'Tank','Dist. m','Sonda m' if language=='ES' else 'Gauge m','m3','C','F','t/m3 @15C','MT'],rows)
        table('TOTALES' if language=='ES' else 'TOTALS',['','VLSFO MT','MGO MT'],[
            ['ROB',result['totals']['vlsfo'],result['totals']['mgo']],['DLOSP',result['dlosp']['vlsfo'],result['dlosp']['mgo']]])
        p=doc.add_paragraph('Total ROB: '+result['total_mt']+' MT');anchor.addprevious(p._p)
        # Only populate submitted content; never carry facts or signatures from samples.
        for group in SPEC['sections']:
            if group.get('tank_fuel') or group['title']=='Service':continue
            rows=[[label(f['label'],language),label(text(data.get(f['key'])),language) if f['key'].startswith('bunker_figure_') and f['key'].endswith('_name') else data.get(f['key'])] for f in group['fields'] if data.get(f['key']) not in (None,'')]
            if rows:table(label(group['title'],language),[label('Field',language),label('Value',language)],rows)
    fit_web_docx(doc);doc.save(target)


def msl_word(data,target):
    """Editable Word report using the retained MSL Bunker letterhead."""
    mci_word(data,target,'EN',company='MSL-CR')


def cover(data,target):
    from docx import Document
    from docx.text.paragraph import Paragraph
    from services.draft_survey_report_formatting import replace_placeholders
    from services.template_autofit import apply_docx_autofit
    doc=Document(TEMPLATES/'presentation_bunker.docx')
    replacements={'{'+key+'}':text(data.get(key)).replace('_',' ') if key=='certificate' else text(data.get(key)) for key in SPEC['fields']}
    for part in [doc,*[p for s in doc.sections for p in (s.header,s.footer)]]:
        for element in part._element.xpath('.//w:p'):replace_placeholders(Paragraph(element,part),replacements)
    apply_docx_autofit(doc);doc.save(target)


def mci_excel(data,target,language='EN'):
    from openpyxl import Workbook
    from openpyxl.styles import Font,PatternFill
    from openpyxl.drawing.image import Image
    from branding import logo_asset
    from services.bunker_web_language import label
    data,result=normalize(data,strict=True)
    book=Workbook();summary=book.active;summary.title='Bunker'
    sheets={fuel:book.create_sheet(fuel.upper()) for fuel in ('vlsfo','mgo')}
    for fuel,sheet in sheets.items():
        headers=[label('Tank',language),label('Distance (m)',language),label('Gauge (m)',language),'m3','C','t/m3 @15C','F','MT']
        for c,value in enumerate(headers,1):put(sheet,f'{chr(64+c)}4',value)
        for i in range(1,21):
            row=i+4;prefix=f'{fuel}_tank_{i}_'
            for col,key in zip('ABCDEF',('name','dist_mtrs','gauge_mtrs','volume_m3','temp_c','density_15c')):
                put(sheet,f'{col}{row}',data.get(prefix+key),key in ('volume_m3','temp_c','density_15c'))
            if data.get(prefix+'temp_f') is not None:
                sheet[f'G{row}']=f'=ROUND(E{row}*1.8+32,2)'
            if data.get(prefix+'weight_mt') is not None:
                sheet[f'H{row}']=f'=IF(OR(D{row}="EMPTY",AND(OR(D{row}="",D{row}=0),C{row}="EMPTY")),0,IF(COUNT(D{row},E{row},F{row})=3,ROUND(D{row}*(F{row}-(0.00063*(E{row}-15))),2),NA()))'
        put(sheet,'A26','TOTAL MT');sheet['H26']='=ROUND(SUM(H5:H24),2)'
        sheet.freeze_panes='D5';sheet.auto_filter.ref='A4:H24';sheet.print_area='A1:H27'
    for row,key in enumerate(('bunker_cert_no','ship_name','client','port','country','report_date'),2):
        put(summary,f'A{row}',SPEC['fields'][key]['label'] if language=='EN' else label(SPEC['fields'][key]['label'],language))
        summary.merge_cells(start_row=row,start_column=2,end_row=row,end_column=4);put(summary,f'B{row}',data.get(key))
    for col,value in [('A','ROB'),('C','VLSFO MT'),('D','MGO MT')]:put(summary,col+'8',value)
    summary['C9']="='VLSFO'!H26";summary['D9']="='MGO'!H26"
    put(summary,'A10',label('Survey type',language));summary.merge_cells('B10:D10');put(summary,'B10',text(data.get('certificate')).replace('_',' '))
    for col,value in zip('ABCD',(label('Figure',language),'IFO MT','VLSFO MT','LSMGO MT')):put(summary,col+'11',value)
    for i in range(1,11):
        for col,suffix in zip('ABCD',('name','ifo','vlsfo','lsmgo')):
            value=data.get(f'bunker_figure_{i}_{suffix}')
            put(summary,f'{col}{i+11}',label(text(value),language) if suffix=='name' else value,suffix!='name')
    put(summary,'A23','DLOSP MT')
    for col,fuel in [('C','vlsfo'),('D','mgo')]:
        if result['dlosp'][fuel] is not None:summary[col+'23']=f'=SUM({col}9,{col}13:{col}14)'
    put(summary,'A24','Total ROB MT');summary['C24']='=SUM(C9:D9)'
    summary.print_area='A1:D25'
    details=book.create_sheet('Data')
    for col,value in zip('ABC',(label('Key',language),label('Field',language),label('Value',language))):put(details,col+'3',value)
    populated=[(key,f) for key,f in SPEC['fields'].items() if data.get(key) not in (None,'') and '_tank_' not in key]
    for row,(key,f) in enumerate(populated,4):
        put(details,f'A{row}',key);put(details,f'B{row}',label(f['label'],language));put(details,f'C{row}',data.get(key),key in NUMERIC)
        if key=='log_at_survey_vlsfo':details[f'C{row}']="='VLSFO'!H26"
        if key=='log_at_survey_lsmgo':details[f'C{row}']="='MGO'!H26"
    details.freeze_panes='C4'
    details.print_area=f'A1:C{details.max_row}'
    for sheet in book:
        sheet.sheet_view.showGridLines=False
        sheet.row_dimensions[1].height=65
        logo=logo_asset({'company_code':'MCI-CR'})
        if not logo:raise ValueError('MCI logo required')
        image=Image(logo);image.height=image.height*75/image.width;image.width=75;sheet.add_image(image,'A1')
        sheet.merge_cells(start_row=1,start_column=2,end_row=1,end_column=4 if sheet==summary else 3 if sheet==details else 8)
        sheet['B1']='MARINE CLAIMS & RISK INTELLIGENCE / '+sheet.title
        sheet['B1'].font=Font(name='Arial',bold=True,size=12,color='173F50')
        for col in 'ABCDEFGH':sheet.column_dimensions[col].width=18 if col!='A' else 30
        if sheet==details:sheet.column_dimensions['A'].width=42;sheet.column_dimensions['B'].width=38;sheet.column_dimensions['C'].width=65
        for row in sheet.iter_rows(min_row=2):
            for cell in row:
                cell.font=Font(name='Arial',size=10)
                cell.alignment=Alignment(vertical='top',wrap_text=True)
                if cell.data_type in ('n','f'):cell.number_format='0.00'
        if sheet in sheets.values():
            for row in range(5,25):
                sheet[f'D{row}'].number_format='0.000'
                sheet[f'F{row}'].number_format='0.0000'
        if sheet==details:
            for row in range(4,details.max_row+1):
                details[f'C{row}'].number_format='0.########'
                details.row_dimensions[row].height=30
        if sheet==summary:
            for row in range(12,22):sheet.row_dimensions[row].height=30
        for row in ((8,11,23) if sheet==summary else (3,) if sheet==details else (4,26)):
            for cell in sheet[row]:
                cell.fill=PatternFill('solid',fgColor='DCE6F1');cell.font=Font(name='Arial',size=10,bold=True,color='173F50')
        sheet.oddFooter.left.text=text(data.get('bunker_cert_no'))
        sheet.oddFooter.right.text='Page &P of &N'
        sheet.sheet_properties.pageSetUpPr.fitToPage=True;sheet.page_setup.fitToWidth=1;sheet.page_setup.fitToHeight=0
    book.save(target);book.close()


def build(data,format,language='EN'):
    if data.get('company_code') not in ('MSL-CR','MCI-CR'):raise ValueError('Company required')
    if format not in ('word','excel','pdf','presentation','complete'):raise ValueError('Unsupported format')
    with tempfile.TemporaryDirectory(prefix='som_bunker_web_') as directory:
        folder=Path(directory);mci=data['company_code']=='MCI-CR'
        if not mci and format=='word':
            path=folder/'report.docx';msl_word(data,path);return path.read_bytes()
        if mci and format=='excel':
            path=folder/'calculations.xlsx';mci_excel(data,path,language);return path.read_bytes()
        if format in ('presentation','complete'):
            path=folder/'presentation.docx'
            if mci:mci_word(data,path,language,True)
            else:cover(data,path)
            cover_pdf=convert(path,folder)
            if format=='presentation':return cover_pdf.read_bytes()
        path=folder/('report.docx' if mci else 'report.xlsx')
        if mci:mci_word(data,path,language)
        else:msl_excel(data,path)
        if format in ('word','excel'):return path.read_bytes()
        report_pdf=convert(path,folder)
        if format=='pdf':return report_pdf.read_bytes()
        from services.port_captancy_bundle import merge
        return merge(cover_pdf.read_bytes(),[report_pdf.read_bytes()])

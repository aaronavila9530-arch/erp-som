"""Deterministic MCI template localization; never translate surveyor narratives."""
import re

ES = {
    'PROFESSIONAL TECHNICAL REPORT': 'INFORME TECNICO PROFESIONAL',
    'Vessel Survey': 'Inspeccion de buque', 'Vessel Condition Survey': 'Inspeccion de condicion del buque',
    'Cargo Condition Survey': 'Inspeccion de condicion de la carga',
    'Logistics Supervision': 'Supervision logistica', 'Port Captancy': 'Supervision de operaciones portuarias',
    'Crane Inspections': 'Inspeccion de gruas', 'Survey Report': 'Informe de inspeccion',
    'CONTAINER SURVEY REPORT': 'INFORME DE INSPECCION DE CONTENEDOR',
    'CONTAINER SURVEY': 'INSPECCION DE CONTENEDOR',
    'INSTRUCTIONS, SCOPE AND METHODOLOGY': 'INSTRUCCIONES, ALCANCE Y METODOLOGIA',
    'Work performed': 'Trabajo realizado', 'Main limitations of this report': 'Principales limitaciones del informe',
    'Time and place of arrival and chronology of events': 'Fecha y lugar de llegada y cronologia de los hechos',
    'Representatives': 'Representantes', 'SURVEY FINDINGS': 'HALLAZGOS DE LA INSPECCION',
    'Visual inspection': 'Inspeccion visual', 'Documentation provided': 'Documentacion proporcionada',
    'Documentation not provided': 'Documentacion no proporcionada', 'CONCLUSION': 'CONCLUSION',
    'ENCLOSURE': 'ANEXO', 'ENCLOSURES': 'ANEXOS', 'Picture link': 'Enlace de fotografias',
    'Prepared for': 'Preparado para', 'Vessel / IMO': 'Buque / IMO',
    'Length overall and tonnage': 'Eslora total y tonelaje', 'Cargo': 'Carga',
    'Period investigated': 'Periodo investigado', 'Date of issue': 'Fecha de emision',
    'Report status': 'Estado del informe', 'Draft': 'Borrador',
    'Final - Confidential / Without Prejudice': 'Final - Confidencial / Sin perjuicio',
    'Master': 'Capitan', 'Chief officer': 'Primer oficial', 'Surveyor': 'Inspector',
    'VESSEL PARTICULARS': 'DATOS DEL BUQUE', 'SUPERVISION PROCESS': 'PROCESO DE SUPERVISION',
    'Documentary findings': 'Hallazgos documentales', 'Operational control findings': 'Hallazgos del control operativo',
    'Incidents': 'Incidentes', 'OPERATION SUMMARY': 'RESUMEN DE OPERACIONES', 'REMARKS': 'OBSERVACIONES',
    'Extract time sheet': 'Resumen cronologico', 'EXTRACT TIME SHEET': 'RESUMEN CRONOLOGICO',
    'Vessel': 'Buque', 'Flag / port of registry': 'Bandera / puerto de registro', 'Year built': 'Ano de construccion',
    'Arrival': 'Llegada', 'Inspection': 'Inspeccion', 'Inspection date': 'Fecha de inspeccion',
    'Supervision completed': 'Supervision finalizada', 'Survey scope': 'Alcance de inspeccion',
    'Operation': 'Operacion', 'Continent': 'Continente', 'Vessel arrival': 'Llegada del buque',
    'NOR tendered': 'Presentacion del aviso de alistamiento', 'All fast': 'Amarre completado',
    'Supervision commenced': 'Inicio de supervision',
    'Introduction': 'Introduccion', 'INTRODUCTION': 'INTRODUCCION', 'Purpose': 'Proposito',
    'Instructions': 'Instrucciones', 'PARTICULARS': 'DATOS GENERALES',
    'DETAILS OF DAMAGE / SHORTAGE (IF ANY) OR INSPECTION CAUSE': 'DETALLES DE DANOS / FALTANTES (SI LOS HUBIERE) O MOTIVO DE INSPECCION',
    'SURVEY LINK PICTURES': 'ENLACE DE FOTOGRAFIAS DE LA INSPECCION',
    'Survey requested by': 'Inspeccion solicitada por', 'On behalf of': 'En representacion de',
    'Receiver Representative': 'Representante del receptor', 'MCI Surveyor': 'Inspector de MCI',
    'Container': 'Contenedor', 'Quantity': 'Cantidad', 'Gross weight': 'Peso bruto',
    'Shipper': 'Embarcador', 'Consignee': 'Consignatario', 'Port of loading': 'Puerto de carga',
    'Port of Discharge': 'Puerto de descarga', 'Vessel / voyage': 'Buque / viaje',
    'Container opening': 'Apertura del contenedor', 'Survey place': 'Lugar de inspeccion',
    'Surveyor arrived': 'Llegada del inspector', 'Container opened': 'Apertura del contenedor',
    'CRANES GEAR SURVEY': 'INSPECCION DEL EQUIPO DE GRUAS', 'Condition': 'Condicion',
    'Hoisting and luffing wires': 'Cables de izado y de abatimiento', 'Sheaves': 'Poleas',
    'Operability': 'Operatividad', 'CRANE INSPECTION': 'INSPECCION DE GRUA',
    'REMARKS BY CRANE': 'OBSERVACIONES POR GRUA', 'RECOMMENDATIONS': 'RECOMENDACIONES',
    'GRABS CONDITION SURVEY': 'INSPECCION DE CONDICION DE CUCHARAS',
    'Crane Access': 'Acceso a la grua', 'Crane machinery space': 'Espacio de maquinaria de la grua',
    'Crane operator cabin': 'Cabina del operador', 'Crane jib head sheaves': 'Poleas de cabeza de pluma',
    'Hoisting wire end pin': 'Pasador terminal del cable de izado',
    'Luffing wire end pin': 'Pasador terminal del cable de abatimiento',
    'Crane wire rope visual inspection': 'Inspeccion visual del cable de acero de la grua',
    'Crane housing top sheaves': 'Poleas superiores de la carcasa',
    'Luffing center sheave visual inspection': 'Inspeccion visual de la polea central de abatimiento',
    'Cargo block sheave shaft': 'Eje de polea del bloque de carga',
    'Slack hoisting wire limit': 'Limitador de cable de izado flojo',
    'Crane jib angle limits': 'Limites de angulo de pluma',
    'Crane jib angle indicator': 'Indicador de angulo de pluma',
    'Crane hoisting wire limits': 'Limites del cable de izado',
    'Pedestal / Light project': 'Pedestal / Proyector de luz',
    'Clean and no obstacles': 'Limpio y sin obstaculos', 'Clean': 'Limpio', 'Working': 'Funcionando',
    'Not working': 'No funciona', 'Greased': 'Engrasado', 'Negative impressions': 'Observaciones negativas',
    'Free to rotate / Unreadable scale': 'Giro libre / Escala ilegible', 'No trunnion': 'Sin munon',
    'Inspection performed; status not specified': 'Inspeccion realizada; estado no especificado',
    'CONFIDENTIAL - WITHOUT PREJUDICE': 'CONFIDENCIAL - SIN PERJUICIO',
    'Marine Master Surveyor': 'Inspector maritimo principal',
}
ES.update({f'Crane {i}': f'Grua {i}' for i in range(1, 5)})
# ASCII source escapes keep Spanish orthography independent of host encoding.
_ACCENTS = {'tecnico':'t\u00e9cnico','inspeccion':'inspecci\u00f3n','condicion':'condici\u00f3n',
            'supervision':'supervisi\u00f3n','logistica':'log\u00edstica','gruas':'gr\u00faas','grua':'gr\u00faa',
            'metodologia':'metodolog\u00eda','cronologia':'cronolog\u00eda','documentacion':'documentaci\u00f3n',
            'fotografias':'fotograf\u00edas','periodo':'per\u00edodo','emision':'emisi\u00f3n','capitan':'capit\u00e1n',
            'cronologico':'cronol\u00f3gico','ano':'a\u00f1o','construccion':'construcci\u00f3n',
            'operacion':'operaci\u00f3n','presentacion':'presentaci\u00f3n','introduccion':'introducci\u00f3n',
            'proposito':'prop\u00f3sito','danos':'da\u00f1os','representacion':'representaci\u00f3n',
            'angulo':'\u00e1ngulo','limites':'l\u00edmites','obstaculos':'obst\u00e1culos','munon':'mu\u00f1\u00f3n',
            'maritimo':'mar\u00edtimo','conclusion':'conclusi\u00f3n'}


def _orthography(text):
    def replace(match):
        word=match[0]
        translated=_ACCENTS.get(word.lower(),word)
        return translated.upper() if word.isupper() else translated[0].upper()+translated[1:] if word[0].isupper() else translated
    return re.sub(r'[A-Za-z]+',replace,text)


ES = {key:_orthography(value) for key,value in ES.items()}
DISCLAIMER = ('ESTE INFORME SE EMITE DE BUENA FE Y SIN PERJUICIO, PARA BENEFICIO DE QUIEN CORRESPONDA. '
              'NOS RESERVAMOS EL DERECHO DE MODIFICARLO O AMPLIARLO SI LLEGA A NUESTRO CONOCIMIENTO NUEVA INFORMACI\u00d3N.')


def translate(text, language):
    if language != 'ES':
        return text
    if text.startswith(('THIS BONA FIDE', 'THIS BONAFIDE')):
        return DISCLAIMER
    if text.startswith('This report is issued exclusively'):
        return ('Este informe se emite exclusivamente para el cliente que encarg\u00f3 la inspecci\u00f3n a MCI y sus asesores.\n'
                'No constituye una admisi\u00f3n de responsabilidad ni una opini\u00f3n jur\u00eddica.')
    match = re.fullmatch(r'(\d+(?:\.\d+)*\.?\s+)?(.*?)(:?)', text, re.S)
    prefix, body, suffix = match.groups()
    return (prefix or '') + ES.get(body, body) + suffix


def localize_template(element, language):
    """Call before inserting user data. Preserve runs, drawings and field codes."""
    if language != 'ES':
        return
    # Static phrases can be split across runs, so replace spans backwards.
    for p in element.xpath('.//w:p'):
        nodes = p.xpath('.//w:t')
        original = ''.join(n.text or '' for n in nodes)
        replacements = []
        translated = translate(original.strip(), language)
        if translated != original.strip():
            start = len(original) - len(original.lstrip())
            replacements = [(start, start + len(original.strip()), translated)]
        else:
            phrases = {**ES, 'Head Office': 'Oficina principal', 'Phone': 'Tel\u00e9fono',
                       'Contact': 'Contacto', 'site G14': 'local G14', 'Page': 'P\u00e1gina', 'of': 'de'}
            pattern = re.compile(r'(?<!\w)(' + '|'.join(re.escape(k) for k in sorted(phrases, key=len, reverse=True)) + r')(?!\w)')
            replacements = [(m.start(), m.end(), phrases[m[0]]) for m in pattern.finditer(original)]
        for start, end, value in reversed(replacements):
            offset = 0
            spans = []
            for node in nodes:
                length = len(node.text or '')
                spans.append((node, offset, offset + length))
                offset += length
            first = True
            for node, left, right in spans:
                if right <= start or left >= end:
                    continue
                text = node.text or ''
                node.text = text[:max(0, start-left)] + (value if first else '') + text[min(len(text), end-left):]
                first = False


def localize_document(doc, language):
    localize_template(doc.element, language)
    seen = set()
    for section in doc.sections:
        for part in (section.header, section.footer):
            if part.part.partname not in seen:
                localize_template(part._element, language)
                seen.add(part.part.partname)

"""Static labels only: measured values and user narrative are never translated."""
LABELS={
    'Key':'Clave','Generator until DLOSP':'Generador hasta DLOSP',
    'Cons. Departure M.E. to Sea Buoy':'Consumo de salida del motor principal hasta boya de mar',
    'Bunker figures (signed MT)':'Cifras de combustible (MT con signo)',
    'Service':'Servicio','Survey chronology':'Cronologia de inspeccion','Delivery point':'Punto de entrega',
    'Declared figures (MT)':'Cifras declaradas (MT)','Draft and list':'Calados y escora',
    'Generator until DLOSP (signed MT)':'Generador hasta DLOSP (MT con signo)',
    'Departure M.E. to sea buoy (signed MT)':'Motor principal hasta boya de mar (MT con signo)',
    'Bunker on log book':'Combustible segun diario de maquinas','At survey':'Al momento de inspeccion',
    'Consumption: Sea / loaded':'Consumo: navegacion con carga','Consumption: Sea / ballast':'Consumo: navegacion en lastre',
    'Consumption: Port / ship gear':'Consumo: puerto con equipos del buque',
    'Consumption: Port / shore gear':'Consumo: puerto con equipos de tierra',
    'Remarks':'Observaciones','Representatives':'Representantes','Figure':'Concepto',
    'Field':'Campo','Value':'Valor','Report number':'Numero de informe','Vessel':'Buque',
    'Prepared for':'Preparado para','Port':'Puerto','Country':'Pais','Report date':'Fecha del informe',
    'Port of registry':'Puerto de registro','Gross tonnage':'Arqueo bruto','Report category':'Categoria',
    'Survey type':'Tipo de inspeccion','Draft':'Calado','Draft fwd':'Calado a proa',
    'Draft aft':'Calado a popa','Trim':'Asiento','List':'Escora','DATE':'FECHA','HOUR':'HORA','MINUTE':'MINUTO',
    'Berthing date':'Fecha de atraque','Berthing hour':'Hora de atraque','Berthing minute':'Minuto de atraque',
    'Commenced date':'Fecha de inicio','Antecedent arrived port':'Puerto de llegada',
    'Antecedent arrived dt':'Fecha de llegada','Antecedent survey date from':'Fecha inicial',
    'Antecedent survey hour from':'Hora inicial','Antecedent survey minute from':'Minuto inicial',
    'Antecedent survey date to':'Fecha final','Antecedent survey hour to':'Hora final',
    'Antecedent survey minute to':'Minuto final','Inspection with':'Inspeccion conjunta con',
    'Dslop date':'Fecha DLOSP','Dslop hour':'Hora DLOSP','Dslop minute':'Minuto DLOSP',
    'Dslop port':'Puerto DLOSP','Dslop country':'Pais DLOSP','Bunker delivery declared':'Combustible entregado declarado',
    'Rob diff':'Diferencia ROB','Plus consumption':'Mas consumo','Generator until aps':'Generador hasta APS',
    'Cons dept':'Consumo de salida','Me to sea buoy':'Motor principal hasta boya de mar',
    'Surveyor name':'Inspector','Master name':'Capitan','Chief engineer name':'Jefe de maquinas',
    'Owner name':'Armador','Charterers name':'Fletadores',
    'Tank':'Tanque','Distance (m)':'Distancia (m)','Gauge (m)':'Sonda (m)',
    'Corrected volume (m3)':'Volumen corregido (m3)','Temperature (C)':'Temperatura (C)',
    'Temperature (F)':'Temperatura (F)','Density at 15 C (t/m3)':'Densidad a 15 C (t/m3)','Weight (MT)':'Peso (MT)',
}


def label(value,language):
    if language!='ES':return value
    if value.startswith('Bunker figure '):return value.replace('Bunker figure ','Cifra de combustible ')
    if value.endswith(' tanks'):return 'Tanques '+value.removesuffix(' tanks')
    return LABELS.get(value,value)

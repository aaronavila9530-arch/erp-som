SOM_QA = [
    {
        "category": "General",
        "question": "Manual general: Que es ERP SOM y como se navega?",
        "answer": (
            "ERP SOM centraliza la operacion de servicios maritimos, informes, finanzas, "
            "comercial, HHRR, master data y dashboards.\n"
            "Paso a paso:\n"
            "1. Inicia sesion con usuario, contrasena y codigo de autenticacion cuando aplique.\n"
            "2. Usa el menu lateral para entrar al modulo autorizado por tu rol.\n"
            "3. Consulta primero Dashboards o pizarras para revisar pendientes.\n"
            "4. Entra al modulo operativo correspondiente para crear, editar, aprobar o exportar.\n"
            "5. Si un boton no aparece, normalmente es por permisos del rol o por el estado del registro.\n"
            "6. PORTIA SOM sirve para consultar y resumir datos; no modifica informacion."
        ),
    },
    {
        "category": "Dashboard",
        "question": "Manual Dashboard: Como revisar indicadores ejecutivos?",
        "answer": (
            "El dashboard resume KPIs para gerencia y seguimiento operativo.\n"
            "Paso a paso:\n"
            "1. Abre Dashboard o Centro Ejecutivo desde el menu.\n"
            "2. Selecciona filtros de ano, cliente, pais, puerto u operacion si estan disponibles.\n"
            "3. Revisa tarjetas KPI antes de interpretar graficos.\n"
            "4. En servicios, compara finalizados, pendientes y valores facturados.\n"
            "5. En finanzas, revisa facturado, cuentas por cobrar, pagos y cuentas por pagar.\n"
            "6. En comercial, revisa ingresos, margen, clientes activos, paises y puertos.\n"
            "7. Usa la tabla inferior para validar de donde sale cada grafico."
        ),
    },
    {
        "category": "Master Data",
        "question": "Manual Master Data: Como administrar clientes, proveedores, empleados y surveyors?",
        "answer": (
            "Master Data alimenta los combos y validaciones del resto del ERP.\n"
            "Paso a paso:\n"
            "1. Entra a Master Data.\n"
            "2. Selecciona la entidad: clientes, proveedores, empleados, surveyors, servicios, paises o puertos.\n"
            "3. Usa Ver para consultar todos los registros existentes.\n"
            "4. Usa Agregar para crear un registro nuevo con campos obligatorios completos.\n"
            "5. Usa Editar para modificar datos existentes sin duplicar registros.\n"
            "6. Guarda y vuelve a abrir el combo del modulo afectado para confirmar que ya aparece.\n"
            "7. Las fechas deben mostrarse en formato largo en ingles en pantalla y regularizarse al formato aceptado por base de datos al guardar."
        ),
    },
    {
        "category": "Servicios",
        "question": "Manual Servicios: Como crear un servicio y generar consecutivo?",
        "answer": (
            "Servicios es el origen operativo de facturacion e informes.\n"
            "Paso a paso:\n"
            "1. Entra a Servicios y presiona Agregar Servicio.\n"
            "2. Selecciona cliente, pais, puerto, operacion, surveyor y fechas desde los combos/calendarios.\n"
            "3. No escribas manualmente el consecutivo si la version desktop lo genera automatico.\n"
            "4. Guarda el servicio en estado inicial.\n"
            "5. Cuando corresponda, usa Generar Consecutivo para asignar num_informe segun fecha y reglas del ERP.\n"
            "6. Si editas la fecha despues, el num_informe debe actualizar los cuatro digitos centrales segun la nueva fecha.\n"
            "7. Finaliza el servicio solo cuando la operacion este completa y lista para facturacion/informes."
        ),
    },
    {
        "category": "Servicios",
        "question": "Manual Servicios: Como asignar surveyors y honorarios?",
        "answer": (
            "La asignacion de surveyors controla personal y costos por servicio.\n"
            "Paso a paso:\n"
            "1. En la tabla de Servicios, selecciona o edita el servicio.\n"
            "2. Abre Agregar Surveyor o Gestion de Surveyors.\n"
            "3. Selecciona el surveyor desde el combo cargado desde Master Data.\n"
            "4. Ingresa honorario editable cuando aplique.\n"
            "5. Agrega hasta el limite permitido por servicio.\n"
            "6. Guarda y revisa que el resumen muestre total de surveyors y honorarios totales.\n"
            "7. Si el combo aparece vacio, revisa que existan surveyors activos en Master Data."
        ),
    },
    {
        "category": "Servicios",
        "question": "Manual Servicios: Como abrir informes desde Servicios?",
        "answer": (
            "Servicios puede abrir informes creados cuando el servicio ya tiene num_informe.\n"
            "Paso a paso:\n"
            "1. Ubica un servicio finalizado en la tabla.\n"
            "2. Haz doble click sobre el registro.\n"
            "3. Si el informe existe en alguna tabla de informes, el ERP debe abrir el formulario con GET.\n"
            "4. Usa Editar para habilitar campos si necesitas corregir informacion.\n"
            "5. Usa Guardar Cambios para enviar PUT y actualizar el informe existente.\n"
            "6. Si el informe no existe, debe mantenerse pendiente en la pizarra de Informes."
        ),
    },
    {
        "category": "Finanzas",
        "question": "Manual Finanzas: Como funciona Billing?",
        "answer": (
            "Billing convierte servicios finalizados en documentos listos para facturar.\n"
            "Paso a paso:\n"
            "1. Abre Finanzas > Billing.\n"
            "2. Selecciona cliente en el filtro.\n"
            "3. El sistema busca servicios finalizados sin numero de factura.\n"
            "4. Si no hay pendientes, muestra mensaje sin pendientes por facturar.\n"
            "5. Si hay pendientes, habilita carga de XML o factura manual.\n"
            "6. Registra numero de factura, fecha, termino de pago y vencimiento.\n"
            "7. Valida que el numero largo de factura se exporte como texto para no truncarse."
        ),
    },
    {
        "category": "Finanzas",
        "question": "Manual Finanzas: Como funciona Invoicing?",
        "answer": (
            "Invoicing permite consultar y exportar facturas emitidas.\n"
            "Paso a paso:\n"
            "1. Abre Finanzas > Invoicing.\n"
            "2. Usa filtros de cliente, estado, fecha, numero de factura o moneda.\n"
            "3. Selecciona una factura para ver detalle.\n"
            "4. Exporta PDF, Word o Excel segun permisos.\n"
            "5. Si subes XML, valida que el cliente exista y que el backend acepte el payload.\n"
            "6. Los numeros de factura de 20+ digitos deben tratarse como texto en exportaciones."
        ),
    },
    {
        "category": "Finanzas",
        "question": "Manual Finanzas: Como funciona Collections?",
        "answer": (
            "Collections controla cuentas por cobrar y aplicacion de pagos.\n"
            "Paso a paso:\n"
            "1. Abre Finanzas > Collections.\n"
            "2. Usa filtros de cliente, estado, aging, fecha o factura.\n"
            "3. Revisa saldo pendiente, vencimiento y dias vencidos.\n"
            "4. Registra pagos desde Bank Reconciliation o pago manual si esta permitido.\n"
            "5. Aplica notas de credito si corresponde.\n"
            "6. Sincroniza con Accounting para generar asientos cuando el flujo lo requiera.\n"
            "7. Exporta reportes para seguimiento de cobranza."
        ),
    },
    {
        "category": "Finanzas",
        "question": "Manual Finanzas: Como funciona Bank Reconciliation?",
        "answer": (
            "Bank Reconciliation concilia movimientos bancarios contra pagos y facturas.\n"
            "Paso a paso:\n"
            "1. Abre Finanzas > Bank Reconciliation.\n"
            "2. Filtra por cliente, referencia, banco, fecha o estado.\n"
            "3. Revisa movimientos importados o registrados.\n"
            "4. Selecciona el movimiento y aplica contra collection cuando corresponda.\n"
            "5. Valida diferencia, moneda y referencia antes de guardar.\n"
            "6. Los pagos conciliados deben reflejarse en Collections e Incoming Payments."
        ),
    },
    {
        "category": "Finanzas",
        "question": "Manual Finanzas: Como funciona Invoice to Pay?",
        "answer": (
            "Invoice to Pay controla facturas de proveedores y cuentas por pagar.\n"
            "Paso a paso:\n"
            "1. Abre Finanzas > Invoice to Pay.\n"
            "2. Filtra por proveedor, estado, fechas, vencimiento o moneda.\n"
            "3. Registra factura manual o carga PDF/XML segun flujo disponible.\n"
            "4. Valida monto, balance, fecha de emision y vencimiento.\n"
            "5. Aplica pago cuando corresponda.\n"
            "6. Sincroniza con Accounting para asientos de obligacion y pago.\n"
            "7. Revisa AP pendiente desde Dashboard Finanzas o PORTIA."
        ),
    },
    {
        "category": "Finanzas",
        "question": "Manual Finanzas: Como funciona Accounting y Closing?",
        "answer": (
            "Accounting agrupa asientos, reportes, tipo de cambio y cierre contable.\n"
            "Paso a paso:\n"
            "1. Abre Finanzas > Accounting.\n"
            "2. El periodo actual debe cargarse automaticamente.\n"
            "3. Primero obtiene y valida tipo de cambio del periodo.\n"
            "4. Solo despues de TC valido se generan asientos.\n"
            "5. Usa filtros por periodo, modulo, estado o cuenta para revisar movimientos.\n"
            "6. Descarga reportes en Excel/PDF cuando esten generados.\n"
            "7. Closing debe estar dentro de Accounting para generar cierres, no como modulo separado.\n"
            "8. No cierres periodo hasta validar asientos, TC y reportes."
        ),
    },
    {
        "category": "Finanzas",
        "question": "Manual Finanzas: Como funciona Credit Hold?",
        "answer": (
            "Credit Hold controla limites de credito y liberacion de ordenes.\n"
            "Paso a paso:\n"
            "1. Abre Finanzas > Credit, Order Hold & Release.\n"
            "2. Selecciona cliente desde el combo.\n"
            "3. Si el cliente no tiene limite asignado, el sistema debe avisarlo.\n"
            "4. Si tiene limite, revisa limite, usado, disponible y exposicion.\n"
            "5. Asigna o actualiza limite crediticio segun permisos.\n"
            "6. Libera o mantiene hold con justificacion.\n"
            "7. Verifica que el estado impacte el flujo comercial/servicios cuando aplique."
        ),
    },
    {
        "category": "Comercial",
        "question": "Manual Comercial: Como usar pizarra, clientes, puertos, servicios, precios y cotizaciones?",
        "answer": (
            "Comercial administra oportunidad, precios y cotizaciones.\n"
            "Paso a paso:\n"
            "1. Abre Comercial para ver la pizarra principal.\n"
            "2. Usa Clientes para analizar actividad por cliente.\n"
            "3. Usa Puertos para revisar pais, puerto y actividad comercial.\n"
            "4. Usa Servicios para ver oferta, costos y frecuencia.\n"
            "5. En Precios, filtra continente > pais > puerto en cascada.\n"
            "6. En Cotizaciones, selecciona cliente, ubicacion y servicio desde combos.\n"
            "7. Revisa el preview editable antes de aprobar.\n"
            "8. Exporta Word/PDF conservando formato, idioma y marca de agua cuando aplique."
        ),
    },
    {
        "category": "Informes",
        "question": "Manual Informes: Como funciona la pantalla principal?",
        "answer": (
            "Informes inicia con opciones y pizarra, no con todos los formularios abiertos.\n"
            "Paso a paso:\n"
            "1. Abre Informes.\n"
            "2. Debes ver botones: Revisar Informes, Generar Informe y Calculadora de Proyectos.\n"
            "3. Debes ver la pizarra con informes pendientes.\n"
            "4. La pizarra compara servicios finalizados contra tablas de informes.\n"
            "5. Si num_informe existe en una tabla de informe, no debe salir como pendiente.\n"
            "6. Si esta finalizado en Servicios y no existe en informes, debe salir pendiente.\n"
            "7. Usa filtros de status, continente, pais, puerto, ano y mes para consultar."
        ),
    },
    {
        "category": "Informes",
        "question": "Manual Informes: Como generar informes?",
        "answer": (
            "Generar Informe organiza los tipos por familia.\n"
            "Paso a paso:\n"
            "1. En Informes, presiona Generar Informe.\n"
            "2. Selecciona Contenedor, Buque o Certificados.\n"
            "3. En Contenedor, selecciona el num_informe desde popup como en desktop.\n"
            "4. En Buque, elige Grain Sampling, Truck Supervision, Draft Survey, Bunker, Vessel Condition, Port Captancy, Crane Inspection u otros.\n"
            "5. En Certificados, elige Holds Inspection, Sampling, Sealing o Lashing.\n"
            "6. Si abres desde Generar Informe, el flujo debe crear con POST y enviar a revision.\n"
            "7. Los botones Editar y Guardar Cambios no deben habilitarse en creacion nueva."
        ),
    },
    {
        "category": "Informes",
        "question": "Manual Informes: Como revisar informes?",
        "answer": (
            "Revisar Informes permite consultar, corregir y aprobar/rechazar documentos existentes.\n"
            "Paso a paso:\n"
            "1. Presiona Revisar Informes.\n"
            "2. Selecciona el tipo de informe y busca registros.\n"
            "3. Review debe abrir el formulario con GET.\n"
            "4. En modo review, Editar y Guardar Cambios deben estar habilitados.\n"
            "5. Guardar Cambios debe usar PUT, no POST.\n"
            "6. Aprobar o Rechazar actualiza status y comentarios.\n"
            "7. Generar informe/presentacion debe usar la data aprobada o revisada."
        ),
    },
    {
        "category": "Informes",
        "question": "Manual Informes: Como usar PORTIA para mejorar textos?",
        "answer": (
            "PORTIA en Informes ayuda a mejorar redaccion, no a cambiar hechos.\n"
            "Paso a paso:\n"
            "1. Completa los campos narrativos del informe.\n"
            "2. Presiona Improve PORTIA o el boton equivalente.\n"
            "3. Revisa la propuesta antes de reemplazar el texto.\n"
            "4. Mantiene datos tecnicos, fechas, buque, cliente y cantidades.\n"
            "5. Ajusta manualmente cualquier frase que no represente el hecho real.\n"
            "6. Guarda cambios solo si estas en review; en creacion envia a revision."
        ),
    },
    {
        "category": "Informes",
        "question": "Manual Informes: Como manejar Draft Survey?",
        "answer": (
            "Draft Survey es el flujo mas delicado de informes de buque.\n"
            "Paso a paso:\n"
            "1. Al abrir Draft Survey, el sistema debe preguntar si deseas abrir uno previo o crear desde cero.\n"
            "2. Si es previo, busca y carga el reporte existente.\n"
            "3. Debe permitir abrir Excel para previsualizar calculos cuando aplique.\n"
            "4. Carga tanques, medidas, correcciones y datos del buque con cuidado.\n"
            "5. Valida formulas y totales antes de enviar a revision.\n"
            "6. En review, usa PUT para corregir registros ya creados.\n"
            "7. No apruebes sin revisar consistencia de certificados, cantidades y anexos."
        ),
    },
    {
        "category": "Informes",
        "question": "Manual Informes: Como manejar Bunker Survey?",
        "answer": (
            "Bunker Survey maneja tanques, densidades, temperaturas y pesos.\n"
            "Paso a paso:\n"
            "1. Selecciona reporte o crea uno desde servicio.\n"
            "2. Completa header, tipo, puerto, pais, cliente, buque y categoria.\n"
            "3. En tanques, ingresa valores numericos donde corresponde.\n"
            "4. Si el campo admite GAUGE/GAUGES, debe guardarse como texto valido y no romper numeric.\n"
            "5. Revisa FWD, AFT, TRIM, LIST y tablas Fuel Oil / Diesel MGO.\n"
            "6. Valida engine log book y consumos declarados.\n"
            "7. Envia a revision cuando los datos esten completos."
        ),
    },
    {
        "category": "HHRR",
        "question": "Manual HHRR: Como usar noticias, solicitudes, horas, politicas y colillas?",
        "answer": (
            "HHRR depende mucho del rol del usuario.\n"
            "Paso a paso:\n"
            "1. Abre HHRR.\n"
            "2. Noticias muestra comunicados internos.\n"
            "3. Solicitudes permite consultar o crear solicitudes segun permisos.\n"
            "4. Registro de horas usa fecha/hora con selector calendario y guarda formato backend.\n"
            "5. Politicas permite consultar documentos internos.\n"
            "6. Colillas permite descargar PDF si el usuario esta autenticado.\n"
            "7. Roles de empleado pueden consultar/descargar pero no postear ni actualizar si no tienen permiso."
        ),
    },
    {
        "category": "PORTIA",
        "question": "Manual PORTIA SOM: Que puede consultar y que no puede hacer?",
        "answer": (
            "PORTIA SOM es un asistente de consulta ejecutiva y manual interno.\n"
            "Paso a paso:\n"
            "1. Abre PORTIA desde el menu.\n"
            "2. Haz preguntas sobre finanzas, comercial, servicios, puertos, master data, HHRR e informes.\n"
            "3. Usa consultas sugeridas para respuestas ejecutivas rapidas.\n"
            "4. Usa Q&A SOM para manual paso a paso por modulo.\n"
            "5. PORTIA no modifica datos, no aprueba informes y no ejecuta cierres.\n"
            "6. Si responde que no tiene contexto vivo, actualiza contexto o valida conexion con backend.\n"
            "7. Para informacion financiera, valida siempre contra Finanzas antes de tomar decisiones criticas."
        ),
    },
]


PORTIA_SUGGESTED_QUESTIONS = [
    "Resume el estado financiero actual.",
    "Que clientes tienen mayor exposicion en cuentas por cobrar?",
    "Cuantos servicios hay finalizados este ano?",
    "Que servicios estan listos para facturar?",
    "Que informes estan pendientes de crear o revisar?",
    "Como estan las cotizaciones comerciales?",
    "Que puertos concentran mayor actividad?",
    "Que modulos tiene SOM y para que sirve cada uno?",
    "Dame el manual paso a paso de Servicios.",
    "Dame el manual paso a paso de Finanzas.",
    "Dame el manual paso a paso de Informes.",
    "Que riesgos de cobranza deberia revisar gerencia?",
    "Dame un resumen ejecutivo de SOM.",
]

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
    {
        "category": "Finanzas - Collections",
        "question": "Manual Collections: Como generar estados de cuenta?",
        "answer": (
            "El estado de cuenta resume facturas, saldos, pagos y vencimientos por cliente.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Collections.\n"
            "2. Filtra por cliente antes de generar el documento.\n"
            "3. Revisa que las facturas mostradas correspondan al cliente correcto.\n"
            "4. Verifica numero de factura, fecha de emision, fecha de vencimiento, dias vencidos, total, pagos aplicados y saldo pendiente.\n"
            "5. Si necesitas un corte especifico, ajusta filtros de fecha o estado antes de exportar.\n"
            "6. Presiona Estado de Cuenta, Exportar PDF o Exportar Word segun la opcion disponible.\n"
            "7. Antes de enviarlo al cliente, valida que los numeros de factura largos se muestren completos y no en notacion cientifica.\n"
            "8. Si una factura no aparece, sincroniza Collections desde Invoicing y vuelve a filtrar."
        ),
    },
    {
        "category": "Finanzas - Collections",
        "question": "Manual Collections: Como crear una disputa?",
        "answer": (
            "Una disputa documenta una factura o saldo que el cliente cuestiona.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Collections.\n"
            "2. Busca la factura por cliente, numero de factura, estado o vencimiento.\n"
            "3. Selecciona la linea correcta.\n"
            "4. Presiona Crear Disputa o Dispute, segun la pantalla.\n"
            "5. Indica motivo: precio, servicio, documento, impuesto, diferencia de pago u otro.\n"
            "6. Escribe una descripcion clara con evidencia o comentario del cliente.\n"
            "7. Adjunta o referencia documentos si el flujo lo permite.\n"
            "8. Guarda la disputa.\n"
            "9. Verifica que el estado de la factura refleje la disputa o que aparezca en el modulo Disputes.\n"
            "10. Da seguimiento hasta resolver, cancelar o cerrar la disputa."
        ),
    },
    {
        "category": "Finanzas - Collections",
        "question": "Manual Collections: Como aplicar pagos?",
        "answer": (
            "Aplicar pagos reduce el saldo pendiente de una factura o cuenta por cobrar.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Collections.\n"
            "2. Filtra por cliente o factura.\n"
            "3. Selecciona la factura con saldo pendiente.\n"
            "4. Presiona Aplicar Pago o Pago.\n"
            "5. Selecciona origen del pago: Bank Reconciliation, Incoming Payment o pago manual.\n"
            "6. Confirma fecha de pago, monto, moneda, banco y referencia.\n"
            "7. Si el pago es parcial, registra solo el monto recibido.\n"
            "8. Si el pago cubre todo, el saldo debe quedar en cero y el estado debe pasar a pagado/cerrado.\n"
            "9. Guarda y vuelve a consultar la factura para confirmar saldo pendiente actualizado.\n"
            "10. Sincroniza con Accounting si el flujo contable lo requiere."
        ),
    },
    {
        "category": "Finanzas - Collections",
        "question": "Manual Collections: Como aplicar una nota de credito?",
        "answer": (
            "La nota de credito disminuye el saldo de una factura sin registrar un pago bancario.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Collections.\n"
            "2. Busca y selecciona la factura afectada.\n"
            "3. Presiona Aplicar Nota de Credito.\n"
            "4. Ingresa numero de nota, fecha, monto y motivo.\n"
            "5. Verifica que el monto no exceda el saldo pendiente salvo que el flujo lo permita.\n"
            "6. Guarda la nota.\n"
            "7. Revisa que el saldo pendiente se haya reducido.\n"
            "8. Exporta estado de cuenta actualizado si debes enviarlo al cliente.\n"
            "9. Valida impacto contable en Accounting cuando aplique."
        ),
    },
    {
        "category": "Finanzas - Billing",
        "question": "Manual Billing: Como facturar manualmente un servicio finalizado?",
        "answer": (
            "Billing manual se usa cuando el servicio esta finalizado y aun no tiene factura.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Billing.\n"
            "2. Selecciona el cliente en el combo/filtro.\n"
            "3. Revisa servicios finalizados sin numero de factura.\n"
            "4. Selecciona el servicio a facturar.\n"
            "5. Presiona Factura Manual.\n"
            "6. Ingresa numero de factura completo como texto, fecha de factura, termino de pago, vencimiento, moneda y monto.\n"
            "7. Revisa impuestos o cargos si la pantalla los solicita.\n"
            "8. Guarda.\n"
            "9. Verifica que el servicio quede con factura asignada.\n"
            "10. Sincroniza Invoicing y Collections para que la factura aparezca en cobranza."
        ),
    },
    {
        "category": "Finanzas - Invoicing",
        "question": "Manual Invoicing: Como subir factura electronica XML?",
        "answer": (
            "La carga XML registra factura electronica desde archivo.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Invoicing o Billing segun el flujo.\n"
            "2. Selecciona cliente y servicio si la pantalla lo solicita.\n"
            "3. Presiona Cargar XML o Factura Electronica.\n"
            "4. Selecciona el archivo XML correcto.\n"
            "5. El sistema debe leer numero de factura, emisor, receptor, fecha, moneda y monto.\n"
            "6. Verifica que el cliente del XML coincida con el servicio/cliente del ERP.\n"
            "7. Guarda el registro.\n"
            "8. Si hay error 400, revisa detalle del backend: cliente no encontrado, XML invalido, factura duplicada o servicio sin datos requeridos.\n"
            "9. Confirma que Invoicing muestre la factura y que Collections reciba el saldo."
        ),
    },
    {
        "category": "Finanzas - Bank Reconciliation",
        "question": "Manual Bank Reconciliation: Como conciliar un pago bancario?",
        "answer": (
            "La conciliacion une el movimiento bancario con una cuenta por cobrar o pago recibido.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Bank Reconciliation.\n"
            "2. Filtra por referencia, cliente, banco, fecha o monto.\n"
            "3. Selecciona el movimiento bancario.\n"
            "4. Presiona Ver Aplicados o Aplicar segun corresponda.\n"
            "5. Busca la factura o collection relacionada.\n"
            "6. Valida que monto, moneda, referencia y cliente coincidan.\n"
            "7. Aplica el pago total o parcial.\n"
            "8. Guarda la conciliacion.\n"
            "9. Revisa que Collections reduzca saldo y que Incoming Payments tenga el registro.\n"
            "10. Si aplicaste mal, usa reversa/anulacion solo si tu rol lo permite."
        ),
    },
    {
        "category": "Finanzas - Accounting",
        "question": "Manual Accounting: Como generar asientos y descargar reportes?",
        "answer": (
            "Accounting convierte eventos financieros en asientos y reportes.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Accounting.\n"
            "2. Confirma que el periodo actual se cargue automaticamente.\n"
            "3. Presiona Obtener TC o Validar Tipo de Cambio.\n"
            "4. No generes asientos hasta que el TC este confirmado.\n"
            "5. Ejecuta sincronizacion desde Collections, Invoicing o Invoice to Pay segun corresponda.\n"
            "6. Filtra asientos por periodo, origen, estado o cuenta.\n"
            "7. Revisa debitos y creditos antes de exportar.\n"
            "8. Descarga Diario/Reporte en Excel o PDF.\n"
            "9. Si el boton no descarga, revisa permisos, periodo seleccionado y respuesta del backend.\n"
            "10. Cierra periodo desde Closing dentro de Accounting solo cuando todo este validado."
        ),
    },
    {
        "category": "Informes - Containers",
        "question": "Manual Informes Containers: Como crear un container report?",
        "answer": (
            "Container Report se crea desde servicios finalizados pendientes de informe.\n"
            "Paso a paso:\n"
            "1. Entra a Informes.\n"
            "2. Presiona Generar Informe.\n"
            "3. Selecciona Contenedor.\n"
            "4. Abre el popup selector de num_informe.\n"
            "5. Selecciona el informe correspondiente al servicio finalizado.\n"
            "6. El formulario debe cargar cliente, num_informe, pais, puerto, fecha y datos base desde Servicios.\n"
            "7. Completa datos de contenedor, producto, hallazgos, proceso, conclusion y anexos.\n"
            "8. Usa PORTIA para mejorar textos si el campo narrativo lo permite.\n"
            "9. Presiona Enviar a Revision para crear con POST.\n"
            "10. Si se abre desde Review, usa Editar y Guardar Cambios con PUT."
        ),
    },
    {
        "category": "Informes - Grain Sampling",
        "question": "Manual Grain Sampling: Como crear informe de muestreo de granos?",
        "answer": (
            "Grain Sampling documenta supervision de muestras de granos/carga agricola.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque.\n"
            "2. Selecciona Grain Sampling o Sampling Supervision.\n"
            "3. Selecciona num_informe desde el selector.\n"
            "4. Confirma cliente, buque, puerto, pais, fecha y operacion.\n"
            "5. Completa antecedentes, alcance de supervision y metodo de muestreo.\n"
            "6. Registra producto, lotes, bodegas, puntos de muestreo o unidades segun aplique.\n"
            "7. Documenta hallazgos, incidentes, observaciones y conclusion.\n"
            "8. Usa PORTIA solo para mejorar redaccion, sin cambiar hechos.\n"
            "9. Envia a revision.\n"
            "10. En Review, valida informacion, edita si aplica, guarda con PUT y luego aprueba/rechaza."
        ),
    },
    {
        "category": "Informes - Truck Supervision",
        "question": "Manual Truck Supervision: Como crear informe de supervision de camiones?",
        "answer": (
            "Truck Supervision documenta control de camiones, guias, placas e incidencias.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque.\n"
            "2. Selecciona Truck Supervision o Logistics Supervision.\n"
            "3. Selecciona num_informe desde Servicios.\n"
            "4. Verifica cliente, buque, puerto, pais y fecha.\n"
            "5. Completa representantes, tiempos, proceso de supervision y detalle operativo.\n"
            "6. Registra hallazgos documentales, control operativo e incidentes.\n"
            "7. Completa conclusion clara y objetiva.\n"
            "8. Usa PORTIA para mejorar textos si es necesario.\n"
            "9. En creacion, solo Enviar a Revision.\n"
            "10. En Review, Editar y Guardar Cambios deben estar habilitados y usar PUT."
        ),
    },
    {
        "category": "Informes - Draft Survey",
        "question": "Manual Draft Survey: Como crear o abrir un draft survey?",
        "answer": (
            "Draft Survey requiere escoger entre crear nuevo o abrir previo.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque > Draft Survey.\n"
            "2. El sistema debe preguntar si deseas crear desde cero o abrir uno previo.\n"
            "3. Si abres previo, busca por num_informe/buque/cliente y carga el registro.\n"
            "4. Si creas nuevo, selecciona el servicio desde el selector.\n"
            "5. Completa header, datos del buque, puertos, fechas y representantes.\n"
            "6. Carga lecturas draft, tanques, correcciones, densidades y constantes.\n"
            "7. Usa abrir Excel/previsualizar para revisar calculos cuando aplique.\n"
            "8. Valida totales, initial/final/intermediate y diferencias.\n"
            "9. Envia a revision solo cuando formulas y datos coincidan.\n"
            "10. En Review, corrige con Editar/Guardar Cambios usando PUT."
        ),
    },
    {
        "category": "Informes - Bunker",
        "question": "Manual Bunker Survey: Como crear informe on hire/off hire bunker?",
        "answer": (
            "Bunker Survey registra combustible, tanques y datos de hire.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque > Bunker Survey.\n"
            "2. Selecciona num_informe o reporte previo.\n"
            "3. Escoge tipo: On Hire, Off Hire, Spot o Condition segun servicio.\n"
            "4. Completa certificado, buque, cliente, puerto, pais, fecha y categoria.\n"
            "5. Completa texto de certificado y antecedentes.\n"
            "6. En tanques Fuel Oil/Diesel MGO, ingresa dist, gauge, volumen, temperatura, densidad y peso.\n"
            "7. Si un campo debe contener GAUGE o GAUGES, guardalo como texto valido.\n"
            "8. Completa engine log book y consumos declarados.\n"
            "9. Visualiza antes de enviar.\n"
            "10. Envia a revision y corrige desde Review si aplica."
        ),
    },
    {
        "category": "Informes - Vessel Condition",
        "question": "Manual Vessel Condition: Como crear vessel condition survey?",
        "answer": (
            "Vessel Condition documenta condicion general del buque.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque > Vessel Condition.\n"
            "2. Selecciona el num_informe del servicio.\n"
            "3. Verifica datos del buque, cliente, puerto, pais y fecha.\n"
            "4. Completa secciones de condicion, inspeccion visual, observaciones y hallazgos.\n"
            "5. Agrega comentarios por area del buque segun el formulario.\n"
            "6. Usa PORTIA para mejorar narrativa sin alterar hechos.\n"
            "7. Guarda/Envia a revision.\n"
            "8. Si requiere presentacion, abre el popup y confirma que el boton generar sea visible.\n"
            "9. Revisa documento final antes de aprobar.\n"
            "10. En Review, usa PUT para cambios."
        ),
    },
    {
        "category": "Informes - Port Captancy",
        "question": "Manual Port Captancy: Como crear informe port captancy?",
        "answer": (
            "Port Captancy documenta supervision portuaria/captancy segun servicio.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque > Port Captancy.\n"
            "2. Selecciona num_informe desde Servicios.\n"
            "3. Confirma cliente, buque, pais, puerto y fechas.\n"
            "4. Completa alcance, actividades supervisadas, eventos, tiempos y hallazgos.\n"
            "5. Agrega comentarios de coordinacion, operacion y cierre.\n"
            "6. Usa PORTIA para mejorar textos.\n"
            "7. Envia a revision.\n"
            "8. Desde Review, valida, edita, guarda cambios y aprueba/rechaza segun corresponda."
        ),
    },
    {
        "category": "Informes - Crane Inspection",
        "question": "Manual Crane Inspection: Como crear crane inspection?",
        "answer": (
            "Crane Inspection registra inspeccion de gruas/equipos asociados al servicio.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque > Crane Inspection.\n"
            "2. Selecciona el num_informe correspondiente.\n"
            "3. Verifica cliente, puerto, pais, buque y fecha.\n"
            "4. Completa identificacion de grua/equipo, estado visual y puntos de inspeccion.\n"
            "5. Registra observaciones, hallazgos, riesgos y recomendaciones.\n"
            "6. Adjunta o referencia evidencia si el flujo lo permite.\n"
            "7. Usa PORTIA para mejorar redaccion tecnica.\n"
            "8. Envia a revision.\n"
            "9. Desde Review, usa GET para abrir y PUT para guardar correcciones."
        ),
    },
    {
        "category": "Informes - Cargo Condition",
        "question": "Manual Cargo Condition Survey: Como crear cargo condition?",
        "answer": (
            "Cargo Condition documenta condicion de la carga observada.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque > Cargo Condition Survey.\n"
            "2. Selecciona num_informe desde el servicio.\n"
            "3. Confirma cliente, buque, producto, puerto, pais y fecha.\n"
            "4. Describe condicion de la carga, empaque, humedad, contaminacion, danos o anomalias.\n"
            "5. Registra hallazgos con lenguaje objetivo.\n"
            "6. Completa conclusion y recomendaciones.\n"
            "7. Envia a revision.\n"
            "8. Genera documento final solo despues de revisar datos y textos."
        ),
    },
    {
        "category": "Informes - Certificados",
        "question": "Manual Holds Inspection Certificate: Como crear certificado de bodegas?",
        "answer": (
            "Holds Inspection Certificate certifica condicion/aptitud de bodegas.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Certificados.\n"
            "2. Selecciona Holds Inspection Certificate.\n"
            "3. Selecciona num_informe/servicio desde el selector.\n"
            "4. Verifica buque, cliente, puerto, pais y fecha.\n"
            "5. Completa bodegas inspeccionadas y condicion observada.\n"
            "6. Registra observaciones o restricciones.\n"
            "7. Envia a revision.\n"
            "8. Desde Review, edita si aplica y genera certificado final."
        ),
    },
    {
        "category": "Informes - Certificados",
        "question": "Manual Sampling Certificate: Como crear certificado de muestreo?",
        "answer": (
            "Sampling Certificate certifica toma o supervision de muestras.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Certificados.\n"
            "2. Selecciona Sampling Certificate.\n"
            "3. Selecciona el servicio/num_informe.\n"
            "4. Confirma cliente, producto, buque, puerto y fecha.\n"
            "5. Indica metodo, cantidad de muestras, ubicacion y responsable.\n"
            "6. Registra observaciones si existieron incidencias.\n"
            "7. Envia a revision.\n"
            "8. Genera documento final despues de aprobar."
        ),
    },
    {
        "category": "Informes - Certificados",
        "question": "Manual Sealing Certificate: Como crear certificado de sellado?",
        "answer": (
            "Sealing Certificate documenta sellos aplicados o verificados.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Certificados.\n"
            "2. Selecciona Sealing Certificate.\n"
            "3. Selecciona num_informe.\n"
            "4. Confirma cliente, puerto, pais, buque/contenedor y fecha.\n"
            "5. Ingresa numeros de sello, unidades, bodegas o contenedores segun aplique.\n"
            "6. Verifica que los numeros no tengan errores.\n"
            "7. Completa observaciones.\n"
            "8. Envia a revision y genera certificado al aprobar."
        ),
    },
    {
        "category": "Informes - Certificados",
        "question": "Manual Lashing Certificate: Como crear certificado de lashing?",
        "answer": (
            "Lashing Certificate certifica sujecion/aseguramiento de carga.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Certificados.\n"
            "2. Selecciona Lashing Certificate.\n"
            "3. Selecciona servicio o num_informe.\n"
            "4. Confirma datos de cliente, buque, puerto, pais y fecha.\n"
            "5. Completa descripcion de carga, tipo de lashing, condicion y observaciones.\n"
            "6. Registra hallazgos o restricciones si existen.\n"
            "7. Envia a revision.\n"
            "8. Desde Review, edita con PUT y genera certificado final."
        ),
    },
    {
        "category": "Informes - Revision",
        "question": "Manual Informes Review: Como aprobar, rechazar o corregir informes?",
        "answer": (
            "Review controla calidad antes del documento final.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Revisar Informes.\n"
            "2. Selecciona tipo de informe.\n"
            "3. Busca por num_informe, cliente, puerto, status o fecha.\n"
            "4. Presiona Review o doble click sobre el registro.\n"
            "5. El formulario debe abrir con GET y mostrar datos existentes.\n"
            "6. Presiona Editar para habilitar campos.\n"
            "7. Corrige informacion y presiona Guardar Cambios para PUT.\n"
            "8. Si esta correcto, aprueba.\n"
            "9. Si requiere correccion, rechaza e indica motivo.\n"
            "10. Genera informe/presentacion solo con informacion revisada."
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

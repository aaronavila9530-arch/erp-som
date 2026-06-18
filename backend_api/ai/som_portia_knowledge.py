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
        "category": "Master Data - Pantalla principal",
        "question": "Master Data: Que hace cada filtro y boton de la pantalla principal?",
        "answer": (
            "La pantalla principal de Master Data permite buscar y abrir catalogos base.\n"
            "Paso a paso:\n"
            "1. Tipo: selecciona Todos, Empleado, Surveyor, Cliente, Proveedor o Servicio para limitar la busqueda.\n"
            "2. Continente: filtra ubicaciones por continente cuando el catalogo usa pais/puerto.\n"
            "3. Pais: se carga segun continente y filtra los registros relacionados.\n"
            "4. Puerto: se carga segun pais y permite revisar registros por puerto.\n"
            "5. Buscar: aplica los filtros y muestra la tabla correspondiente.\n"
            "6. + Empleado: abre el formulario para crear un empleado.\n"
            "7. + Surveyor: abre el formulario para crear un surveyor operativo.\n"
            "8. + Cliente: abre el formulario para crear cliente.\n"
            "9. + Proveedor: abre el formulario para crear proveedor.\n"
            "10. + Servicio: abre el formulario para crear servicio maestro/catalogo.\n"
            "11. Si un combo esta vacio, revisa primero que existan datos base de paises/puertos o registros activos."
        ),
    },
    {
        "category": "Master Data - Tablas",
        "question": "Master Data: Como usar Ver, Editar, Eliminar, Anterior y Siguiente?",
        "answer": (
            "Las tablas de Master Data comparten una barra de acciones.\n"
            "Paso a paso:\n"
            "1. Selecciona un registro en la tabla.\n"
            "2. Ver: abre una ventana de solo lectura para confirmar todos los campos del registro.\n"
            "3. Editar: abre el formulario con los datos actuales cargados para modificarlos.\n"
            "4. Eliminar: solicita confirmacion y elimina el registro si tu rol tiene permiso.\n"
            "5. Anterior: regresa a la pagina previa de la tabla.\n"
            "6. Siguiente: avanza a la pagina siguiente.\n"
            "7. Volver: regresa a la pantalla principal de Master Data.\n"
            "8. Antes de eliminar, confirma que el registro no se usa en Servicios, Finanzas, Comercial o Informes.\n"
            "9. Despues de editar, vuelve a buscar para confirmar que la tabla refresco los datos."
        ),
    },
    {
        "category": "Master Data - Clientes",
        "question": "Master Data Clientes: Como agregar o editar un cliente?",
        "answer": (
            "Cliente alimenta Servicios, Comercial, Finanzas e Informes.\n"
            "Paso a paso:\n"
            "1. En Master Data presiona + Cliente o abre tabla Clientes y presiona Editar.\n"
            "2. Datos generales: llena Nombre Juridico, Nombre Comercial, Pais y Cedula Juridica/VAT.\n"
            "3. Direccion: llena Provincia, Canton, Distrito y Direccion Exacta.\n"
            "4. Pago/contacto: llena Fecha de Pago con calendario, Correo, Prefijo, Telefono, Contacto Principal, Contacto Secundario y Comentarios.\n"
            "5. Prefijo: selecciona el codigo telefonico correcto desde el combo.\n"
            "6. Fecha de pago: debe verse en formato largo en ingles en pantalla y guardarse regularizada para base de datos.\n"
            "7. Presiona Guardar.\n"
            "8. Reabre la tabla Clientes y busca el cliente para validar.\n"
            "9. Si el cliente se usara en Billing o Collections, revisa que Nombre Comercial y Codigo queden consistentes."
        ),
    },
    {
        "category": "Master Data - Proveedores",
        "question": "Master Data Proveedores: Como agregar o editar un proveedor?",
        "answer": (
            "Proveedor se usa principalmente en compras, cuentas por pagar y operaciones relacionadas.\n"
            "Paso a paso:\n"
            "1. Presiona + Proveedor o selecciona un proveedor y presiona Editar.\n"
            "2. Identificacion: llena Nombre, Apellidos, Nombre Comercial y Cedula.\n"
            "3. Ubicacion/contacto: llena Pais, Provincia, Canton, Distrito, Direccion Exacta, Prefijo, Telefono y Correo.\n"
            "4. Datos bancarios: llena Terminos de Pago, Banco, Cuenta IBAN, Swift Code, UID y Direccion Banco.\n"
            "5. Tipo de proveeduria: selecciona el tipo desde el combo.\n"
            "6. Comentarios: agrega notas utiles para compras/finanzas.\n"
            "7. Presiona Guardar.\n"
            "8. En tabla Proveedores usa Ver para confirmar la informacion bancaria antes de pagar.\n"
            "9. Evita duplicar proveedores con variaciones de nombre comercial."
        ),
    },
    {
        "category": "Master Data - Empleados",
        "question": "Master Data Empleados: Como agregar o editar un empleado?",
        "answer": (
            "Empleado alimenta HHRR, permisos, colillas y procesos internos.\n"
            "Paso a paso:\n"
            "1. Presiona + Empleado o selecciona un empleado y presiona Editar.\n"
            "2. Datos personales: llena Nombre, Apellidos, Estado Civil, Genero y Nacionalidad.\n"
            "3. Contacto/direccion: llena Prefijo, Telefono, Provincia, Canton, Distrito y Direccion.\n"
            "4. Laboral/pago: selecciona Jornada y Frecuencia de Pago; llena Salario, Banco, Cuenta IBAN y Moneda.\n"
            "5. Salud/emergencia: llena Enfermedades, Contacto de Emergencia y Telefono de Emergencia.\n"
            "6. Activos: registra Activo, Marca y Serial de los equipos asignados si aplica.\n"
            "7. Presiona Guardar.\n"
            "8. Verifica en tabla Empleados que los datos se hayan actualizado.\n"
            "9. Si el empleado requiere usuario, revisa tambien el modulo de usuarios/permisos."
        ),
    },
    {
        "category": "Master Data - Surveyors",
        "question": "Master Data Surveyors: Como agregar o editar un surveyor?",
        "answer": (
            "Surveyor se usa para asignaciones de servicios, honorarios y reportes operativos.\n"
            "Paso a paso:\n"
            "1. Presiona + Surveyor o selecciona un surveyor y presiona Editar.\n"
            "2. Datos personales: llena Nombre, Apellidos, Estado Civil, Genero y Nacionalidad.\n"
            "3. Contacto/direccion: selecciona Prefijo; llena Telefono, Provincia, Canton, Distrito y Direccion.\n"
            "4. Laboral/pago: selecciona Jornada, Frecuencia de Pago y Moneda; llena Banco, Cuenta IBAN, Swift y UID.\n"
            "5. Salud/emergencia: llena Enfermedades, Contacto de Emergencia y Telefono de Emergencia.\n"
            "6. Operacion: selecciona Operacion desde el combo cargado por Servicios MD.\n"
            "7. Honorario: ingresa el honorario base.\n"
            "8. Puertos que atiende: selecciona puerto desde combo.\n"
            "9. Presiona Guardar.\n"
            "10. Si luego no aparece en Servicios > Agregar Surveyor, confirma que se guardo correctamente y que el catalogo esta activo."
        ),
    },
    {
        "category": "Master Data - Servicios",
        "question": "Master Data Servicios: Como agregar o editar un servicio maestro?",
        "answer": (
            "Servicio maestro define operaciones disponibles para Servicios y Comercial.\n"
            "Paso a paso:\n"
            "1. Presiona + Servicio o abre tabla Servicios y presiona Editar.\n"
            "2. Codigo: se muestra como readonly si el sistema lo genera.\n"
            "3. Codigo Producto: ingresa el codigo comercial/contable si aplica.\n"
            "4. Nombre: escribe el nombre exacto del servicio u operacion.\n"
            "5. Costo: ingresa el costo base si aplica.\n"
            "6. Presiona Guardar.\n"
            "7. Verifica que el servicio aparezca en combos de Servicios, Surveyors, Comercial y Precios.\n"
            "8. Evita crear nombres duplicados con diferencias menores como mayusculas o abreviaturas."
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
        "category": "Servicios - Pantalla principal",
        "question": "Servicios: Que hacen los filtros y botones de la pantalla inicial?",
        "answer": (
            "La pantalla inicial de Servicios permite buscar operaciones y crear nuevos servicios.\n"
            "Paso a paso:\n"
            "1. Status: filtra servicios por estado, por ejemplo pendiente, confirmado, finalizado o cancelado.\n"
            "2. Ano: filtra por ano tomado del num_informe cuando existe.\n"
            "3. Cliente: filtra por cliente desde el catalogo.\n"
            "4. Operacion: filtra por tipo de servicio/operacion desde Servicios MD.\n"
            "5. Surveyor: filtra por surveyor asociado.\n"
            "6. Buscar: aplica los filtros y abre la tabla de resultados.\n"
            "7. + Servicio: abre el formulario para registrar un servicio nuevo.\n"
            "8. Los combos cargan datos bajo demanda; si alguno aparece vacio, revisa Master Data o conexion con backend."
        ),
    },
    {
        "category": "Servicios - Tabla",
        "question": "Servicios: Que muestra la tabla y que significan sus KPIs?",
        "answer": (
            "La tabla de Servicios muestra operaciones y sus datos financieros/operativos.\n"
            "Paso a paso:\n"
            "1. La barra KPI resume Servicios, Facturado, Paises, Confirmados, Cancelados y Operaciones.\n"
            "2. La tabla muestra consec, tipo, estado, num_informe, buque/contenedor, cliente, contacto y detalle.\n"
            "3. Tambien muestra continente, pais, puerto, operacion, surveyor, honorarios, costo operativo y costo tarjetas.\n"
            "4. Fechas visibles: fecha_inicio, hora_inicio, fecha_fin, hora_fin, duracion y demoras.\n"
            "5. Datos de facturacion: factura, valor_factura, fecha_factura, terminos_pago, fecha_vencimiento y dias_vencido.\n"
            "6. Las filas con costos faltantes se marcan en rojo pastel para advertir que no deben finalizarse sin completar costos.\n"
            "7. Usa scroll horizontal para ver columnas largas y paginacion Anterior/Siguiente para navegar resultados.\n"
            "8. Doble click sobre un servicio finalizado puede abrir el informe asociado si ya fue creado."
        ),
    },
    {
        "category": "Servicios - Agregar",
        "question": "Servicios: Como agregar un servicio nuevo y que campos debo llenar?",
        "answer": (
            "Agregar Servicio registra una operacion nueva sin generar aun num_informe final.\n"
            "Paso a paso:\n"
            "1. Entra a Servicios y presiona + Servicio.\n"
            "2. Tipo: selecciona Buque o Contenedor.\n"
            "3. Buque / Contenedor: escribe el nombre del buque o identificacion del contenedor.\n"
            "4. Cliente: selecciona cliente desde el combo cargado desde Master Data.\n"
            "5. Contacto: escribe contacto del cliente o responsable.\n"
            "6. Detalle: describe producto, carga, observacion o detalle operativo.\n"
            "7. Continente: selecciona continente; esto carga Paises.\n"
            "8. Pais: selecciona pais; esto carga Puertos.\n"
            "9. Puerto: selecciona puerto.\n"
            "10. Operacion: selecciona el servicio desde Servicios MD.\n"
            "11. Surveyor: selecciona surveyor desde Master Data.\n"
            "12. Honorarios: se autocompleta segun surveyor/operacion cuando existe configuracion.\n"
            "13. Costo operativo: ingresa costo operativo estimado o real si ya se conoce.\n"
            "14. Fecha inicio: selecciona con calendario; se muestra LONG en ingles y se guarda normalizada.\n"
            "15. Hora inicio: selecciona con reloj.\n"
            "16. Presiona Guardar.\n"
            "17. No escribas num_informe aqui: se genera despues con Generar Consecutivo."
        ),
    },
    {
        "category": "Servicios - Editar",
        "question": "Servicios: Como editar un servicio existente?",
        "answer": (
            "Editar Servicio permite corregir costos, fecha/hora y surveyors antes o despues del consecutivo.\n"
            "Paso a paso:\n"
            "1. Busca el servicio y selecciona la fila.\n"
            "2. Presiona Editar servicio.\n"
            "3. Revisa Surveyor resumen; para cambiar detalle usa Agregar surveyor o Ver desglose.\n"
            "4. Honorarios: modifica el total si aplica o deja que se actualice desde el desglose de surveyors.\n"
            "5. Costo Operativo: ingresa o corrige el costo.\n"
            "6. Costo Tarjetas: se habilita solo bajo la regla configurada, por ejemplo pais distinto de Costa Rica y surveyor especifico.\n"
            "7. Fecha Inicio: usa calendario para cambiarla.\n"
            "8. Hora Inicio: usa selector de hora.\n"
            "9. Presiona Guardar.\n"
            "10. Si cambias fecha de un servicio con num_informe, el sistema debe actualizar los cuatro digitos centrales del num_informe segun la nueva fecha.\n"
            "11. Refresca la tabla para confirmar que valores y colores de costos se actualizaron."
        ),
    },
    {
        "category": "Servicios - Consecutivo",
        "question": "Servicios: Como generar consecutivo o num_informe?",
        "answer": (
            "Generar Consecutivo confirma el servicio y asigna el num_informe segun reglas del ERP.\n"
            "Paso a paso:\n"
            "1. Busca y selecciona el servicio.\n"
            "2. Presiona Generar Consecutivo.\n"
            "3. Verifica o selecciona Fecha de Inicio con calendario.\n"
            "4. Verifica o selecciona Hora de Inicio con reloj.\n"
            "5. Presiona Generar Consecutivo en el popup.\n"
            "6. El backend confirma el servicio y genera num_informe automaticamente.\n"
            "7. El sistema muestra el numero asignado y el nuevo estado.\n"
            "8. Si falta fecha u hora, no permite continuar.\n"
            "9. Si la fecha se corrige despues desde Editar, los cuatro digitos centrales del num_informe deben cambiar para coincidir con la nueva fecha.\n"
            "10. No edites manualmente el num_informe salvo correccion directa autorizada en base de datos."
        ),
    },
    {
        "category": "Servicios - Costos",
        "question": "Servicios: Como agregar costos, honorarios y costo tarjetas?",
        "answer": (
            "Los costos son obligatorios para controlar margen y permitir finalizacion correcta.\n"
            "Paso a paso:\n"
            "1. Selecciona el servicio y presiona Editar servicio.\n"
            "2. Honorarios: revisa el total de honorarios de surveyors.\n"
            "3. Si hay varios surveyors, presiona Agregar surveyor y registra el honorario individual de cada uno.\n"
            "4. Costo Operativo: ingresa costos operativos directos del servicio.\n"
            "5. Costo Tarjetas: solo se habilita cuando la regla de negocio aplica.\n"
            "6. Los valores deben ser numericos; usa punto o coma decimal segun acepte la pantalla.\n"
            "7. Guarda cambios.\n"
            "8. Si el servicio queda con honorarios, costo operativo o costo tarjetas faltantes, la fila puede marcarse como costos_faltantes.\n"
            "9. Antes de Finalizar Servicio, valida que costos necesarios esten completos.\n"
            "10. Estos costos alimentan Finanzas, Comercial y analitica de margen."
        ),
    },
    {
        "category": "Servicios - Surveyors",
        "question": "Servicios: Como agregar varios surveyors al servicio?",
        "answer": (
            "Gestion de Surveyors permite hasta 10 surveyors por servicio.\n"
            "Paso a paso:\n"
            "1. Selecciona el servicio y presiona Editar servicio.\n"
            "2. Presiona Agregar surveyor.\n"
            "3. En el popup, usa + Agregar surveyor para insertar una linea.\n"
            "4. Selecciona el surveyor desde el combo.\n"
            "5. Ingresa Honorario de esa persona.\n"
            "6. Repite hasta completar el equipo del servicio, maximo 10.\n"
            "7. Usa Quitar para eliminar una linea incorrecta.\n"
            "8. Usa Limpiar todo si debes rehacer la asignacion.\n"
            "9. Revisa Total surveyors y Honorarios totales.\n"
            "10. Presiona Guardar.\n"
            "11. El resumen se refleja en Editar Servicio y en la tabla."
        ),
    },
    {
        "category": "Servicios - Demoras",
        "question": "Servicios: Como registrar demoras?",
        "answer": (
            "Demoras registra periodos de retraso dentro del servicio.\n"
            "Paso a paso:\n"
            "1. Busca y selecciona el servicio.\n"
            "2. Presiona Demoras.\n"
            "3. Presiona + Agregar linea.\n"
            "4. Selecciona Fecha Inicio y Hora Inicio.\n"
            "5. Selecciona Fecha Fin y Hora Fin.\n"
            "6. Agrega mas lineas si hubo varios periodos de demora.\n"
            "7. Usa Quitar para borrar una linea incorrecta.\n"
            "8. Presiona Guardar.\n"
            "9. La tabla debe actualizar columna Demoras y Duracion si el backend calcula esos valores.\n"
            "10. Registra demoras antes de finalizar si afectan facturacion o reporte."
        ),
    },
    {
        "category": "Servicios - Finalizar",
        "question": "Servicios: Como finalizar un servicio?",
        "answer": (
            "Finalizar Servicio cierra la operacion y la deja lista para facturacion/informes.\n"
            "Paso a paso:\n"
            "1. Busca y selecciona el servicio.\n"
            "2. Verifica que tenga honorarios y costo operativo completos.\n"
            "3. Si requiere costo tarjetas, completalo antes de continuar.\n"
            "4. Presiona Finalizar Servicio.\n"
            "5. Revisa el resumen: surveyor, honorarios, costo operativo y costo tarjetas.\n"
            "6. Si falta algo, presiona Editar y corrige.\n"
            "7. Presiona Finalizar Servicio dentro del popup.\n"
            "8. Selecciona Fecha finalizacion con calendario.\n"
            "9. Selecciona Hora finalizacion con reloj.\n"
            "10. Confirma.\n"
            "11. Al finalizar, el servicio puede pasar a Billing y a pizarra de Informes si aun no existe informe creado."
        ),
    },
    {
        "category": "Servicios - Ver y abrir informes",
        "question": "Servicios: Como ver un servicio o abrir su informe?",
        "answer": (
            "Ver Servicio muestra detalle completo y doble click puede abrir informe relacionado.\n"
            "Paso a paso:\n"
            "1. Selecciona una fila en la tabla.\n"
            "2. Presiona Ver para abrir una ventana de solo lectura con los campos del servicio.\n"
            "3. Usa Cerrar para volver a la tabla.\n"
            "4. Si el servicio esta finalizado y tiene informe creado, doble click puede abrir la vista de informe.\n"
            "5. La vista de informe debe usar GET para cargar datos existentes.\n"
            "6. Si necesitas corregir el servicio, usa Editar.\n"
            "7. Si el informe no existe, el servicio debe permanecer pendiente en Informes.\n"
            "8. Desde la vista de informe, si aplica, puedes editar o confirmar segun permisos y estado."
        ),
    },
    {
        "category": "Servicios - Cancelar y eliminar",
        "question": "Servicios: Como cancelar o eliminar un servicio?",
        "answer": (
            "Cancelar conserva trazabilidad; eliminar borra o remueve el registro segun backend y permisos.\n"
            "Paso a paso para cancelar:\n"
            "1. Selecciona el servicio.\n"
            "2. Presiona Cancelar.\n"
            "3. Selecciona Motivo de cancelacion.\n"
            "4. Escribe descripcion adicional si aplica.\n"
            "5. Confirma Cancelar servicio.\n"
            "6. El estado debe cambiar a cancelado y guardar razon/comentario.\n"
            "Paso a paso para eliminar:\n"
            "1. Selecciona el servicio.\n"
            "2. Presiona Eliminar.\n"
            "3. Confirma solo si estas seguro.\n"
            "4. Evita eliminar servicios con factura, informe o trazabilidad financiera; usa cancelar cuando necesites conservar historial."
        ),
    },
    {
        "category": "Servicios - Exportar",
        "question": "Servicios: Como exportar la tabla?",
        "answer": (
            "Exportar descarga los resultados visibles o consultados para analisis externo.\n"
            "Paso a paso:\n"
            "1. Aplica filtros y presiona Buscar.\n"
            "2. En la tabla, abre Exportar.\n"
            "3. Selecciona CSV, PDF, XML o Excel.\n"
            "4. Elige ruta de guardado si el sistema la solicita.\n"
            "5. Valida que las columnas largas como num_informe y factura se vean completas.\n"
            "6. En Excel, numero de factura debe exportarse como texto para no truncar 20+ digitos.\n"
            "7. Usa CSV/XML para integraciones y Excel/PDF para revision operativa."
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
        "category": "Finanzas - Menu",
        "question": "Finanzas: Como esta organizado el modulo?",
        "answer": (
            "Finanzas esta dividido en flujos Order to Cash, Invoice to Pay y Accounting.\n"
            "Paso a paso:\n"
            "1. Abre Finanzas desde el menu principal.\n"
            "2. Usa Invoicing & Billing para facturar servicios, facturas anticipadas, XML, notas de credito y consulta de facturas.\n"
            "3. Usa Credit (Order Hold & Release) para configurar limites de credito y revisar exposicion.\n"
            "4. Usa Collections para cuentas por cobrar, pagos, notas de credito, disputas y estados de cuenta.\n"
            "5. Usa Bank Reconciliation para registrar o revisar pagos bancarios y su aplicacion.\n"
            "6. Usa Disputes para gestionar casos abiertos por diferencias o reclamos.\n"
            "7. Usa Invoice To Pay para obligaciones de pago a proveedores.\n"
            "8. Usa Accounting para TC, asientos, cierres, reportes y declaraciones.\n"
            "9. El orden recomendado es Servicios finalizados -> Billing/Invoicing -> Collections/Bank -> Accounting."
        ),
    },
    {
        "category": "Finanzas - Invoicing",
        "question": "Invoicing: Como buscar cliente y facturar servicios pendientes?",
        "answer": (
            "Invoicing permite buscar servicios pendientes de facturar por cliente.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Invoicing & Billing > pestana Invoicing.\n"
            "2. Selecciona Cliente desde el combo.\n"
            "3. Presiona Buscar.\n"
            "4. La tabla debe mostrar servicios finalizados pendientes o facturas relacionadas segun el flujo.\n"
            "5. Selecciona una fila antes de usar Factura Manual, Factura Electronica XML o Ver Factura.\n"
            "6. Si no hay pendientes, confirma que el servicio este Finalizado y sin numero de factura.\n"
            "7. Si el cliente no aparece, revisa Master Data > Clientes.\n"
            "8. Despues de facturar, valida que Collections reciba la factura mediante sincronizacion si aplica."
        ),
    },
    {
        "category": "Finanzas - Invoicing",
        "question": "Invoicing: Como crear factura manual?",
        "answer": (
            "Factura Manual crea una factura desde datos capturados en el ERP.\n"
            "Paso a paso:\n"
            "1. Busca cliente en Invoicing y selecciona el servicio/fila correspondiente.\n"
            "2. Presiona Factura Manual.\n"
            "3. Completa periodo de operacion.\n"
            "4. Completa descripcion del servicio.\n"
            "5. Completa fecha de factura usando calendario.\n"
            "6. Ingresa numero de factura completo como texto si corresponde.\n"
            "7. Revisa cliente, servicio, monto, moneda, impuestos y total.\n"
            "8. Presiona Preview Factura para revisar antes de crear.\n"
            "9. Presiona Facturar.\n"
            "10. Guarda o descarga el PDF si el popup lo ofrece.\n"
            "11. Verifica que la factura aparezca en Invoicing y luego en Collections."
        ),
    },
    {
        "category": "Finanzas - Invoicing",
        "question": "Invoicing: Como cargar factura electronica XML?",
        "answer": (
            "Factura Electronica XML registra datos desde archivo XML.\n"
            "Paso a paso:\n"
            "1. Busca y selecciona el servicio/fila a facturar.\n"
            "2. Presiona Factura Electronica (XML).\n"
            "3. En el popup, presiona Seleccionar XML.\n"
            "4. Selecciona el archivo XML correcto.\n"
            "5. El sistema envia el XML al backend.\n"
            "6. Valida que el cliente, numero, fecha, moneda y total correspondan.\n"
            "7. Si aparece error 400, revisa detalle: cliente no existe, servicio incorrecto, XML invalido o factura duplicada.\n"
            "8. Confirma que numero de factura largo se guarde y exporte completo como texto.\n"
            "9. Sincroniza Collections si la factura no aparece en cuentas por cobrar."
        ),
    },
    {
        "category": "Finanzas - Invoicing",
        "question": "Invoicing: Como usar facturacion anticipada y nota de credito independiente?",
        "answer": (
            "Estos botones crean documentos sin depender necesariamente de un servicio seleccionado.\n"
            "Paso a paso facturacion anticipada:\n"
            "1. Presiona Facturacion Anticipada.\n"
            "2. Selecciona Tipo de factura: Manual o XML.\n"
            "3. Selecciona Cliente.\n"
            "4. En modo Manual, llena periodo de operacion, descripcion, fecha y montos.\n"
            "5. En modo XML, carga el XML.\n"
            "6. Usa Preview cuando aplique.\n"
            "7. Presiona Facturar y valida numero_documento creado.\n"
            "Paso a paso nota de credito:\n"
            "1. Presiona Nota de Credito Independiente.\n"
            "2. Selecciona modo manual o XML si la pantalla lo permite.\n"
            "3. Completa cliente, documento relacionado, motivo, fecha, moneda y monto.\n"
            "4. Guarda y valida impacto en Collections."
        ),
    },
    {
        "category": "Finanzas - Billing",
        "question": "Billing: Como usar filtros y tabla de facturas?",
        "answer": (
            "Billing consulta documentos generados y permite ver/descargar/exportar.\n"
            "Paso a paso:\n"
            "1. Entra a Invoicing & Billing > pestana Billing.\n"
            "2. Cliente: selecciona ALL o un cliente especifico.\n"
            "3. Desde/Hasta: selecciona fechas con calendario.\n"
            "4. Tipo Factura: filtra MANUAL o ELECTRONICA.\n"
            "5. Documento: filtra FACTURA o NOTA_CREDITO.\n"
            "6. Presiona Buscar.\n"
            "7. En la tabla revisa ID, tipo factura, documento, numero, cliente, fecha, moneda, total y estado.\n"
            "8. Usa Ver Factura para abrir preview.\n"
            "9. Usa Descargar PDF para guardar el documento.\n"
            "10. Usa Exportar CSV/Excel para reporte; numeros largos deben salir como texto."
        ),
    },
    {
        "category": "Finanzas - Collections",
        "question": "Collections: Como usar filtros, KPIs y sincronizar facturas?",
        "answer": (
            "Collections gestiona cuentas por cobrar.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Collections.\n"
            "2. Presiona el combo Cliente para cargar clientes desde Collections.\n"
            "3. Selecciona Cliente o deja ALL.\n"
            "4. Aging: filtra CURRENT, 1-30, 31-60, 61-90 o 90+.\n"
            "5. Estado: filtra EMITIDA, PENDIENTE_PAGO, PAGADA, DISPUTADA o WRITE_OFF.\n"
            "6. Disputada: filtra True o False.\n"
            "7. Presiona Buscar.\n"
            "8. Revisa KPIs: Total AR, Current, Overdue y Over 90.\n"
            "9. Si faltan facturas emitidas, presiona Sincronizar facturas.\n"
            "10. Confirma y revisa cuantas facturas nuevas se insertaron.\n"
            "11. Vuelve a Buscar para refrescar tabla y KPIs."
        ),
    },
    {
        "category": "Finanzas - Collections",
        "question": "Collections: Como usar la tabla, ver factura, disputar y aplicar pago?",
        "answer": (
            "La tabla de Collections permite acciones sobre cada cuenta por cobrar.\n"
            "Paso a paso:\n"
            "1. Busca datos con filtros.\n"
            "2. Selecciona una factura en la tabla.\n"
            "3. Ver factura: abre el documento o preview asociado.\n"
            "4. Disputar: abre popup para crear disputa con motivo y comentario.\n"
            "5. Aplicar pago / NC: abre popup para aplicar pago o nota de credito.\n"
            "6. Generar estado de cuenta: usa los registros cargados para crear estado por cliente.\n"
            "7. Exportar CSV/Excel descarga la tabla.\n"
            "8. Exportar PDF (Estado de Cuenta) genera estado de cuenta en PDF.\n"
            "9. Las filas vencidas se resaltan para priorizar cobranza.\n"
            "10. Usa paginacion para revisar mas resultados."
        ),
    },
    {
        "category": "Finanzas - Collections",
        "question": "Collections: Que campos se llenan al aplicar pago o nota de credito?",
        "answer": (
            "Aplicar pago/NC reduce el saldo pendiente.\n"
            "Paso a paso:\n"
            "1. Selecciona una factura en Collections.\n"
            "2. Presiona Aplicar pago / NC.\n"
            "3. Tipo de aplicacion: selecciona Pago o Nota de Credito.\n"
            "4. Si es Pago, llena Banco, Fecha de pago, Comision, Referencia y Monto a aplicar.\n"
            "5. Fecha de pago se selecciona con calendario y se guarda normalizada.\n"
            "6. Si es Nota de Credito, selecciona la nota disponible desde el combo.\n"
            "7. Presiona Aplicar.\n"
            "8. Confirma que saldo_pendiente se reduzca.\n"
            "9. Si el saldo queda en cero, la factura debe quedar pagada/cerrada segun backend.\n"
            "10. Sincroniza Accounting si corresponde."
        ),
    },
    {
        "category": "Finanzas - Collections",
        "question": "Collections: Como generar estado de cuenta Word o PDF?",
        "answer": (
            "Estado de cuenta usa la informacion cargada en la tabla.\n"
            "Paso a paso:\n"
            "1. Aplica filtros y presiona Buscar.\n"
            "2. Verifica que la tabla tenga facturas del cliente correcto.\n"
            "3. Presiona Generar estado de cuenta o Exportar PDF (Estado de Cuenta).\n"
            "4. En el popup selecciona idioma.\n"
            "5. Completa datos bancarios solicitados.\n"
            "6. Presiona Continuar.\n"
            "7. El sistema genera Word/PDF segun la opcion.\n"
            "8. Revisa numeros de factura completos, saldos, fechas y datos bancarios.\n"
            "9. Si no hay datos cargados, primero debes Buscar."
        ),
    },
    {
        "category": "Finanzas - Bank Reconciliation",
        "question": "Bank Reconciliation: Como buscar y revisar pagos?",
        "answer": (
            "Bank Reconciliation revisa pagos bancarios y su aplicacion.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Bank Reconciliation.\n"
            "2. Selecciona Cliente o ingresa Referencia Bancaria / Comprobante.\n"
            "3. Si quieres consultar sin filtros, marca Ver todos.\n"
            "4. Presiona Buscar.\n"
            "5. La tabla muestra Banco, Fecha de Pago, Cliente, Documento, Referencia, Tipo, Monto Recibido, Monto Aplicado, Saldo y Estado.\n"
            "6. Selecciona un pago y presiona Ver Detalle del Pago.\n"
            "7. Tambien puedes hacer doble click sobre la fila.\n"
            "8. Usa Limpiar para borrar filtros y tabla.\n"
            "9. Si no seleccionas cliente/referencia ni Ver todos, el sistema te pide filtros."
        ),
    },
    {
        "category": "Finanzas - Bank Reconciliation",
        "question": "Bank Reconciliation: Como registrar pago manual?",
        "answer": (
            "Registrar Pago Manual crea un ingreso cuando no viene de integracion bancaria.\n"
            "Paso a paso:\n"
            "1. En Bank Reconciliation presiona Registrar Pago Manual.\n"
            "2. Selecciona Cliente.\n"
            "3. Llena Banco.\n"
            "4. Llena Numero de Referencia.\n"
            "5. Selecciona Fecha de Pago con calendario.\n"
            "6. Llena Documento si corresponde.\n"
            "7. Llena Monto.\n"
            "8. Presiona Registrar Pago.\n"
            "9. El pago debe aparecer en Bank Reconciliation/Incoming Payments.\n"
            "10. Luego puedes aplicarlo contra Collections."
        ),
    },
    {
        "category": "Finanzas - Disputes",
        "question": "Disputes: Como buscar y gestionar disputas?",
        "answer": (
            "Disputes permite administrar casos creados desde Collections u otros flujos.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Disputes.\n"
            "2. Selecciona Cliente en el combo.\n"
            "3. Presiona Buscar.\n"
            "4. Revisa KPIs del modulo.\n"
            "5. La tabla muestra Dispute, Documento, Codigo Cliente, Cliente, Fecha Factura, Vencimiento, Monto, Status, Motivo, Comentario, Buque, Operacion, Periodo, Descripcion y Creado.\n"
            "6. Selecciona una disputa y presiona Gestionar Disputa.\n"
            "7. Tambien puedes abrirla con doble click.\n"
            "8. En el popup actualiza responsable, estado, motivo, comentario o resolucion segun campos disponibles.\n"
            "9. Guarda y vuelve a buscar para refrescar KPIs y tabla.\n"
            "10. Mantiene trazabilidad de reclamos de facturacion/cobranza."
        ),
    },
    {
        "category": "Finanzas - Credit Hold",
        "question": "Credit Order Hold and Release: Como buscar cliente y revisar exposicion?",
        "answer": (
            "Credit Control define terminos crediticios y calcula exposicion.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Credit (Order Hold & Release).\n"
            "2. Selecciona Cliente desde el combo codigo - nombre.\n"
            "3. Presiona Buscar.\n"
            "4. Si el cliente no tiene terminos crediticios, el sistema avisa y abre popup para asignarlos.\n"
            "5. Si existe configuracion, revisa Termino de pago, Limite de credito, Moneda, Estado y Observaciones.\n"
            "6. Revisa Exposicion Crediticia: Total facturado, Disponible, Exposicion, Avg dias de pago y Payment trend.\n"
            "7. Observa semaforo: disponible, critico o sobregirado.\n"
            "8. Usa Editar para modificar terminos.\n"
            "9. Usa Eliminar solo si deseas remover configuracion crediticia del cliente.\n"
            "10. Este modulo ayuda a decidir hold/release antes de aceptar mas operaciones."
        ),
    },
    {
        "category": "Finanzas - Credit Hold",
        "question": "Credit Order Hold and Release: Que campos se llenan al asignar o editar credito?",
        "answer": (
            "La configuracion crediticia define limite y condiciones del cliente.\n"
            "Paso a paso:\n"
            "1. Busca cliente en Credit Control.\n"
            "2. Si no tiene credito, completa el popup inicial; si ya tiene, presiona Editar.\n"
            "3. Termino de pago: ingresa dias o condicion de pago.\n"
            "4. Limite de credito: ingresa monto autorizado.\n"
            "5. Moneda: selecciona o ingresa moneda del limite.\n"
            "6. Estado: define ACTIVE/HOLD/RELEASE u opciones del formulario.\n"
            "7. Observaciones: explica condiciones, aprobaciones o restricciones.\n"
            "8. Guarda.\n"
            "9. Vuelve a Buscar para recalcular disponible y exposicion.\n"
            "10. Si el cliente queda sobregirado, coordina aprobacion antes de liberar orden."
        ),
    },
    {
        "category": "Finanzas - Invoice To Pay",
        "question": "Invoice To Pay: Como buscar obligaciones y leer KPIs?",
        "answer": (
            "Invoice To Pay controla cuentas por pagar.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Invoice To Pay.\n"
            "2. Filtra por tipo de obligacion, beneficiario/payee y status.\n"
            "3. Filtra por Fecha factura desde/hasta.\n"
            "4. Filtra por Fecha vencimiento desde/hasta.\n"
            "5. Filtra por Ultimo pago desde/hasta.\n"
            "6. Presiona Buscar.\n"
            "7. Revisa KPIs: Pending Payables, Paid Amount, Avg Payment Days y Overdue Amount.\n"
            "8. Revisa alertas de pagos proximos y vencidos.\n"
            "9. La tabla muestra beneficiario, obligacion, referencia, fechas, buque, pais, operacion, moneda, total, saldo, ultimo pago y estado.\n"
            "10. Las obligaciones vencidas se marcan visualmente."
        ),
    },
    {
        "category": "Finanzas - Invoice To Pay",
        "question": "Invoice To Pay: Como registrar obligacion, cargar PDF/XML, aplicar pago y eliminar?",
        "answer": (
            "Invoice To Pay permite crear, cargar, pagar y eliminar obligaciones.\n"
            "Paso a paso registrar obligacion:\n"
            "1. Presiona Registrar obligacion manual.\n"
            "2. Completa proveedor/beneficiario, referencia, fechas, total, moneda, buque/pais/operacion si aplica.\n"
            "3. Guarda y busca nuevamente.\n"
            "Paso a paso cargar factura:\n"
            "1. Presiona Cargar factura PDF / XML.\n"
            "2. Selecciona archivo y completa datos requeridos.\n"
            "3. Guarda.\n"
            "Paso a paso aplicar pago:\n"
            "1. Selecciona una obligacion con saldo mayor a cero.\n"
            "2. Presiona Aplicar pago.\n"
            "3. Ingresa Payment Amount y Payment Date con calendario.\n"
            "4. Guarda.\n"
            "Paso a paso eliminar:\n"
            "1. Selecciona una obligacion.\n"
            "2. Presiona Eliminar.\n"
            "3. Confirma solo si no debe conservarse trazabilidad."
        ),
    },
    {
        "category": "Finanzas - Accounting",
        "question": "Accounting: Como buscar TC, filtrar asientos y sincronizar contabilidad?",
        "answer": (
            "Accounting exige tipo de cambio antes de consultar/sincronizar asientos.\n"
            "Paso a paso:\n"
            "1. Entra a Finanzas > Accounting.\n"
            "2. Presiona Buscar TC para obtener tipo de cambio BCCR.\n"
            "3. Confirma TC y Fecha.\n"
            "4. Selecciona Buscar por Periodo o Rango.\n"
            "5. Periodo: usa el periodo actual o anterior disponible.\n"
            "6. Rango: selecciona Desde y Hasta; Desde no puede ser mayor que Hasta.\n"
            "7. Origen: elige TODOS, ITP, COLLECTIONS, INVOICING, MANUAL o CASH_APP.\n"
            "8. Cuenta: abre el combo para cargar catalogo y selecciona cuenta si aplica.\n"
            "9. Presiona Buscar.\n"
            "10. Antes de consultar, el sistema sincroniza Collections, Cash App, ITP y Payroll.\n"
            "11. Revisa KPIs Total Debe, Total Haber e IVA.\n"
            "12. Si no hay TC, el sistema no debe continuar."
        ),
    },
    {
        "category": "Finanzas - Accounting",
        "question": "Accounting: Como usar acciones, reportes, cierre y declaraciones?",
        "answer": (
            "El menu Acciones contiene cierres, asientos, ajustes, reversas, declaraciones y reportes.\n"
            "Paso a paso:\n"
            "1. Carga TC y presiona Buscar para tener asientos en tabla.\n"
            "2. Acciones > Mayorizar / Cierre contable abre wizard de cierre.\n"
            "3. Acciones > Asiento manual abre popup para crear asiento manual.\n"
            "4. Selecciona un asiento y usa Ajustar asiento para corregir.\n"
            "5. Selecciona un asiento y usa Reversar asiento para revertir.\n"
            "6. Declaraciones > D-150 abre IVA; D-101 y D-270 aparecen como pendientes si no estan implementadas.\n"
            "7. Reportes permite Asientos, Libro Mayor, Balance de Comprobacion, Estado de Situacion Financiera, Estado de Resultados y Flujo de Caja.\n"
            "8. En el selector de reportes elige periodo unico o rango.\n"
            "9. Exporta en Excel/PDF segun reporte disponible.\n"
            "10. Antes de cerrar periodo, valida que debe y haber cuadren y que reportes salgan correctos."
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
        "category": "Comercial - Pizarra",
        "question": "Manual Comercial Pizarra: Como usar la pantalla principal?",
        "answer": (
            "La pizarra comercial muestra servicios operativos desde una vista ejecutiva.\n"
            "Paso a paso:\n"
            "1. Entra a Comercial.\n"
            "2. Revisa la tabla con consec, tipo, estado, num_informe, buque/contenedor, cliente, operacion, surveyor, pais, puerto, fechas, demoras y duracion.\n"
            "3. Filtra por Cliente, Pais, Puerto, Surveyor y Ano.\n"
            "4. Marca o desmarca estados: Confirmado, En Operacion, Finalizado y Cancelado.\n"
            "5. Presiona Buscar para cargar datos.\n"
            "6. Usa Limpiar para reiniciar filtros.\n"
            "7. Usa Anterior/Siguiente para paginar.\n"
            "8. Si el usuario es surveyor01/surveyor02, solo ve la pizarra; no ve botones de Clientes, Puertos, Servicios, Cotizaciones ni Precios."
        ),
    },
    {
        "category": "Comercial - Clientes",
        "question": "Manual Comercial Clientes: Como analizar clientes y abrir detalle?",
        "answer": (
            "Clientes es una vista de analytics comercial por cliente.\n"
            "Paso a paso:\n"
            "1. Entra a Comercial > Clientes.\n"
            "2. Filtra por Ano, rango Desde/Hasta, Cliente y Servicio.\n"
            "3. Presiona Buscar para traer actividad comercial.\n"
            "4. Revisa KPIs de clientes, servicios y resultados asociados.\n"
            "5. Revisa la tabla paginada de actividad por cliente.\n"
            "6. Selecciona un cliente en la tabla.\n"
            "7. Presiona Ver cliente seleccionado para abrir el popup de detalle.\n"
            "8. Usa Exportar Excel o PDF para descargar el analisis."
        ),
    },
    {
        "category": "Comercial - Puertos",
        "question": "Manual Comercial Puertos: Como revisar analytics y cobertura por puerto?",
        "answer": (
            "Puertos permite analizar actividad por continente, pais y puerto.\n"
            "Paso a paso:\n"
            "1. Entra a Comercial > Puertos.\n"
            "2. Filtra por Ano desde, Ano hasta o Ano exacto.\n"
            "3. Filtra por Continente, Pais y Cliente.\n"
            "4. Presiona Buscar.\n"
            "5. Revisa KPIs: clientes, paises, puertos, facturado, costos, margen bruto, margen neto y rentabilidad.\n"
            "6. Revisa la tabla de total de operaciones, frecuencia, ticket promedio y Pareto 80.\n"
            "7. Usa Cobertura de Puertos para abrir el popup de cobertura.\n"
            "8. En el popup, filtra por umbral minimo, estado, continente, pais y puerto.\n"
            "9. Usa Actualizar, paginacion y Cerrar segun corresponda."
        ),
    },
    {
        "category": "Comercial - Servicios",
        "question": "Manual Comercial Servicios: Como analizar servicios ofrecidos y no ofrecidos?",
        "answer": (
            "Servicios analiza rentabilidad y frecuencia por servicio.\n"
            "Paso a paso:\n"
            "1. Entra a Comercial > Servicios.\n"
            "2. Selecciona modo de anos: RANGO o EXACTO.\n"
            "3. Filtra por Ano desde/hasta, Continente, Pais, Puerto, Servicio y Quarter cuando aplique.\n"
            "4. Presiona Buscar.\n"
            "5. Revisa KPIs: servicios, facturado, costos, margen bruto, margen neto y rentabilidad.\n"
            "6. Revisa la tabla Servicios Ofrecidos.\n"
            "7. Usa Exportar CSV o Excel si necesitas descargar la informacion.\n"
            "8. Usa Ver servicios NO ofrecidos para revisar servicios del catalogo que no han tenido ejecucion.\n"
            "9. Usa Ver costos por Surveyor (Pareto 80/20) para analizar costo operativo por surveyor."
        ),
    },
    {
        "category": "Comercial - Precios",
        "question": "Manual Comercial Precios: Como buscar, agregar, editar, eliminar y exportar precios?",
        "answer": (
            "Precios define la matriz comercial necesaria para cotizar.\n"
            "Paso a paso:\n"
            "1. Entra a Comercial > Precios.\n"
            "2. Filtra por Servicio, Cliente, Continente, Pais y Puerto.\n"
            "3. La ubicacion debe funcionar en cascada: Continente filtra Paises y Pais filtra Puertos.\n"
            "4. Presiona Buscar para ver precios configurados.\n"
            "5. Usa Agregar Precio para crear una regla comercial.\n"
            "6. Usa Editar Precio para modificar servicio, cliente, ubicacion, precio o activo.\n"
            "7. Usa Eliminar Precio solo si confirmas que esa combinacion ya no se debe usar.\n"
            "8. Usa Exportar para descargar Excel o CSV.\n"
            "9. Si no existe precio activo para Cliente + Servicio + Puerto, Nueva Cotizacion no podra agregar ese servicio."
        ),
    },
    {
        "category": "Comercial - Precios",
        "question": "Manual Comercial Precios: Como llenar el popup Agregar Precio?",
        "answer": (
            "Agregar Precio crea una combinacion comercial usada por cotizaciones.\n"
            "Paso a paso:\n"
            "1. Presiona Agregar Precio.\n"
            "2. Selecciona Servicio; el servicio debe existir previamente en Master Data/catalogo.\n"
            "3. Selecciona Cliente; el cliente debe existir previamente en Master Data.\n"
            "4. Selecciona Continente.\n"
            "5. Selecciona Pais; la lista depende del continente.\n"
            "6. Selecciona Puerto; la lista depende del pais.\n"
            "7. Digita Precio como numero mayor a cero.\n"
            "8. Presiona Guardar.\n"
            "9. Si falta servicio, cliente o precio valido, el popup debe bloquear el guardado."
        ),
    },
    {
        "category": "Comercial - Precios",
        "question": "Manual Comercial Precios: Como editar o desactivar un precio?",
        "answer": (
            "Editar Precio cambia una regla comercial existente.\n"
            "Paso a paso:\n"
            "1. Busca el precio en Comercial > Precios.\n"
            "2. Selecciona la fila.\n"
            "3. Presiona Editar Precio.\n"
            "4. Ajusta Servicio, Cliente, Continente, Pais, Puerto o Precio.\n"
            "5. Usa Activo para habilitar o deshabilitar la regla.\n"
            "6. Presiona Guardar.\n"
            "7. Una regla inactiva no debe estar disponible para nuevas cotizaciones.\n"
            "8. Si el precio ya no aplica pero quieres conservar historial, es preferible desactivarlo antes que eliminarlo."
        ),
    },
    {
        "category": "Comercial - Cotizaciones",
        "question": "Manual Comercial Cotizaciones: Como buscar, aprobar, cancelar, eliminar y exportar?",
        "answer": (
            "Cotizaciones administra propuestas comerciales y sus estados.\n"
            "Paso a paso:\n"
            "1. Entra a Comercial > Cotizaciones.\n"
            "2. Filtra por Cliente, Servicio, Continente, Pais, Puerto y Status.\n"
            "3. Usa el boton ... para seleccionar servicios cuando la lista sea grande.\n"
            "4. Presiona Buscar.\n"
            "5. Revisa KPIs de clientes, servicios, paises, puertos, pendientes, aprobadas y canceladas.\n"
            "6. Usa Nueva Cotizacion para crear una propuesta.\n"
            "7. En Acciones > Aprobar, solo puedes aprobar cotizaciones en status PENDIENTE; al aprobar se abre el popup para crear servicio.\n"
            "8. En Acciones > Cancelar, solo puedes cancelar PENDIENTE y debes indicar razon.\n"
            "9. En Acciones > Eliminar, confirma antes de borrar.\n"
            "10. Usa Exportar para descargar Excel o CSV con fechas en formato LONG ingles."
        ),
    },
    {
        "category": "Comercial - Cotizaciones",
        "question": "Manual Comercial Cotizaciones: Como crear una nueva cotizacion?",
        "answer": (
            "Nueva Cotizacion depende de precios activos previamente configurados.\n"
            "Paso a paso:\n"
            "1. Antes de cotizar, confirma que el cliente exista en Master Data.\n"
            "2. Confirma que el servicio exista en Master Data/catalogo.\n"
            "3. Confirma que exista precio activo para Cliente + Servicio + Continente/Pais/Puerto en Comercial > Precios.\n"
            "4. Entra a Comercial > Cotizaciones > Nueva Cotizacion.\n"
            "5. Selecciona Cliente; esto carga opciones disponibles de precios.\n"
            "6. Selecciona Continente, Pais y Puerto en cascada.\n"
            "7. Selecciona Idioma ES o EN, Validez en dias y Formato WORD/PDF.\n"
            "8. Selecciona Servicio y presiona Agregar Servicio.\n"
            "9. Si no existe precio para esa combinacion, el sistema debe advertirlo.\n"
            "10. Revisa total, texto editable y servicios agregados.\n"
            "11. Presiona Confirmar y Guardar para crear la cotizacion en status PENDIENTE."
        ),
    },
    {
        "category": "Comercial - Cotizaciones",
        "question": "Manual Comercial Cotizaciones: Como usar preview, texto editable y exportar WORD/PDF?",
        "answer": (
            "El popup de cotizacion permite editar el texto antes de exportar o guardar.\n"
            "Paso a paso:\n"
            "1. Crea una Nueva Cotizacion.\n"
            "2. Agrega uno o varios servicios.\n"
            "3. Revisa el texto de la cotizacion en el cuadro editable.\n"
            "4. En idioma ES debe iniciar con Estimado cliente; en EN debe iniciar con Dear client.\n"
            "5. Ajusta redaccion, condiciones o informacion adicional si aplica.\n"
            "6. Usa Exportar WORD para generar .docx sin guardar necesariamente.\n"
            "7. Usa Exportar PDF para generar PDF con formato comercial/marca de agua cuando aplique.\n"
            "8. Usa Confirmar y Guardar para enviar la cotizacion al backend.\n"
            "9. No guardes cotizaciones sin al menos un servicio agregado."
        ),
    },
    {
        "category": "Comercial - Cotizaciones",
        "question": "Manual Comercial Cotizaciones: Que pasa al aprobar una cotizacion?",
        "answer": (
            "Aprobar una cotizacion convierte la oportunidad en flujo operativo.\n"
            "Paso a paso:\n"
            "1. En Cotizaciones, selecciona una fila en status PENDIENTE.\n"
            "2. Abre Acciones > Aprobar.\n"
            "3. Confirma la aprobacion.\n"
            "4. El sistema cambia status a APROBADO.\n"
            "5. Luego abre el popup de Servicio para registrar la operacion.\n"
            "6. En ese popup se completa la informacion operativa necesaria.\n"
            "7. Cuando el servicio queda creado, Comercial y Servicios quedan conectados.\n"
            "8. Si la cotizacion no esta PENDIENTE, no se debe aprobar."
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
        "question": "Manual HHRR: Como navegar el modulo segun rol?",
        "answer": (
            "HHRR cambia la pantalla segun el rol del usuario.\n"
            "Paso a paso:\n"
            "1. Abre HHRR desde el menu lateral del ERP.\n"
            "2. Revisa la pizarra de noticias/comunicados en la pantalla inicial.\n"
            "3. Si eres empleado, veras Colillas, Solicitudes, Horas y Politicas.\n"
            "4. Si tienes rol administrativo, tambien veras Empleados y funciones de aprobacion.\n"
            "5. Usa Volver para regresar al menu principal de HHRR.\n"
            "6. Si un boton no aparece, el rol no tiene permiso para esa funcion.\n"
            "7. Los empleados pueden consultar y descargar, pero no deben postear ni actualizar datos restringidos."
        ),
    },
    {
        "category": "HHRR - Noticias",
        "question": "Manual HHRR Noticias: Como consultar o publicar noticias?",
        "answer": (
            "Noticias muestra comunicados internos para el personal.\n"
            "Paso a paso:\n"
            "1. Entra a HHRR.\n"
            "2. Lee el panel de noticias de la pantalla principal.\n"
            "3. Si tienes permiso administrativo, usa el popup de noticias para publicar o actualizar comunicados.\n"
            "4. Escribe titulo, contenido y vigencia si el formulario lo solicita.\n"
            "5. Guarda la noticia.\n"
            "6. Verifica que aparezca en la pantalla principal.\n"
            "7. Usuarios empleados solo deben consultar la informacion publicada."
        ),
    },
    {
        "category": "HHRR - Empleados",
        "question": "Manual HHRR Empleados: Como buscar, ver, crear o editar empleados?",
        "answer": (
            "Empleados es una pantalla administrativa.\n"
            "Paso a paso:\n"
            "1. Entra a HHRR > Empleados.\n"
            "2. Usa filtros de Nombre, Codigo, Estado y Usuario.\n"
            "3. Presiona Buscar para aplicar filtros.\n"
            "4. Usa Limpiar para quitar filtros.\n"
            "5. Usa Nuevo empleado para abrir el formulario en modo creacion.\n"
            "6. Selecciona una fila y presiona Ver para consulta.\n"
            "7. Selecciona una fila y presiona Editar para modificar datos.\n"
            "8. Usa paginacion para recorrer resultados cuando hay muchos empleados."
        ),
    },
    {
        "category": "HHRR - Empleados",
        "question": "Manual HHRR Empleados: Que campos se llenan en el formulario?",
        "answer": (
            "El formulario de empleado concentra datos personales, contacto y datos laborales.\n"
            "Paso a paso:\n"
            "1. Completa Codigo, Cedula ID, Nombre y Apellidos.\n"
            "2. Selecciona Estado civil, Genero, Nacionalidad y Usuario si aplica.\n"
            "3. Selecciona Fecha nacimiento con calendario; se muestra LONG en ingles y se guarda normalizada para backend.\n"
            "4. Completa Prefijo, Telefono, Provincia, Canton, Distrito y Direccion.\n"
            "5. En datos laborales llena Jornada, Estado, Salario, Pago, Banco, Cuenta IBAN y Moneda.\n"
            "6. Selecciona Fecha ingreso con calendario.\n"
            "7. Completa Horas contratadas, Vacaciones, Enfermedades y contacto de emergencia.\n"
            "8. Guarda y verifica que el empleado aparezca en la tabla."
        ),
    },
    {
        "category": "HHRR - Solicitudes",
        "question": "Manual HHRR Solicitudes: Como buscar, crear y exportar solicitudes?",
        "answer": (
            "Solicitudes gestiona vacaciones, documentos, incapacidades y otros requerimientos.\n"
            "Paso a paso:\n"
            "1. Entra a HHRR > Solicitudes.\n"
            "2. Filtra por Empleado, Estado y Tipo.\n"
            "3. Presiona Buscar o Aplicar filtros.\n"
            "4. Usa Limpiar para reiniciar la busqueda.\n"
            "5. Usa + Nueva Solicitud para crear una solicitud.\n"
            "6. Usa Info aprobaciones para revisar criterios o flujo de aprobacion.\n"
            "7. Usa Exportar para generar CSV/Excel si tienes permiso.\n"
            "8. Revisa paginacion y estado de cada solicitud."
        ),
    },
    {
        "category": "HHRR - Solicitudes",
        "question": "Manual HHRR Solicitudes: Como llenar una nueva solicitud?",
        "answer": (
            "Nueva Solicitud cambia campos segun el tipo seleccionado.\n"
            "Paso a paso:\n"
            "1. Presiona + Nueva Solicitud.\n"
            "2. Selecciona Tipo de solicitud.\n"
            "3. Para vacaciones, selecciona Desde y Hasta con calendario y revisa dias solicitados/saldo.\n"
            "4. Para documentos, selecciona Tipo de documento y completa el detalle.\n"
            "5. Para incapacidad, selecciona Desde, Hasta y agrega observaciones.\n"
            "6. Completa Motivo o comentario si el popup lo muestra.\n"
            "7. Revisa saldo disponible y saldo restante cuando aplique.\n"
            "8. Presiona Enviar solicitud.\n"
            "9. Cancela solo si no deseas guardar."
        ),
    },
    {
        "category": "HHRR - Solicitudes",
        "question": "Manual HHRR Solicitudes: Como aprobar o rechazar solicitudes?",
        "answer": (
            "La aprobacion es funcion administrativa.\n"
            "Paso a paso:\n"
            "1. Entra a HHRR > Solicitudes.\n"
            "2. Filtra por estado pendiente si necesitas revisar solo nuevas solicitudes.\n"
            "3. Selecciona la solicitud.\n"
            "4. Abre el popup de aprobacion o detalle.\n"
            "5. Revisa empleado, tipo, fechas, saldo y observaciones.\n"
            "6. Presiona Aprobar si procede.\n"
            "7. Presiona Rechazar si no procede y registra motivo cuando el sistema lo solicite.\n"
            "8. Verifica que el estado cambie en la tabla."
        ),
    },
    {
        "category": "HHRR - Registro Horas",
        "question": "Manual HHRR Registro de Horas: Como registra horas un empleado?",
        "answer": (
            "Registro de Horas permite al empleado reportar horas trabajadas.\n"
            "Paso a paso:\n"
            "1. Entra a HHRR > Horas.\n"
            "2. Revisa el resumen: empleado, horas contratadas, registradas y pendientes.\n"
            "3. Filtra por Tipo o Estado si deseas revisar registros previos.\n"
            "4. Presiona Registrar horas.\n"
            "5. Selecciona fecha con calendario; se muestra LONG en ingles y se guarda en formato backend.\n"
            "6. Completa hora inicial, hora final, tipo de hora y detalle.\n"
            "7. Guarda el registro.\n"
            "8. Si te equivocaste y el estado lo permite, selecciona el registro y usa Eliminar seleccionado."
        ),
    },
    {
        "category": "HHRR - Registro Horas",
        "question": "Manual HHRR Registro de Horas Admin: Como revisar, aprobar o rechazar horas?",
        "answer": (
            "La vista admin permite controlar horas registradas por usuarios.\n"
            "Paso a paso:\n"
            "1. Entra a HHRR > Horas con rol administrativo.\n"
            "2. Filtra por Usuario, Tipo y Estado.\n"
            "3. Usa Buscar/Reload para actualizar resultados.\n"
            "4. Usa Nuevo registro si necesitas crear una entrada administrativa.\n"
            "5. Selecciona una fila y usa Ver para revisar detalle.\n"
            "6. Usa Aprobar cuando la hora corresponde.\n"
            "7. Usa Rechazar cuando no corresponde y registra motivo si aplica.\n"
            "8. Usa Eliminar solo cuando el registro deba retirarse.\n"
            "9. Export CSV descarga la tabla para analisis externo."
        ),
    },
    {
        "category": "HHRR - Colillas",
        "question": "Manual HHRR Colillas: Como consultar o descargar colillas?",
        "answer": (
            "Colillas permite descargar comprobantes de pago en PDF.\n"
            "Paso a paso:\n"
            "1. Entra a HHRR > Colillas.\n"
            "2. Si eres empleado, el sistema debe mostrar solo tus colillas disponibles.\n"
            "3. Selecciona la colilla por periodo.\n"
            "4. Presiona Descargar colilla o Descargar PDF.\n"
            "5. Si el sistema indica usuario no autenticado, vuelve a iniciar sesion y repite.\n"
            "6. Si eres admin, puedes cargar o generar colillas segun permisos.\n"
            "7. Valida que el archivo PDF descargado corresponda al empleado y periodo correcto."
        ),
    },
    {
        "category": "HHRR - Planilla",
        "question": "Manual HHRR Planilla: Como generar planilla o colillas desde admin?",
        "answer": (
            "Planilla es una funcion administrativa para generar periodos de pago.\n"
            "Paso a paso:\n"
            "1. Entra a la vista administrativa de planilla/colillas.\n"
            "2. Selecciona Ano y Mes.\n"
            "3. Presiona Generar Planilla.\n"
            "4. Abre la colilla del empleado si necesitas revisar detalle.\n"
            "5. Verifica empleado, periodo, salario, valor hora extra y deducciones.\n"
            "6. Usa Preview antes de generar PDF.\n"
            "7. Presiona Generar PDF cuando este correcto.\n"
            "8. Confirma que el registro quede disponible para descarga."
        ),
    },
    {
        "category": "HHRR - Politicas",
        "question": "Manual HHRR Politicas: Como consultar o administrar politicas internas?",
        "answer": (
            "Politicas contiene documentos internos de la empresa.\n"
            "Paso a paso:\n"
            "1. Entra a HHRR > Politicas.\n"
            "2. Selecciona la politica que deseas leer.\n"
            "3. Abre el lector para consultar el contenido.\n"
            "4. Si tienes rol administrativo, usa el popup CRUD para crear o editar politicas.\n"
            "5. Completa titulo, categoria, contenido y estado si aplica.\n"
            "6. Guarda cambios.\n"
            "7. Verifica que empleados puedan consultar la politica publicada."
        ),
    },
    {
        "category": "HHRR - Liquidacion",
        "question": "Manual HHRR Liquidacion: Como calcular liquidacion laboral?",
        "answer": (
            "Liquidacion laboral calcula montos finales segun datos del empleado.\n"
            "Paso a paso:\n"
            "1. Abre el popup de Liquidacion Laboral desde la funcion administrativa correspondiente.\n"
            "2. Selecciona empleado.\n"
            "3. Selecciona Tipo de despido o salida.\n"
            "4. Selecciona Fecha de salida con calendario.\n"
            "5. Revisa salario, fecha ingreso, vacaciones y datos laborales.\n"
            "6. Ejecuta el calculo.\n"
            "7. Revisa preaviso, cesantia, vacaciones, aguinaldo y totales.\n"
            "8. Exporta o guarda solo despues de validar los datos legales y laborales."
        ),
    },
    {
        "category": "HHRR - Permisos",
        "question": "Manual HHRR Permisos: Que puede hacer un empleado y que puede hacer admin?",
        "answer": (
            "HHRR separa permisos por rol.\n"
            "Paso a paso:\n"
            "1. Usuario empleado puede ver noticias, consultar colillas, crear/consultar solicitudes, registrar horas y leer politicas.\n"
            "2. Usuario empleado puede descargar colillas y documentos permitidos.\n"
            "3. Usuario empleado no debe crear empleados, aprobar solicitudes, aprobar horas ni modificar planilla.\n"
            "4. Usuario admin puede ver Empleados, crear/editar empleados y administrar politicas.\n"
            "5. Usuario admin puede aprobar/rechazar solicitudes y horas.\n"
            "6. Usuario admin puede generar planilla y colillas segun permisos.\n"
            "7. Si una opcion no aparece, revisa el rol/perfil del usuario."
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
        "category": "Informes - Flujo General",
        "question": "Manual Informes: Cual es el flujo correcto de seleccion, creacion y review?",
        "answer": (
            "Informes siempre debe partir de un servicio o registro existente, no de datos sueltos.\n"
            "Paso a paso:\n"
            "1. Entra a Informes.\n"
            "2. La primera pantalla debe mostrar solo Revisar Informes, Generar Informe, Calculadora de Proyectos y pizarra de pendientes.\n"
            "3. La pizarra muestra servicios finalizados cuyo num_informe no existe todavia en ninguna tabla de informes.\n"
            "4. Presiona Generar Informe para escoger familia: Contenedor, Buque o Certificados.\n"
            "5. En cada formulario usa Seleccionar Reporte o selector de num_informe.\n"
            "6. El selector carga datos base: num_informe, cliente, buque/contenedor, puerto, pais, operacion, fecha y detalle cuando existan en Servicios.\n"
            "7. Completa solo los campos tecnicos/narrativos que no vienen de Servicios.\n"
            "8. En creacion nueva, el boton principal debe ser Enviar a Revision y debe guardar con POST.\n"
            "9. Si abres desde Revisar Informes o desde Servicios un informe ya creado, debe cargar con GET.\n"
            "10. En modo review se habilitan Editar y Guardar Cambios; Guardar Cambios usa PUT.\n"
            "11. Aprobar/Rechazar cambia status; generar informe final usa datos revisados."
        ),
    },
    {
        "category": "Informes - Containers",
        "question": "Manual Containers: Que campos se llenan despues de seleccionar num_informe?",
        "answer": (
            "Container Report debe llenarse a partir del selector de reporte.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Contenedor.\n"
            "2. Presiona Seleccionar Reporte o el selector de num_informe.\n"
            "3. Busca el servicio finalizado pendiente.\n"
            "4. Selecciona la fila; el formulario debe cargar num_informe, cliente, pais, puerto, fecha y operacion.\n"
            "5. Completa Container Description: tipo de contenedor, condicion, numero de contenedor y sello si aplica.\n"
            "6. Completa Inspected Container: producto, cantidad, estado, empaque y hallazgos observados.\n"
            "7. Completa Transfer To Container si hubo transferencia o cambio de unidad.\n"
            "8. Marca documentos de calidad: Quality Documents, Sanitary Certificate, Phytosanitary Cert., Factory Certificate y Certificate of Origin segun corresponda.\n"
            "9. Completa narrativa de inspeccion, hallazgos, observaciones y conclusion.\n"
            "10. Usa PORTIA para mejorar textos, sin cambiar datos del contenedor ni documentos.\n"
            "11. Envia a Revision; desde Review se edita con PUT."
        ),
    },
    {
        "category": "Informes - Grain Sampling",
        "question": "Manual Grain Sampling: Como llenar puntos de muestreo por bodega?",
        "answer": (
            "Grain Sampling se centra en documentar puntos y condiciones de muestreo.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque > Muestreo de Granos.\n"
            "2. Selecciona num_informe desde el selector de servicios.\n"
            "3. Verifica certificado, cliente, buque, puerto, pais, producto y fechas.\n"
            "4. Completa fecha/hora de inicio y fecha/hora de finalizacion de muestreo.\n"
            "5. En Puntos de Muestreo por Bodega, registra cada bodega o punto inspeccionado.\n"
            "6. Para cada punto, indica bodega, ubicacion, metodo, cantidad o referencia de muestra si el formulario lo pide.\n"
            "7. Si hay multiples puntos por bodega, agregalos de forma separada para mantener trazabilidad.\n"
            "8. Describe condiciones: clima, acceso, estado de carga, observaciones de producto y cualquier incidencia.\n"
            "9. Registra responsables o representantes presentes si aplica.\n"
            "10. Completa conclusion indicando si el muestreo fue realizado/supervisado satisfactoriamente.\n"
            "11. Usa PORTIA solo para claridad de redaccion; no cambies numero de muestras, bodegas ni hechos."
        ),
    },
    {
        "category": "Informes - Truck Supervision",
        "question": "Manual Truck Supervision: Como llenar hallazgos y conclusion?",
        "answer": (
            "Truck Supervision documenta control operativo de camiones y documentacion.\n"
            "Paso a paso:\n"
            "1. Selecciona num_informe desde el selector.\n"
            "2. Confirma que se carguen cliente, buque, puerto, pais y fecha.\n"
            "3. Completa representantes: capitan, primer oficial u otros si aplica.\n"
            "4. Completa tiempos: arribo, inspeccion y supervision completada.\n"
            "5. En Proceso de Supervision, explica como se realizo el control operativo.\n"
            "6. En Hallazgos Documentales, registra guias, placas, consecutivos, sellos o documentos con errores.\n"
            "7. En Hallazgos de Control Operativo, registra patrones, rangos atipicos, controles faltantes o brechas.\n"
            "8. En Incidentes, registra unidades devueltas, motivos, responsables y placas si existen.\n"
            "9. En Conclusion, resume riesgos, mejoras, incidentes y recomendacion operativa.\n"
            "10. Usa PORTIA para mejorar redaccion de Proceso, Hallazgos y Conclusion.\n"
            "11. En creacion envia a revision; en Review usa Editar y Guardar Cambios."
        ),
    },
    {
        "category": "Informes - Draft Survey",
        "question": "Manual Draft Survey: Como iniciar, abrir previo o crear desde cero?",
        "answer": (
            "Draft Survey debe preguntar si se abre uno previo o se crea desde cero.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Buque > Draft Survey.\n"
            "2. El sistema pregunta si deseas realizar un reporte desde 0.\n"
            "3. Si respondes Si, abre DraftSurveyForm en modo creacion.\n"
            "4. Presiona Seleccionar Reporte para escoger el servicio desde el selector.\n"
            "5. El selector debe cargar servicios compatibles con Draft Survey y mostrar num_informe, cliente, buque, pais, puerto y fecha.\n"
            "6. Si respondes No, abre el selector de Draft existente.\n"
            "7. Busca por num_informe, buque, cliente o filtros disponibles.\n"
            "8. Presiona Cargar Draft para abrir el registro existente con GET.\n"
            "9. En Draft existente puedes revisar, editar y guardar cambios con PUT.\n"
            "10. Usa abrir Excel/previsualizar cuando necesites revisar calculos antes de enviar o aprobar."
        ),
    },
    {
        "category": "Informes - Draft Survey",
        "question": "Manual Draft Survey: Como llenar header, buque y datos generales?",
        "answer": (
            "El header de Draft Survey define la identidad del calculo y del documento final.\n"
            "Paso a paso:\n"
            "1. Selecciona el num_informe antes de llenar datos tecnicos.\n"
            "2. Verifica Cert No/Report No, cliente, buque, puerto, pais, fecha de reporte y operacion.\n"
            "3. Completa datos del buque: nombre, bandera/registro, GRT, NRT, IMO, year built y datos que el formulario solicite.\n"
            "4. Completa representantes: capitan/master, chief officer, surveyor y personas presentes.\n"
            "5. Completa puertos o lugares de operacion si hay loading/discharging port.\n"
            "6. Revisa producto/cargo, detalle y descripcion de operacion.\n"
            "7. Mantén fechas con formato LONG en pantalla y normalizadas para backend.\n"
            "8. No avances a calculos si el num_informe, buque o cliente no coinciden con Servicios.\n"
            "9. Guarda solo cuando el header corresponde al servicio correcto."
        ),
    },
    {
        "category": "Informes - Draft Survey",
        "question": "Manual Draft Survey: Como llenar drafts, constantes y correcciones?",
        "answer": (
            "Los drafts son la base del calculo; cualquier error cambia el peso final.\n"
            "Paso a paso:\n"
            "1. Identifica si estas llenando Initial, Final o Intermediate Draft Survey.\n"
            "2. Registra lecturas Forward, Midship y Aft en babor/estribor cuando el formulario lo solicite.\n"
            "3. Usa unidades consistentes; no mezcles metros, centimetros o pies si el template espera otra unidad.\n"
            "4. Registra trim, list y correcciones aplicables.\n"
            "5. Completa densidad de agua observada y densidad estandar si aplica.\n"
            "6. Completa displacement, TPC, LCF, MTC u otras constantes tomadas de tablas hidrostaticas.\n"
            "7. Revisa que el promedio de drafts sea razonable contra el estado de carga.\n"
            "8. Revisa que las correcciones no tengan signo invertido.\n"
            "9. Abre Excel/previsualizacion para confirmar formulas.\n"
            "10. Si el resultado se ve fuera de rango, no envies a revision hasta revisar lecturas y constantes."
        ),
    },
    {
        "category": "Informes - Draft Survey",
        "question": "Manual Draft Survey: Como llenar ballast, fresh water, fuel, diesel y tanques?",
        "answer": (
            "Ballast y tanques son la parte mas sensible del Draft Survey despues de las lecturas.\n"
            "Paso a paso:\n"
            "1. Abre la seccion de tanques/ballast del Draft Survey.\n"
            "2. Registra cada tanque de ballast por nombre, sounding/ullage, volumen y densidad si aplica.\n"
            "3. Verifica si el tanque se suma o se resta segun el calculo del formulario.\n"
            "4. Registra Fresh Water con nombre de tanque, cantidad y observacion si aplica.\n"
            "5. Registra Fuel Oil, Diesel/MGO, Lube Oil u otros consumibles con cantidad correcta.\n"
            "6. Si el formulario permite cargar tanques, usa la accion de cargar/agregar tanque y no escribas todo en una observacion libre.\n"
            "7. No dejes tanques duplicados; un duplicado distorsiona el total de deducciones.\n"
            "8. Si un tanque no aplica, dejalo en cero o vacio segun regla del formulario; no inventes datos.\n"
            "9. Revisa total de ballast y consumibles contra datos del chief officer o sounding record.\n"
            "10. Abre Excel/previsualiza y confirma que los totales de tanques alimentan el calculo final.\n"
            "11. Corrige cualquier diferencia antes de enviar a revision."
        ),
    },
    {
        "category": "Informes - Draft Survey",
        "question": "Manual Draft Survey: Como validar resultado final antes de enviar?",
        "answer": (
            "La validacion final evita aprobar un Draft con formulas o datos inconsistentes.\n"
            "Paso a paso:\n"
            "1. Confirma que el tipo de survey sea Initial, Final o Intermediate segun el servicio.\n"
            "2. Revisa drafts promedio, trim, list, density correction y displacement corregido.\n"
            "3. Revisa deducciones: ballast, fresh water, fuel, diesel, lube oil y otros pesos.\n"
            "4. Revisa constant o lightship si aplica.\n"
            "5. Valida net displacement/cargo quantity contra esperado operativo.\n"
            "6. Si existe Initial y Final, compara diferencia y confirma cargo cargado/descargado.\n"
            "7. Usa abrir Excel o previsualizar para revisar formulas y formato.\n"
            "8. Confirma que las observaciones expliquen cualquier diferencia material.\n"
            "9. Envia a Revision solo cuando datos, formulas y narrativa coincidan.\n"
            "10. En Review, usa Editar para habilitar campos y Guardar Cambios para PUT."
        ),
    },
    {
        "category": "Informes - Bunker",
        "question": "Manual Bunker Survey: Como llenar tanques, engine log y consumos?",
        "answer": (
            "Bunker Survey documenta combustible a bordo y condiciones on/off hire.\n"
            "Paso a paso:\n"
            "1. Selecciona Reporte para cargar el servicio.\n"
            "2. Completa tipo: ON_HIRE, OFF_HIRE, SPOT o la categoria que aplique.\n"
            "3. Completa FWD, AFT, TRIM y LIST.\n"
            "4. En Fuel Oil Tanks, ingresa Tank Name, Dist, Gauge, Volume, Temp C, Temp F, Density@15C y Weight MT.\n"
            "5. En Diesel/MGO Tanks, llena los mismos campos cuando aplique.\n"
            "6. Si Dist o Gauge debe decir GAUGE/GAUGES, guardalo como texto permitido; no lo conviertas a numero.\n"
            "7. Agrega o elimina tanques con Add Tank/Remove Last segun cantidad real.\n"
            "8. En Engine Log Book Figures Declaration, registra eventos, fecha, hora y cantidades VLSFO/HFSO/MDO/LSMGO.\n"
            "9. En Consumption MT/Day, completa consumo declarado por condicion: at sea loaded, ballast, at port, shore gear in use.\n"
            "10. Revisa delivery point, charterers, master, surveyor y observaciones.\n"
            "11. Visualiza antes de enviar a revision."
        ),
    },
    {
        "category": "Informes - Bullets",
        "question": "Manual Informes: Como usar secciones con bullets y PORTIA?",
        "answer": (
            "Algunos informes usan bullets dinamicos para observaciones tecnicas.\n"
            "Paso a paso:\n"
            "1. Ubica secciones con boton + Add bullet o equivalente.\n"
            "2. Agrega un bullet por idea, hallazgo o recomendacion.\n"
            "3. Respeta el maximo de bullets por seccion; algunos formularios permiten 10, otros 20.\n"
            "4. En Crane Inspection, usa bullets por grua, recomendaciones, grabs condition y conclusion.\n"
            "5. En Vessel Condition, usa bullets para condicion, hallazgos, recomendaciones y conclusion.\n"
            "6. No pegues parrafos enormes en un solo bullet si son hallazgos separados.\n"
            "7. Usa PORTIA para mejorar solo bullets seleccionados cuando el popup lo permita.\n"
            "8. Revisa comparacion antes de aplicar texto mejorado.\n"
            "9. No permitas que PORTIA cambie numeros, fechas, nombres de buque, cliente, puerto o evidencias."
        ),
    },
    {
        "category": "Informes - Certificados",
        "question": "Manual Certificados: Como escoger y llenar certificados desde Informes?",
        "answer": (
            "Certificados es la tercera familia de Generar Informe.\n"
            "Paso a paso:\n"
            "1. Entra a Informes > Generar Informe > Certificados.\n"
            "2. Selecciona Weight Certificate, Vessel Holds Inspection, Sampling Certificate, Sealing Certificate o Lashing Certificate.\n"
            "3. Usa el selector de num_informe/servicio para cargar datos base.\n"
            "4. Verifica cliente, buque/contenedor, puerto, pais, fecha y operacion.\n"
            "5. Completa los campos especificos del certificado.\n"
            "6. En Weight Certificate, revisa peso, unidad, producto y referencia documental.\n"
            "7. En Holds Inspection, registra bodegas inspeccionadas, condicion y aptitud.\n"
            "8. En Sampling Certificate, registra metodo, cantidad y ubicacion de muestras.\n"
            "9. En Sealing Certificate, registra sellos, unidades, bodegas o contenedores.\n"
            "10. En Lashing Certificate, registra carga, tipo de lashing, condicion y observaciones.\n"
            "11. Envia a revision y genera certificado final solo al aprobar."
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

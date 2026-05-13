export type TableAction = {
  key: "view" | "edit" | "add" | "delete" | "generate";
  label: string;
  method?: "GET" | "POST" | "PUT" | "DELETE";
  endpoint?: string;
};

export type TableConfig = {
  idField: string;
  columns: string[];
  detailEndpoint?: string;
  createEndpoint?: string;
  updateEndpoint?: string;
  deleteEndpoint?: string;
  actions: TableAction[];
  filters?: string[];
};

export type AppSection = {
  key: string;
  label: string;
  endpoint?: string;
  method?: "GET" | "POST" | "PUT";
  table?: TableConfig;
};

export type AppModule = {
  code: string;
  label: string;
  sections: AppSection[];
};

const clientColumns = [
  "codigo",
  "nombrejuridico",
  "nombrecomercial",
  "pais",
  "correo",
  "telefono",
  "cedulajuridicavat",
  "actividad_economica",
  "comentarios",
  "provincia",
  "canton",
  "distrito",
  "direccionexacta",
  "fecha_pago",
  "prefijo",
  "contacto_principal",
  "contacto_secundario"
];

const supplierColumns = [
  "Codigo",
  "Nombre",
  "Apellidos",
  "NombreComercial",
  "Cedula",
  "Pais",
  "Provincia",
  "Canton",
  "Distrito",
  "DireccionExacta",
  "Prefijo",
  "Telefono",
  "Correo",
  "TerminosPago",
  "Banco",
  "CuentaIBAN",
  "SwiftCode",
  "UID",
  "DireccionBanco",
  "TipoProveeduria",
  "Comentarios"
];

const employeeColumns = [
  "codigo",
  "nombre",
  "apellidos",
  "estado_civil",
  "genero",
  "nacionalidad",
  "prefijo",
  "telefono",
  "provincia",
  "canton",
  "distrito",
  "direccion",
  "jornada",
  "salario",
  "pago",
  "banco",
  "cuenta_iban",
  "moneda",
  "enfermedades",
  "contacto_emergencia",
  "telefono_emergencia",
  "activo1",
  "marca1",
  "serial1",
  "activo2",
  "marca2",
  "serial2",
  "activo3",
  "marca3",
  "serial3",
  "fecharegistro"
];

const surveyorColumns = [
  "codigo",
  "nombre",
  "apellidos",
  "estado_civil",
  "genero",
  "nacionalidad",
  "prefijo",
  "telefono",
  "provincia",
  "canton",
  "distrito",
  "direccion",
  "jornada",
  "operacion",
  "honorario",
  "pago",
  "banco",
  "cuenta_iban",
  "moneda",
  "swift",
  "uid",
  "enfermedades",
  "contacto_emergencia",
  "telefono_emergencia",
  "puerto"
];

const serviceColumns = [
  "consec",
  "tipo",
  "estado",
  "num_informe",
  "buque_contenedor",
  "cliente",
  "contacto",
  "detalle",
  "continente",
  "pais",
  "puerto",
  "operacion",
  "surveyor",
  "honorarios",
  "costo_operativo",
  "fecha_inicio",
  "hora_inicio",
  "fecha_fin",
  "hora_fin",
  "demoras",
  "duracion",
  "factura",
  "valor_factura",
  "fecha_factura",
  "terminos_pago",
  "fecha_vencimiento",
  "dias_vencido",
  "razon_cancelacion",
  "comentario_cancelacion"
];

const billingColumns = [
  "id",
  "tipo_factura",
  "tipo_documento",
  "numero_documento",
  "nombre_cliente",
  "fecha_emision",
  "moneda",
  "total",
  "estado"
];

const invoicingColumns = [
  "consec",
  "tipo",
  "buque_contenedor",
  "num_informe",
  "detalle",
  "cliente",
  "continente",
  "pais",
  "puerto",
  "operacion",
  "fecha_inicio",
  "hora_inicio",
  "fecha_fin",
  "hora_fin",
  "demoras",
  "duracion",
  "factura"
];

const collectionsColumns = [
  "codigo_cliente",
  "nombre_cliente",
  "tipo_factura",
  "tipo_documento",
  "numero_documento",
  "fecha_emision",
  "dias_credito",
  "fecha_vencimiento",
  "aging_dias",
  "bucket_aging",
  "moneda",
  "total",
  "saldo_pendiente",
  "num_informe",
  "buque_contenedor",
  "operacion",
  "periodo_operacion",
  "estado_factura",
  "disputada"
];

const bankReconciliationColumns = [
  "banco",
  "fecha_pago",
  "nombre_cliente",
  "numero_documento",
  "referencia",
  "tipo_aplicacion",
  "monto_pagado",
  "monto_aplicado",
  "saldo",
  "estado"
];

const invoiceToPayColumns = [
  "id",
  "payee_name",
  "obligation_type",
  "referencia",
  "vessel",
  "country",
  "operation",
  "currency",
  "total",
  "balance",
  "status",
  "last_payment_date",
  "issue_date",
  "due_date",
  "origin"
];

const accountingLedgerColumns = ["entry_date", "entry_id", "account", "line_description", "debit", "credit", "period", "origin"];

const closingStatusColumns = [
  "company_code",
  "fiscal_year",
  "period",
  "ledger",
  "period_closed",
  "gl_closed",
  "tb_closed",
  "pnl_closed",
  "fs_closed",
  "fy_opened",
  "last_batch_id",
  "updated_at"
];

const disputeColumns = [
  "management_id",
  "status",
  "disputed_amount",
  "dispute_closed_at",
  "dispute_id",
  "dispute_case",
  "numero_documento",
  "codigo_cliente",
  "nombre_cliente",
  "fecha_factura",
  "fecha_vencimiento",
  "monto",
  "motivo",
  "comentario",
  "buque_contenedor",
  "operacion",
  "periodo_operacion",
  "ultimo_comentario"
];

const masterActions: TableAction[] = [
  { key: "view", label: "Ver" },
  { key: "add", label: "Agregar" },
  { key: "edit", label: "Editar" },
  { key: "delete", label: "Eliminar" }
];

const readOnlyActions: TableAction[] = [{ key: "view", label: "Ver" }];

export const ERP_MODULES: AppModule[] = [
  {
    code: "dashboard",
    label: "Dashboard",
    sections: [
      { key: "dashboard-servicios", label: "Servicios", endpoint: "/dashboard/servicios" },
      { key: "dashboard-finanzas", label: "Finanzas", endpoint: "/dashboard-finanzas/resumen" },
      { key: "dashboard-comercial", label: "Comercial", endpoint: "/dashboard-comercial/resumen" },
      { key: "dashboard-informes", label: "Informes", endpoint: "/dashboard-informes/resumen" }
    ]
  },
  {
    code: "master_data",
    label: "Master Data",
    sections: [
      {
        key: "clientes",
        label: "Clientes",
        endpoint: "/clientes?page=1&page_size=100",
        table: {
          idField: "codigo",
          columns: clientColumns,
          detailEndpoint: "/clientes/{id}",
          createEndpoint: "/clientes/add",
          updateEndpoint: "/clientes/update",
          deleteEndpoint: "/clientes/{id}",
          actions: masterActions,
          filters: ["codigo", "nombrecomercial", "pais", "correo"]
        }
      },
      {
        key: "proveedores",
        label: "Proveedores",
        endpoint: "/proveedores/?page=1&page_size=100",
        table: {
          idField: "Codigo",
          columns: supplierColumns,
          detailEndpoint: "/proveedores/{id}",
          createEndpoint: "/proveedores/add",
          updateEndpoint: "/proveedores/update",
          deleteEndpoint: "/proveedores/{id}",
          actions: masterActions,
          filters: ["Codigo", "NombreComercial", "Pais", "Correo"]
        }
      },
      {
        key: "empleados",
        label: "Empleados",
        endpoint: "/empleados/?page=1&page_size=100",
        table: {
          idField: "codigo",
          columns: employeeColumns,
          detailEndpoint: "/empleados/{id}",
          createEndpoint: "/empleados/add",
          updateEndpoint: "/empleados/update",
          deleteEndpoint: "/empleados/{id}",
          actions: masterActions,
          filters: ["codigo", "nombre", "apellidos", "telefono"]
        }
      },
      {
        key: "surveyores",
        label: "Surveyores",
        endpoint: "/surveyores/?page=1&page_size=100",
        table: {
          idField: "codigo",
          columns: surveyorColumns,
          detailEndpoint: "/surveyores/{id}",
          createEndpoint: "/surveyores/add",
          updateEndpoint: "/surveyores/update",
          deleteEndpoint: "/surveyores/{id}",
          actions: masterActions,
          filters: ["codigo", "nombre", "apellidos", "puerto"]
        }
      },
      {
        key: "servicios-md",
        label: "Servicios MD",
        endpoint: "/servicios_md/?page=1&page_size=100",
        table: {
          idField: "codigo",
          columns: ["codigo", "codigo_prod", "nombre", "costo"],
          detailEndpoint: "/servicios_md/{id}",
          createEndpoint: "/servicios_md/add",
          updateEndpoint: "/servicios_md/update",
          deleteEndpoint: "/servicios_md/{id}",
          actions: masterActions,
          filters: ["codigo", "codigo_prod", "nombre"]
        }
      },
      { key: "puertos", label: "Continentes / Paises / Puertos", endpoint: "/cpp/puertos_all" }
    ]
  },
  {
    code: "servicios",
    label: "Servicios",
    sections: [
      {
        key: "tabla-servicios",
        label: "Tabla de servicios",
        endpoint: "/servicios/?page=1&page_size=50",
        table: {
          idField: "consec",
          columns: serviceColumns,
          detailEndpoint: "/servicios/{id}",
          createEndpoint: "/servicios/add",
          updateEndpoint: "/servicios/editar/{id}",
          deleteEndpoint: "/servicios/{id}",
          actions: [
            { key: "view", label: "Ver" },
            { key: "add", label: "Agregar Servicio" },
            { key: "edit", label: "Editar" },
            { key: "generate", label: "Generar Consecutivo", method: "PUT", endpoint: "/servicios/confirmar/{id}" },
            { key: "generate", label: "Finalizar", method: "PUT", endpoint: "/servicios/generar_informe/{id}" },
            { key: "generate", label: "Cancelar", method: "PUT", endpoint: "/servicios/cancelar/{id}" },
            { key: "generate", label: "Demoras", method: "PUT", endpoint: "/servicios/demoras/{id}" },
            { key: "delete", label: "Eliminar" }
          ],
          filters: ["consec", "estado", "surveyor", "cliente", "year"]
        }
      },
      { key: "surveyors-servicio", label: "Surveyors por servicio", endpoint: "/servicios-surveyors/catalogo/lista" },
      { key: "servicios-filtros", label: "Filtros", endpoint: "/servicios/_meta/filtros" },
      { key: "servicios-ultimo", label: "Ultimo consecutivo", endpoint: "/servicios_md/ultimo" }
    ]
  },
  {
    code: "finanzas",
    label: "Finanzas",
    sections: [
      {
        key: "billing",
        label: "Billing",
        endpoint: "/invoicing/facturables?cliente=__seleccione_cliente__",
        table: {
          idField: "consec",
          columns: invoicingColumns,
          actions: [
            { key: "view", label: "Ver" },
            { key: "generate", label: "Factura Manual" },
            { key: "generate", label: "Factura XML" },
            { key: "generate", label: "Ver Factura" },
            { key: "generate", label: "Facturacion Anticipada" },
            { key: "generate", label: "Nota Credito" }
          ],
          filters: ["consec", "cliente", "num_informe", "buque_contenedor", "operacion"]
        }
      },
      {
        key: "invoicing",
        label: "Invoicing",
        endpoint: "/billing/search?page=1&page_size=50",
        table: {
          idField: "numero_documento",
          columns: billingColumns,
          detailEndpoint: "/billing/{id}",
          actions: readOnlyActions,
          filters: ["numero_documento", "nombre_cliente", "estado", "tipo_documento"]
        }
      },
      {
        key: "collections",
        label: "Collections",
        endpoint: "/collections/search?page=1&page_size=50",
        table: {
          idField: "numero_documento",
          columns: collectionsColumns,
          actions: [
            { key: "view", label: "Ver" },
            { key: "generate", label: "Post Accounting", method: "POST", endpoint: "/collections/post-to-accounting" }
          ],
          filters: ["numero_documento", "nombre_cliente", "bucket_aging", "estado_factura"]
        }
      },
      {
        key: "bank-reconciliation",
        label: "Bank Reconciliation",
        endpoint: "/bank-reconciliation?ver_todos=true&page=1&page_size=50",
        table: {
          idField: "id",
          columns: bankReconciliationColumns,
          actions: readOnlyActions,
          filters: ["numero_documento", "nombre_cliente", "referencia", "estado"]
        }
      },
      {
        key: "invoice-to-pay",
        label: "Invoice To Pay",
        endpoint: "/invoice-to-pay/search?status=ALL",
        table: {
          idField: "id",
          columns: invoiceToPayColumns,
          deleteEndpoint: "/invoice-to-pay/{id}",
          actions: [
            { key: "view", label: "Ver" },
            { key: "delete", label: "Eliminar" }
          ],
          filters: ["payee_name", "obligation_type", "referencia", "status", "origin"]
        }
      },
      {
        key: "accounting",
        label: "Accounting",
        endpoint: "/accounting/ledger",
        table: {
          idField: "entry_id",
          columns: accountingLedgerColumns,
          actions: [
            { key: "view", label: "Ver" },
            { key: "generate", label: "Reversar asiento", method: "POST", endpoint: "/accounting/reverse/{id}" }
          ],
          filters: ["entry_id", "account", "line_description", "period", "origin"]
        }
      },
      {
        key: "disputes",
        label: "Disputes",
        endpoint: "/dispute-management?page=1&page_size=50",
        table: {
          idField: "management_id",
          columns: disputeColumns,
          detailEndpoint: "/dispute-management/{id}/history",
          actions: readOnlyActions,
          filters: ["management_id", "status", "numero_documento", "nombre_cliente", "motivo"]
        }
      },
      {
        key: "credit-hold",
        label: "Credit Hold",
        endpoint: "/clientes?page=1&page_size=100",
        table: {
          idField: "codigo",
          columns: ["codigo", "nombrecomercial", "nombrejuridico", "pais", "correo", "telefono"],
          detailEndpoint: "/cliente-credito/{id}",
          actions: readOnlyActions,
          filters: ["codigo", "nombrecomercial", "nombrejuridico"]
        }
      }
    ]
  },
  {
    code: "hhrre",
    label: "HHRR",
    sections: [
      { key: "empleados-hr", label: "Empleados", endpoint: "/hr/employees" },
      { key: "solicitudes", label: "Solicitudes", endpoint: "/hr/events" },
      { key: "registro-horas", label: "Registro de horas", endpoint: "/hr/ot-log" },
      { key: "payroll", label: "Payroll", endpoint: "/hr/payroll/employees" },
      { key: "colillas", label: "Colillas", endpoint: "/hr/payroll/payslips" },
      { key: "politicas", label: "Politicas", endpoint: "/hr/policies" },
      { key: "noticias", label: "Noticias", endpoint: "/noticias/latest" }
    ]
  },
  {
    code: "comercial",
    label: "Comercial",
    sections: [
      { key: "board", label: "Board", endpoint: "/comercial/board" },
      { key: "clientes-comercial", label: "Clientes", endpoint: "/comercial/clientes" },
      { key: "precios", label: "Precios", endpoint: "/comercial/precios" },
      { key: "cotizaciones", label: "Cotizaciones", endpoint: "/comercial/cotizaciones" },
      { key: "analytics-clientes", label: "Analytics clientes", endpoint: "/comercial/client-view" },
      { key: "analytics-puertos", label: "Analytics puertos", endpoint: "/comercial/analytics/puertos/kpis" },
      { key: "analytics-servicios", label: "Analytics servicios", endpoint: "/comercial/analytics/servicios/kpis" }
    ]
  },
  {
    code: "informes",
    label: "Informes",
    sections: [
      { key: "status-informes", label: "Status informes", endpoint: "/status-informes" },
      { key: "container", label: "Container report", endpoint: "/container-reports/list" },
      { key: "grain-sampling", label: "Vessel grain sampling", endpoint: "/vessel-grain-sampling/" },
      { key: "truck-supervision", label: "Truck supervision", endpoint: "/vessel-truck-supervision/" },
      { key: "draft-survey", label: "Draft survey", endpoint: "/draft-survey/" },
      { key: "bunker", label: "Vessel bunker", endpoint: "/vessel-bunker-reports/" },
      { key: "cargo-condition", label: "Cargo condition", endpoint: "/vessel-cargo-condition-surveys/" },
      { key: "crane-inspection", label: "Crane inspection", endpoint: "/vessel-crane-inspection/" },
      { key: "vessel-condition", label: "Vessel condition", endpoint: "/vessel-condition-surveys" },
      { key: "port-captancy", label: "Port captancy", endpoint: "/port-captancy-reports" },
      { key: "weight-certificate", label: "Weight certificate", endpoint: "/weight-certificates" },
      { key: "holds-certificate", label: "Holds inspection certificate", endpoint: "/vessel-holds-inspection-certificates" },
      { key: "sampling-certificate", label: "Sampling certificate", endpoint: "/sampling-certificates" },
      { key: "sealing-certificate", label: "Sealing certificate", endpoint: "/sealing-certificates" },
      { key: "lashing-certificate", label: "Lashing certificate", endpoint: "/lashing-certificates" }
    ]
  }
];

export function getAllowedModules(allowedCodes: string[]) {
  const allowed = new Set(allowedCodes);
  return ERP_MODULES.filter((module) => allowed.has(module.code));
}

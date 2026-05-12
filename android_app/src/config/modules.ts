export type AppSection = {
  key: string;
  label: string;
  endpoint?: string;
  method?: "GET" | "POST" | "PUT";
};

export type AppModule = {
  code: string;
  label: string;
  sections: AppSection[];
};

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
      { key: "clientes", label: "Clientes", endpoint: "/clientes?page=1&page_size=100" },
      { key: "proveedores", label: "Proveedores", endpoint: "/proveedores?page=1&page_size=100" },
      { key: "empleados", label: "Empleados", endpoint: "/empleados?page=1&page_size=100" },
      { key: "surveyores", label: "Surveyores", endpoint: "/surveyores?page=1&page_size=100" },
      { key: "servicios-md", label: "Servicios MD", endpoint: "/servicios_md?page=1&page_size=100" },
      { key: "puertos", label: "Continentes / Paises / Puertos", endpoint: "/cpp/puertos_all" }
    ]
  },
  {
    code: "servicios",
    label: "Servicios",
    sections: [
      { key: "tabla-servicios", label: "Tabla de servicios", endpoint: "/servicios/?page=1&page_size=50" },
      { key: "surveyors-servicio", label: "Surveyors por servicio", endpoint: "/servicios-surveyors/catalogo/lista" },
      { key: "servicios-filtros", label: "Filtros", endpoint: "/servicios/_meta/filtros" },
      { key: "servicios-ultimo", label: "Ultimo consecutivo", endpoint: "/servicios_md/ultimo" }
    ]
  },
  {
    code: "finanzas",
    label: "Finanzas",
    sections: [
      { key: "billing", label: "Billing", endpoint: "/billing/search?page=1&page_size=50" },
      { key: "invoicing", label: "Invoicing", endpoint: "/invoicing/facturables" },
      { key: "collections", label: "Collections", endpoint: "/collections/search?page=1&page_size=50" },
      { key: "bank-reconciliation", label: "Bank Reconciliation", endpoint: "/bank-reconciliation?page=1&page_size=50" },
      { key: "invoice-to-pay", label: "Invoice To Pay", endpoint: "/invoice-to-pay/kpis" },
      { key: "accounting", label: "Accounting", endpoint: "/accounting/accounts" },
      { key: "closing", label: "Closing", endpoint: "/closing/period/status" },
      { key: "disputes", label: "Disputes", endpoint: "/dispute-management?page=1&page_size=50" },
      { key: "credit-hold", label: "Credit Hold" }
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

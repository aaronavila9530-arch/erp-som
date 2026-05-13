import * as LocalAuthentication from "expo-local-authentication";
import * as SecureStore from "expo-secure-store";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Linking,
  Modal,
  Pressable,
  SafeAreaView,
  ScrollView,
  Share,
  StatusBar,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View
} from "react-native";

import { API_BASE_URL, apiRequest, confirmTotp, login, LoginResponse, verifyTotp } from "./src/api/client";
import { AuthProvider, useAuth } from "./src/auth/AuthContext";
import { AppModule, AppSection, TableAction, getAllowedModules } from "./src/config/modules";

const BLUE = "#003A75";
const BORDER = "#D7DEE8";
const CREDS_KEY = "erp_som_saved_credentials";

type SavedCredentials = {
  usuario: string;
  password: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function extractRows(payload: unknown): Record<string, unknown>[] {
  if (Array.isArray(payload)) return payload.filter((item) => asRecord(item)) as Record<string, unknown>[];
  const obj = asRecord(payload);
  if (!obj) return [];

  for (const key of ["data", "items", "rows", "results", "records", "facturas", "servicios", "reportes"]) {
    const value = obj[key];
    if (Array.isArray(value)) return value.filter((item) => asRecord(item)) as Record<string, unknown>[];
  }

  return [];
}

function flattenAccountingLedger(payload: unknown): Record<string, unknown>[] {
  return extractRows(payload).flatMap((entry) => {
    const lines = Array.isArray(entry.lines) ? entry.lines : [];
    if (!lines.length) return [entry];

    return lines
      .map((line) => asRecord(line))
      .filter(Boolean)
      .map((line) => ({
        entry_date: entry.entry_date,
        entry_id: entry.entry_id,
        period: entry.period,
        origin: entry.origin,
        origin_id: entry.origin_id,
        entry_description: entry.description,
        line_id: line?.line_id,
        account_code: line?.account_code,
        account_name: line?.account_name,
        account: `${formatValue(line?.account_code)} ${formatValue(line?.account_name)}`.trim(),
        line_description: line?.line_description,
        debit: line?.debit,
        credit: line?.credit
      }));
  });
}

function rowsForSection(sectionKey: string | undefined, payload: unknown) {
  if (sectionKey === "accounting") return flattenAccountingLedger(payload);
  return extractRows(payload);
}

function flattenNumbers(value: unknown, prefix = ""): Array<{ label: string; value: number }> {
  if (typeof value === "number" && Number.isFinite(value)) {
    return [{ label: prefix || "Valor", value }];
  }

  if (Array.isArray(value)) return [];

  const obj = asRecord(value);
  if (!obj) return [];

  return Object.entries(obj).flatMap(([key, item]) => {
    const label = prefix ? `${prefix} ${key}` : key;
    if (typeof item === "number" && Number.isFinite(item)) return [{ label, value: item }];
    if (asRecord(item)) return flattenNumbers(item, label);
    return [];
  });
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : value.toFixed(2);
  if (typeof value === "boolean") return value ? "Sí" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function LoginScreen() {
  const { setSession } = useAuth();
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(true);
  const [hasSavedCredentials, setHasSavedCredentials] = useState(false);
  const [pending, setPending] = useState<LoginResponse | null>(null);
  const [codigo, setCodigo] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    SecureStore.getItemAsync(CREDS_KEY).then((value) => setHasSavedCredentials(Boolean(value)));
  }, []);

  async function saveCredentials() {
    if (!remember) return;
    await SecureStore.setItemAsync(CREDS_KEY, JSON.stringify({ usuario, password }), {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY
    });
    setHasSavedCredentials(true);
  }

  async function submitLogin() {
    setLoading(true);
    setError("");
    try {
      const response = await login(usuario.trim(), password);
      await saveCredentials();
      setPending(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  async function unlockSavedCredentials() {
    setLoading(true);
    setError("");
    try {
      const available = await LocalAuthentication.hasHardwareAsync();
      const enrolled = await LocalAuthentication.isEnrolledAsync();

      if (!available || !enrolled) {
        throw new Error("El teléfono no tiene biometría configurada");
      }

      const auth = await LocalAuthentication.authenticateAsync({
        promptMessage: "Ingresar a ERP SOM",
        cancelLabel: "Cancelar",
        fallbackLabel: "Usar PIN"
      });

      if (!auth.success) return;

      const raw = await SecureStore.getItemAsync(CREDS_KEY);
      if (!raw) throw new Error("No hay credenciales guardadas");

      const saved = JSON.parse(raw) as SavedCredentials;
      setUsuario(saved.usuario);
      setPassword(saved.password);

      const response = await login(saved.usuario, saved.password);
      setPending(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo usar biometría");
    } finally {
      setLoading(false);
    }
  }

  async function submitTotp() {
    if (!pending) return;
    setLoading(true);
    setError("");
    try {
      const response =
        pending.action === "ENROLL_TOTP"
          ? await confirmTotp(pending.usuario, codigo)
          : await verifyTotp(pending.usuario, codigo);
      await setSession(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Código inválido");
    } finally {
      setLoading(false);
    }
  }

  return (
    <SafeAreaView style={styles.screen}>
      <StatusBar barStyle="light-content" backgroundColor={BLUE} />
      <ScrollView contentContainerStyle={styles.loginWrap} keyboardShouldPersistTaps="handled">
        <Image source={require("./assets/icon.png")} resizeMode="contain" style={styles.loginLogo} />
        <Text style={styles.brand}>ERP SOM</Text>
        <Text style={styles.title}>Ingreso de usuario</Text>

        {!pending ? (
          <View style={styles.panel}>
            <Text style={styles.label}>Usuario</Text>
            <TextInput
              autoCapitalize="none"
              autoCorrect={false}
              textContentType="username"
              style={styles.input}
              value={usuario}
              onChangeText={setUsuario}
              placeholder="usuario"
            />

            <Text style={styles.label}>Contraseña</Text>
            <TextInput
              autoCapitalize="none"
              autoCorrect={false}
              secureTextEntry
              textContentType="password"
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="contraseña"
            />

            <View style={styles.rememberRow}>
              <Text style={styles.rememberText}>Guardar en este teléfono</Text>
              <Switch value={remember} onValueChange={setRemember} trackColor={{ true: BLUE }} />
            </View>

            <PrimaryButton label="Ingresar" loading={loading} onPress={submitLogin} />

            {hasSavedCredentials ? (
              <Pressable style={styles.secondaryButton} onPress={unlockSavedCredentials} disabled={loading}>
                <Text style={styles.secondaryButtonText}>Ingresar con huella o rostro</Text>
              </Pressable>
            ) : null}
          </View>
        ) : (
          <View style={styles.panel}>
            <Text style={styles.subtitle}>
              {pending.action === "ENROLL_TOTP" ? "Registrar Authenticator" : "Verificar Authenticator"}
            </Text>
            {pending.action === "ENROLL_TOTP" ? (
              <Image
                style={styles.qr}
                source={{ uri: `data:image/png;base64,${pending.qr_base64}` }}
                resizeMode="contain"
              />
            ) : null}

            <Text style={styles.label}>Código</Text>
            <TextInput
              keyboardType="number-pad"
              style={styles.input}
              value={codigo}
              onChangeText={setCodigo}
              placeholder="000000"
            />

            <PrimaryButton label="Continuar" loading={loading} onPress={submitTotp} />
          </View>
        )}

        {error ? <Text style={styles.error}>{error}</Text> : null}
      </ScrollView>
    </SafeAreaView>
  );
}

function Shell() {
  const { session, logout } = useAuth();
  const [activeModule, setActiveModule] = useState<AppModule | null>(null);
  const [activeSection, setActiveSection] = useState<AppSection | null>(null);
  const [payload, setPayload] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const modules = useMemo(
    () => getAllowedModules(session?.modules.map((module) => module.code) ?? []),
    [session?.modules]
  );

  useEffect(() => {
    if (!activeModule && modules.length > 0) setActiveModule(modules[0]);
  }, [activeModule, modules]);

  async function openSection(section: AppSection) {
    setActiveSection(section);
    setPayload(null);
    setError("");

    if (!section.endpoint || !session) return;

    if (section.key === "accounting") {
      setPayload({ data: [] });
      return;
    }

    setLoading(true);
    try {
      const data = await apiRequest(section.endpoint, { session });
      setPayload(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la sección");
    } finally {
      setLoading(false);
    }
  }

  if (!session) return null;

  return (
    <SafeAreaView style={styles.app}>
      <StatusBar barStyle="light-content" backgroundColor={BLUE} />
      <View style={styles.top}>
        <View style={styles.topRow}>
          <View>
            <Text style={styles.headerTitle}>ERP SOM</Text>
            <Text style={styles.headerSub}>
              {session.usuario} · {session.rol}
            </Text>
          </View>
          <Pressable style={styles.headerButton} onPress={logout}>
            <Text style={styles.headerButtonText}>Salir</Text>
          </Pressable>
        </View>

        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.moduleTabs}>
          {modules.map((module) => (
            <Pressable
              key={module.code}
              style={[styles.moduleTab, activeModule?.code === module.code && styles.moduleTabActive]}
              onPress={() => {
                setActiveModule(module);
                setActiveSection(null);
                setPayload(null);
                setError("");
              }}
            >
              <Text style={[styles.moduleTabText, activeModule?.code === module.code && styles.moduleTabTextActive]}>
                {module.label}
              </Text>
            </Pressable>
          ))}
        </ScrollView>
      </View>

      <ScrollView style={styles.content} contentContainerStyle={styles.contentInner}>
        {!activeModule ? (
          <Text style={styles.empty}>Seleccione un módulo</Text>
        ) : (
          <>
            <Text style={styles.moduleTitle}>{activeModule.label}</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.sectionTabs}>
              {activeModule.sections.map((section) => (
                <Pressable
                  key={section.key}
                  style={[styles.sectionTab, activeSection?.key === section.key && styles.sectionTabActive]}
                  onPress={() => openSection(section)}
                >
                  <Text style={[styles.sectionText, activeSection?.key === section.key && styles.sectionTextActive]}>
                    {section.label}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>

            {loading ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
            {error ? <Text style={styles.error}>{error}</Text> : null}
            {activeSection && !activeSection.endpoint ? (
              <Text style={styles.empty}>Esta sección requiere seleccionar un registro o completar filtros.</Text>
            ) : null}
            {payload ? (
              <DataView
                moduleCode={activeModule.code}
                section={activeSection}
                payload={payload}
                session={session}
                onReload={() => activeSection && openSection(activeSection)}
              />
            ) : null}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function DataView({
  moduleCode,
  section,
  payload,
  session,
  onReload
}: {
  moduleCode: string;
  section: AppSection | null;
  payload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onReload: () => void;
}) {
  const rows = rowsForSection(section?.key, payload);
  const numbers = flattenNumbers(payload).slice(0, 8);

  if (moduleCode === "dashboard") {
    return <DashboardView section={section} payload={payload} session={session} />;
  }

  if (section?.table) {
    return <DesktopTable section={section} rows={rows} session={session} onReload={onReload} />;
  }

  if (rows.length > 0) return <ListView rows={rows} />;

  if (numbers.length > 0) return <KpiGrid numbers={numbers} />;

  const obj = asRecord(payload);
  if (obj) return <ObjectCards obj={obj} />;

  return <Text style={styles.empty}>{formatValue(payload)}</Text>;
}

function DashboardView({
  section,
  payload,
  session
}: {
  section: AppSection | null;
  payload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [data, setData] = useState(payload);
  const [filterData, setFilterData] = useState<Record<string, unknown> | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const config = dashboardConfig(section?.key || "");
  const obj = asRecord(data) || {};

  useEffect(() => {
    setData(payload);
    setFilters({});
    setMessage("");
  }, [payload, section?.key]);

  useEffect(() => {
    if (!section || !config.filterEndpoint) return;
    apiRequest(config.filterEndpoint, { session })
      .then((nextFilters) => setFilterData(asRecord(nextFilters)))
      .catch(() => setFilterData(null));
  }, [config.filterEndpoint, section, session]);

  const filterPayload = asRecord(obj.filtros) || filterData || obj;

  function filterOptions(field: DashboardFilter) {
    const raw = filterPayload[field.sourceKey];
    const rows = Array.isArray(raw) ? raw : [];
    const values = rows
      .map((item) => {
        if (typeof item === "string" || typeof item === "number") return String(item);
        const row = asRecord(item);
        return row ? formatValue(row[field.valueKey]) : "";
      })
      .filter((value) => value && value !== "-");
    return ["Todos", ...Array.from(new Set(values))];
  }

  async function searchDashboard() {
    if (!section?.endpoint) return;
    const params = new URLSearchParams();
    config.filters.forEach((field) => {
      const value = filters[field.key];
      if (value && value !== "Todos") params.set(field.param, value);
    });

    const endpoint = `${section.endpoint}${params.toString() ? `?${params.toString()}` : ""}`;
    setLoading(true);
    setMessage("");
    try {
      const nextData = await apiRequest(endpoint, { session });
      setData(nextData);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar el dashboard.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View>
      <View style={styles.dashboardHeader}>
        <Text style={styles.dashboardTitle}>{config.title}</Text>
        <PrimaryButton label="Buscar" loading={loading} onPress={searchDashboard} />
      </View>

      <View style={styles.dashboardFilters}>
        {config.filters.map((field) => (
          <SelectField
            key={field.key}
            label={field.label}
            value={filters[field.key] || selectedFilterValue(filterPayload, field)}
            options={filterOptions(field)}
            onChange={(value) => setFilters((current) => ({ ...current, [field.key]: value }))}
          />
        ))}
      </View>

      <KpiGrid numbers={config.kpis.map((kpi) => ({ label: kpi.label, value: toDashboardNumber(readPath(obj, kpi.path)) }))} />

      {config.charts.map((chart) =>
        chart.type === "pie" ? (
          <PieListChart key={chart.title} title={chart.title} rows={readRows(obj, chart.path)} labelKey={chart.labelKey} valueKey={chart.valueKey} />
        ) : (
          <BarListChart key={chart.title} title={chart.title} rows={readRows(obj, chart.path)} labelKey={chart.labelKey} valueKey={chart.valueKey} />
        )
      )}

      {message ? <Text style={styles.error}>{message}</Text> : null}
    </View>
  );
}

type DashboardFilter = {
  key: string;
  label: string;
  param: string;
  sourceKey: string;
  valueKey: string;
  selectedKey?: string;
};

type DashboardChart = {
  title: string;
  path: string;
  labelKey: string;
  valueKey: string;
  type?: "bar" | "pie";
};

type DashboardConfig = {
  title: string;
  filterEndpoint?: string;
  filters: DashboardFilter[];
  kpis: Array<{ label: string; path: string }>;
  charts: DashboardChart[];
};

function dashboardConfig(key: string): DashboardConfig {
  const baseFilters: DashboardFilter[] = [
    { key: "anio", label: "Anio", param: "anio", sourceKey: "anios", valueKey: "anio", selectedKey: "anio_seleccionado" },
    { key: "pais", label: "Pais", param: "pais", sourceKey: "paises", valueKey: "pais", selectedKey: "pais_seleccionado" },
    { key: "puerto", label: "Puerto", param: "puerto", sourceKey: "puertos", valueKey: "puerto", selectedKey: "puerto_seleccionado" },
    { key: "cliente", label: "Cliente", param: "cliente", sourceKey: "clientes", valueKey: "cliente", selectedKey: "cliente_seleccionado" }
  ];

  if (key === "dashboard-finanzas") {
    return {
      title: "Dashboard - Finanzas",
      filters: [
        { key: "anio", label: "Anio", param: "anio", sourceKey: "anios", valueKey: "anio", selectedKey: "anio_seleccionado" },
        { key: "cliente", label: "Cliente", param: "cliente", sourceKey: "clientes", valueKey: "cliente", selectedKey: "cliente_seleccionado" }
      ],
      kpis: [
        { label: "Revenue", path: "kpis.revenue_total" },
        { label: "Accounts Receivable", path: "kpis.ar_total" },
        { label: "Payments", path: "kpis.payments_total" },
        { label: "Accounts Payable", path: "kpis.ap_total" }
      ],
      charts: [
        { title: "Revenue Monthly", path: "revenue_mensual", labelKey: "mes", valueKey: "revenue" },
        { title: "Accounts Receivable Aging", path: "aging_ar", labelKey: "bucket_aging", valueKey: "total" },
        { title: "Top Clientes con Deuda", path: "top_clientes_deuda", labelKey: "nombre_cliente", valueKey: "deuda" }
      ]
    };
  }

  if (key === "dashboard-comercial") {
    return {
      title: "Dashboard - Comercial",
      filters: [...baseFilters, { key: "operacion", label: "Operacion", param: "operacion", sourceKey: "operaciones", valueKey: "operacion", selectedKey: "operacion_seleccionada" }],
      kpis: [
        { label: "Ticket Promedio", path: "kpis.ticket_promedio" },
        { label: "Revenue", path: "kpis.revenue_total" },
        { label: "Servicios", path: "kpis.total_servicios" },
        { label: "Puertos", path: "kpis.total_puertos" },
        { label: "Margen Neto %", path: "kpis.margen_neto_pct" }
      ],
      charts: [
        { title: "Revenue por Puerto", path: "revenue_por_puerto", labelKey: "puerto", valueKey: "total_revenue" },
        { title: "Servicios por Puerto", path: "servicios_por_puerto", labelKey: "puerto", valueKey: "total_servicios" },
        { title: "Servicios por Operacion", path: "servicios_por_operacion", labelKey: "operacion", valueKey: "total_servicios" },
        { title: "Clientes por Pais", path: "clientes_por_pais", labelKey: "pais", valueKey: "total_clientes" },
        { title: "Revenue por Pais", path: "revenue_por_pais", labelKey: "pais", valueKey: "total_revenue" }
      ]
    };
  }

  if (key === "dashboard-informes") {
    return {
      title: "Dashboard - Informes",
      filterEndpoint: "/dashboard-informes/filtros",
      filters: [
        ...baseFilters,
        { key: "operacion", label: "Operacion", param: "operacion", sourceKey: "operaciones", valueKey: "operacion", selectedKey: "operacion_seleccionada" },
        { key: "tipo_informe", label: "Tipo Informe", param: "tipo_informe", sourceKey: "tipos_informe", valueKey: "tipo_informe", selectedKey: "tipo_informe_seleccionado" }
      ],
      kpis: [
        { label: "Tiempo Promedio (hrs)", path: "kpis.tiempo_promedio_horas" },
        { label: "Total Informes", path: "kpis.total_informes" },
        { label: "Clientes", path: "kpis.clientes_con_informes" },
        { label: "Puertos", path: "kpis.puertos_con_informes" }
      ],
      charts: [
        { title: "Informes por Tipo", path: "informes_por_tipo", labelKey: "tipo", valueKey: "total" },
        { title: "Informes por Pais", path: "informes_por_pais", labelKey: "pais", valueKey: "total" },
        { title: "Informes por Puerto", path: "informes_por_puerto", labelKey: "puerto", valueKey: "total" },
        { title: "Informes por Cliente", path: "informes_por_cliente", labelKey: "cliente", valueKey: "total" },
        { title: "Tiempo Promedio por Operacion", path: "tiempo_por_operacion", labelKey: "operacion", valueKey: "horas_promedio" }
      ]
    };
  }

  return {
    title: "Dashboard - Servicios",
    filters: baseFilters,
    kpis: [
      { label: "Servicios", path: "kpis.total_servicios" },
      { label: "Facturado", path: "kpis.total_facturado" },
      { label: "Profit", path: "kpis.total_profit" },
      { label: "Paises", path: "kpis.total_paises" },
      { label: "Puertos", path: "kpis.total_puertos" },
      { label: "Clientes", path: "kpis.total_clientes" }
    ],
    charts: [
      { title: "Servicios por Pais", path: "servicios_por_pais", labelKey: "pais", valueKey: "total" },
      { title: "Servicios por Operacion (Top 10)", path: "servicios_por_operacion", labelKey: "operacion", valueKey: "total" },
      { title: "Facturacion por Pais", path: "facturacion_por_pais", labelKey: "pais", valueKey: "total_facturado" },
      { title: "Facturacion por Tipo", path: "facturacion_por_tipo", labelKey: "tipo", valueKey: "total_facturado", type: "pie" }
    ]
  };
}

function selectedFilterValue(filters: Record<string, unknown>, field: DashboardFilter) {
  const value = field.selectedKey ? filters[field.selectedKey] : "";
  return value ? formatValue(value) : "Todos";
}

function readPath(obj: Record<string, unknown>, path: string) {
  return path.split(".").reduce<unknown>((current, key) => asRecord(current)?.[key], obj);
}

function readRows(obj: Record<string, unknown>, path: string) {
  const value = readPath(obj, path);
  return Array.isArray(value) ? (value.filter((item) => asRecord(item)) as Record<string, unknown>[]) : [];
}

function toDashboardNumber(value: unknown) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function BarListChart({ title, rows, labelKey, valueKey }: { title: string; rows: Record<string, unknown>[]; labelKey: string; valueKey: string }) {
  const cleanRows = rows.slice(0, 10);
  const max = Math.max(...cleanRows.map((row) => Math.abs(toDashboardNumber(row[valueKey]))), 1);
  return (
    <View style={styles.chart}>
      <Text style={styles.cardTitle}>{title}</Text>
      {cleanRows.length ? (
        cleanRows.map((row, index) => {
          const value = toDashboardNumber(row[valueKey]);
          const label = formatValue(row[labelKey]);
          return (
            <View key={`${title}-${label}-${index}`} style={styles.dashboardBarRow}>
              <View style={styles.dashboardBarTop}>
                <Text style={styles.dashboardBarLabel} numberOfLines={1}>
                  {label}
                </Text>
                <Text style={styles.dashboardBarValue}>{formatValue(value)}</Text>
              </View>
              <View style={styles.barTrack}>
                <View style={[styles.barFill, { width: `${Math.max(4, (Math.abs(value) / max) * 100)}%` }]} />
              </View>
            </View>
          );
        })
      ) : (
        <Text style={styles.empty}>Sin datos</Text>
      )}
    </View>
  );
}

function PieListChart({ title, rows, labelKey, valueKey }: { title: string; rows: Record<string, unknown>[]; labelKey: string; valueKey: string }) {
  const total = rows.reduce((sum, row) => sum + Math.abs(toDashboardNumber(row[valueKey])), 0) || 1;
  return (
    <View style={styles.chart}>
      <Text style={styles.cardTitle}>{title}</Text>
      {rows.length ? (
        rows.map((row, index) => {
          const value = Math.abs(toDashboardNumber(row[valueKey]));
          const pct = (value / total) * 100;
          return (
            <View key={`${title}-${index}`} style={styles.dashboardBarRow}>
              <View style={styles.dashboardBarTop}>
                <Text style={styles.dashboardBarLabel} numberOfLines={1}>
                  {formatValue(row[labelKey])}
                </Text>
                <Text style={styles.dashboardBarValue}>{pct.toFixed(1)}%</Text>
              </View>
              <View style={styles.barTrack}>
                <View style={[styles.barFill, { width: `${Math.max(4, pct)}%` }]} />
              </View>
            </View>
          );
        })
      ) : (
        <Text style={styles.empty}>Sin datos</Text>
      )}
    </View>
  );
}

function KpiGrid({ numbers }: { numbers: Array<{ label: string; value: number }> }) {
  if (!numbers.length) return null;
  return (
    <View style={styles.kpiGrid}>
      {numbers.map((item) => (
        <View key={item.label} style={styles.kpiCard}>
          <Text style={styles.kpiLabel} numberOfLines={2}>
            {item.label.replaceAll("_", " ")}
          </Text>
          <Text style={styles.kpiValue}>{formatValue(item.value)}</Text>
        </View>
      ))}
    </View>
  );
}

function BarChart({ numbers }: { numbers: Array<{ label: string; value: number }> }) {
  const max = Math.max(...numbers.map((item) => Math.abs(item.value)), 1);
  return (
    <View style={styles.chart}>
      <Text style={styles.cardTitle}>Resumen visual</Text>
      {numbers.map((item) => (
        <View key={item.label} style={styles.barRow}>
          <Text style={styles.barLabel} numberOfLines={1}>
            {item.label.replaceAll("_", " ")}
          </Text>
          <View style={styles.barTrack}>
            <View style={[styles.barFill, { width: `${Math.max(5, (Math.abs(item.value) / max) * 100)}%` }]} />
          </View>
        </View>
      ))}
    </View>
  );
}

function endpointWithId(endpoint: string | undefined, id: string) {
  return endpoint ? endpoint.replace("{id}", encodeURIComponent(id)) : "";
}

function isOperationalServicesTable(section: AppSection, table: NonNullable<AppSection["table"]>) {
  return (
    section.key === "tabla-servicios" ||
    table.createEndpoint === "/servicios/add" ||
    table.detailEndpoint === "/servicios/{id}" ||
    (table.columns.includes("consec") && table.columns.includes("num_informe") && table.columns.includes("buque_contenedor"))
  );
}

const PHONE_PREFIXES_FULL = [
  "+1",
  "+51",
  "+52",
  "+54",
  "+55",
  "+56",
  "+57",
  "+58",
  "+501",
  "+502",
  "+503",
  "+504",
  "+505",
  "+506",
  "+507",
  "+591",
  "+593",
  "+595",
  "+597",
  "+598"
];
const PHONE_PREFIXES_SHORT = ["+506", "+507", "+51", "+52", "+53", "+54", "+57", "+58"];
const PHONE_PREFIXES_EMPLOYEE = ["+506", "+57", "+1"];
const CIVIL_STATUS = ["Soltero", "Casado", "Union libre", "Divorciado", "Separado", "Viudo", "Otro"];
const GENDERS = ["Masculino", "Femenino", "Otro"];
const WORKDAYS = ["Tiempo completo", "Medio tiempo", "Por horas"];
const PAYMENT_FREQUENCY = ["Mensual", "Quincenal", "Semanal"];
const CURRENCIES = ["CRC", "USD", "EUR"];
const SUPPLIER_TYPES = [
  "Limpieza",
  "Alimentacion",
  "Contaduria",
  "Abogacia",
  "Consultoria Comercial",
  "Consultoria Legal",
  "Consultoria Impositiva",
  "Internet",
  "Renta Local",
  "Mantenimiento Vehicular",
  "Otro"
];

type MasterField = {
  key: string;
  label: string;
  options?: string[];
  dynamicOptions?: "operations" | "ports";
  source?: string[];
  readonly?: boolean;
  required?: boolean;
};

type MasterFormConfig = {
  title: string;
  codeKey: string;
  codePrefix?: string;
  codeSuffix?: string;
  ultimoEndpoint?: string;
  fallbackCode: string;
  fields: MasterField[];
};

const MASTER_FORMS: Record<string, MasterFormConfig> = {
  clientes: {
    title: "Cliente",
    codeKey: "Codigo",
    codePrefix: "MSL",
    codeSuffix: "C",
    ultimoEndpoint: "/clientes/ultimo",
    fallbackCode: "MSL-0001-C",
    fields: [
      { key: "Codigo", label: "Codigo", source: ["codigo"], readonly: true },
      { key: "NombreJuridico", label: "Nombre Juridico", source: ["nombrejuridico"] },
      { key: "NombreComercial", label: "Nombre Comercial", source: ["nombrecomercial"] },
      { key: "Pais", label: "Pais", source: ["pais"] },
      { key: "CedulaJuridicaVAT", label: "Cedula Juridica / VAT", source: ["cedulajuridicavat"] },
      { key: "Provincia", label: "Provincia", source: ["provincia"] },
      { key: "Canton", label: "Canton", source: ["canton"] },
      { key: "Distrito", label: "Distrito", source: ["distrito"] },
      { key: "DireccionExacta", label: "Direccion exacta", source: ["direccionexacta"] },
      { key: "FechaDePago", label: "Fecha de pago", source: ["fecha_pago"] },
      { key: "Correo", label: "Correo", source: ["correo"] },
      { key: "Prefijo", label: "Prefijo", source: ["prefijo"], options: PHONE_PREFIXES_FULL },
      { key: "Telefono", label: "Telefono", source: ["telefono"] },
      { key: "ContactoPrincipal", label: "Contacto principal", source: ["contacto_principal"] },
      { key: "ContactoSecundario", label: "Contacto secundario", source: ["contacto_secundario"] },
      { key: "Comentarios", label: "Comentarios", source: ["comentarios"] }
    ]
  },
  proveedores: {
    title: "Proveedor",
    codeKey: "Codigo",
    codePrefix: "MSL",
    codeSuffix: "P",
    ultimoEndpoint: "/proveedores/ultimo",
    fallbackCode: "MSL-0001-P",
    fields: [
      { key: "Codigo", label: "Codigo", readonly: true },
      { key: "Nombre", label: "Nombre" },
      { key: "Apellidos", label: "Apellidos" },
      { key: "NombreComercial", label: "Nombre Comercial" },
      { key: "Cedula", label: "Cedula / VAT" },
      { key: "Pais", label: "Pais" },
      { key: "Provincia", label: "Provincia" },
      { key: "Canton", label: "Canton" },
      { key: "Distrito", label: "Distrito" },
      { key: "DireccionExacta", label: "Direccion" },
      { key: "Prefijo", label: "Prefijo", options: PHONE_PREFIXES_SHORT },
      { key: "Telefono", label: "Telefono" },
      { key: "Correo", label: "Correo" },
      { key: "TerminosPago", label: "Terminos de pago" },
      { key: "Banco", label: "Banco" },
      { key: "CuentaIBAN", label: "Cuenta IBAN" },
      { key: "SwiftCode", label: "Swift Code" },
      { key: "UID", label: "UID" },
      { key: "DireccionBanco", label: "Direccion Banco" },
      { key: "TipoProveeduria", label: "Tipo de Proveeduria", options: SUPPLIER_TYPES },
      { key: "Comentarios", label: "Comentarios" }
    ]
  },
  empleados: {
    title: "Empleado",
    codeKey: "codigo",
    fallbackCode: "MSL-0001-E",
    fields: [
      { key: "codigo", label: "Codigo", readonly: true },
      { key: "nombre", label: "Nombre" },
      { key: "apellidos", label: "Apellidos" },
      { key: "estado_civil", label: "Estado civil", options: CIVIL_STATUS },
      { key: "genero", label: "Genero", options: GENDERS },
      { key: "nacionalidad", label: "Nacionalidad" },
      { key: "prefijo", label: "Prefijo", options: PHONE_PREFIXES_EMPLOYEE },
      { key: "telefono", label: "Telefono" },
      { key: "provincia", label: "Provincia" },
      { key: "canton", label: "Canton" },
      { key: "distrito", label: "Distrito" },
      { key: "direccion", label: "Direccion" },
      { key: "jornada", label: "Jornada", options: WORKDAYS },
      { key: "salario", label: "Salario" },
      { key: "pago", label: "Pago", options: PAYMENT_FREQUENCY },
      { key: "banco", label: "Banco" },
      { key: "cuenta_iban", label: "Cuenta IBAN" },
      { key: "moneda", label: "Moneda", options: CURRENCIES },
      { key: "enfermedades", label: "Enfermedades" },
      { key: "contacto_emergencia", label: "Contacto emergencia" },
      { key: "telefono_emergencia", label: "Tel. emergencia" },
      { key: "activo1", label: "Activo 1" },
      { key: "marca1", label: "Marca 1" },
      { key: "serial1", label: "Serial 1" },
      { key: "activo2", label: "Activo 2" },
      { key: "marca2", label: "Marca 2" },
      { key: "serial2", label: "Serial 2" },
      { key: "activo3", label: "Activo 3" },
      { key: "marca3", label: "Marca 3" },
      { key: "serial3", label: "Serial 3" }
    ]
  },
  surveyores: {
    title: "Surveyor",
    codeKey: "codigo",
    codePrefix: "MSL",
    codeSuffix: "S",
    ultimoEndpoint: "/surveyores/ultimo",
    fallbackCode: "MSL-0001-S",
    fields: [
      { key: "codigo", label: "Codigo", readonly: true },
      { key: "nombre", label: "Nombre" },
      { key: "apellidos", label: "Apellidos" },
      { key: "estado_civil", label: "Estado civil", options: CIVIL_STATUS },
      { key: "genero", label: "Genero", options: GENDERS },
      { key: "nacionalidad", label: "Nacionalidad" },
      { key: "prefijo", label: "Prefijo", options: PHONE_PREFIXES_EMPLOYEE },
      { key: "telefono", label: "Telefono" },
      { key: "provincia", label: "Provincia" },
      { key: "canton", label: "Canton" },
      { key: "distrito", label: "Distrito" },
      { key: "direccion", label: "Direccion exacta" },
      { key: "jornada", label: "Jornada", options: WORKDAYS },
      { key: "pago", label: "Pago", options: PAYMENT_FREQUENCY },
      { key: "banco", label: "Banco" },
      { key: "cuenta_iban", label: "Cuenta IBAN" },
      { key: "swift", label: "Swift Code" },
      { key: "uid", label: "UID" },
      { key: "moneda", label: "Moneda", options: CURRENCIES },
      { key: "enfermedades", label: "Enfermedades" },
      { key: "contacto_emergencia", label: "Contacto emergencia" },
      { key: "telefono_emergencia", label: "Tel. emergencia" },
      { key: "operacion", label: "Operacion", dynamicOptions: "operations" },
      { key: "honorario", label: "Honorario" },
      { key: "puerto", label: "Puertos que atiende", dynamicOptions: "ports" }
    ]
  },
  "servicios-md": {
    title: "Servicio",
    codeKey: "codigo",
    codePrefix: "MSL",
    codeSuffix: "S",
    ultimoEndpoint: "/servicios_md/ultimo",
    fallbackCode: "MSL-0001-S",
    fields: [
      { key: "codigo", label: "Codigo", readonly: true },
      { key: "codigo_prod", label: "Codigo Producto" },
      { key: "nombre", label: "Nombre del servicio", required: true },
      { key: "costo", label: "Costo" }
    ]
  }
};

function DesktopTable({
  section,
  rows,
  session,
  onReload
}: {
  section: AppSection;
  rows: Record<string, unknown>[];
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onReload: () => void;
}) {
  const table = section.table!;
  const masterForm = MASTER_FORMS[section.key];
  const operationalServicesTable = isOperationalServicesTable(section, table);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [modalMode, setModalMode] = useState<"view" | "edit" | "add" | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const [showServiceForm, setShowServiceForm] = useState(false);
  const [serviceAction, setServiceAction] = useState<string | null>(null);
  const [serviceDetail, setServiceDetail] = useState<Record<string, unknown> | null>(null);
  const [tableRows, setTableRows] = useState(rows);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    setTableRows(rows);
    setSelectedIndex(null);
  }, [rows, section.key]);

  const filteredRows = tableRows.filter((row) => {
    if (!search.trim()) return true;
    const needle = search.toLowerCase();
    const fields = table.filters?.length ? table.filters : table.columns;
    return fields.some((field) => formatValue(row[field]).toLowerCase().includes(needle));
  });

  const selectedRow = selectedIndex === null ? null : filteredRows[selectedIndex] || null;
  const selectedId = selectedRow ? formatValue(selectedRow[table.idField]) : "";

  async function runAction(action: TableAction) {
    setMessage("");

    if (action.key === "add") {
      if (operationalServicesTable || action.label.toLowerCase().includes("agregar servicio")) {
        setModalMode(null);
        setForm({});
        setShowServiceForm(true);
        return;
      }
      if (masterForm) {
        setForm({});
        setModalMode("add");
        return;
      }
      const blank = Object.fromEntries(table.columns.map((column) => [column, ""]));
      setForm(blank);
      setModalMode("add");
      return;
    }

    if (!selectedRow || !selectedId) {
      setMessage("Seleccione una fila primero.");
      return;
    }

    if (action.key === "view" || action.key === "edit") {
      setBusy(true);
      try {
        const detail = table.detailEndpoint
          ? await apiRequest<Record<string, unknown>>(endpointWithId(table.detailEndpoint, selectedId), { session })
          : selectedRow;
        if (operationalServicesTable) {
          setServiceDetail(detail);
          setServiceAction(action.key);
          return;
        }
        if (masterForm) {
          setForm(Object.fromEntries(Object.entries(detail).map(([key, value]) => [key, formatValue(value) === "-" ? "" : formatValue(value)])));
          setModalMode(action.key);
          return;
        }
        setForm(Object.fromEntries(table.columns.map((column) => [column, formatValue(detail[column])])));
        setModalMode(action.key);
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "No se pudo cargar el registro.");
      } finally {
        setBusy(false);
      }
      return;
    }

    if (action.key === "generate") {
      if (operationalServicesTable) {
        setBusy(true);
        try {
          const detail = table.detailEndpoint
            ? await apiRequest<Record<string, unknown>>(endpointWithId(table.detailEndpoint, selectedId), { session })
            : selectedRow;
          setServiceDetail(detail);
          setServiceAction(action.label);
        } catch (err) {
          setMessage(err instanceof Error ? err.message : "No se pudo cargar el servicio.");
        } finally {
          setBusy(false);
        }
        return;
      }
      if (!action.endpoint) return;
      setBusy(true);
      try {
        await apiRequest(endpointWithId(action.endpoint, selectedId), { method: action.method ?? "PUT", session });
        setMessage("Accion ejecutada correctamente.");
        onReload();
      } catch (err) {
        setMessage(err instanceof Error ? err.message : "No se pudo ejecutar la accion.");
      } finally {
        setBusy(false);
      }
      return;
    }

    if (action.key === "delete") {
      Alert.alert("Confirmar", `Eliminar ${selectedId}?`, [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Eliminar",
          style: "destructive",
          onPress: async () => {
            if (!table.deleteEndpoint) return;
            setBusy(true);
            try {
              await apiRequest(endpointWithId(table.deleteEndpoint, selectedId), { method: "DELETE", session });
              setSelectedIndex(null);
              onReload();
            } catch (err) {
              setMessage(err instanceof Error ? err.message : "No se pudo eliminar.");
            } finally {
              setBusy(false);
            }
          }
        }
      ]);
    }
  }

  async function saveForm() {
    if (!modalMode || modalMode === "view") return;
    const endpoint = modalMode === "add" ? table.createEndpoint : table.updateEndpoint;
    const method = modalMode === "add" ? "POST" : "PUT";
    if (!endpoint) return;

    const id = form[table.idField] || selectedId;
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(endpointWithId(endpoint, id), { method, body: form, session });
      setModalMode(null);
      onReload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <FinanceFilters
        sectionKey={section.key}
        session={session}
        onLoading={setBusy}
        onMessage={setMessage}
        onRows={(nextRows) => {
          setSelectedIndex(null);
          setTableRows(nextRows);
        }}
        rows={tableRows}
        columns={table.columns}
      />
      <View style={styles.tableToolbar}>
        <TextInput
          autoCapitalize="none"
          autoCorrect={false}
          value={search}
          onChangeText={setSearch}
          placeholder="Filtrar tabla"
          style={styles.tableSearch}
        />
        <Text style={styles.tableCount}>{filteredRows.length} filas</Text>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator>
        <View>
          <View style={styles.tableHeader}>
            {table.columns.map((column) => (
              <Text key={column} style={styles.tableHeaderCell} numberOfLines={1}>
                {column.replaceAll("_", " ")}
              </Text>
            ))}
          </View>
          <ScrollView style={styles.tableRows} nestedScrollEnabled>
            {filteredRows.map((row, index) => (
              <Pressable
                key={`${formatValue(row[table.idField])}-${index}`}
                style={[styles.tableRow, selectedIndex === index && styles.tableRowSelected]}
                onPress={() => setSelectedIndex(index)}
              >
                {table.columns.map((column) => (
                  <Text key={column} style={styles.tableCell} numberOfLines={1}>
                    {formatValue(row[column])}
                  </Text>
                ))}
              </Pressable>
            ))}
          </ScrollView>
        </View>
      </ScrollView>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
        {table.actions.map((action) => (
          <Pressable key={action.key + action.label} style={styles.actionButton} onPress={() => runAction(action)}>
            <Text style={styles.actionButtonText}>{action.label}</Text>
          </Pressable>
        ))}
      </ScrollView>

      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}

      {masterForm ? (
        <MasterDataModal
          visible={modalMode !== null}
          mode={modalMode}
          sectionKey={section.key}
          initialData={form}
          table={table}
          session={session}
          onClose={() => setModalMode(null)}
          onSaved={() => {
            setModalMode(null);
            onReload();
          }}
        />
      ) : (
        <Modal visible={modalMode !== null} animationType="slide" onRequestClose={() => setModalMode(null)}>
          <SafeAreaView style={styles.modalScreen}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>
                {modalMode === "view" ? "Ver" : modalMode === "edit" ? "Editar" : "Agregar"} {section.label}
              </Text>
              <Pressable style={styles.modalClose} onPress={() => setModalMode(null)}>
                <Text style={styles.modalCloseText}>Cerrar</Text>
              </Pressable>
            </View>
            <ScrollView contentContainerStyle={styles.modalBody}>
              {table.columns.map((column) => (
                <View key={column} style={styles.formField}>
                  <Text style={styles.label}>{column.replaceAll("_", " ")}</Text>
                  <TextInput
                    editable={modalMode !== "view" && column !== "fecharegistro"}
                    value={form[column] ?? ""}
                    onChangeText={(value) => setForm((current) => ({ ...current, [column]: value }))}
                    style={[styles.input, modalMode === "view" && styles.readonlyInput]}
                  />
                </View>
              ))}
              {modalMode !== "view" ? <PrimaryButton label="Guardar" loading={busy} onPress={saveForm} /> : null}
              {message ? <Text style={styles.error}>{message}</Text> : null}
            </ScrollView>
          </SafeAreaView>
        </Modal>
      )}
      <ServiceCreateModal
        visible={showServiceForm}
        session={session}
        onClose={() => setShowServiceForm(false)}
        onSaved={() => {
          setShowServiceForm(false);
          onReload();
        }}
      />
      <ServiceActionModal
        visible={serviceAction !== null}
        action={serviceAction}
        service={serviceDetail}
        session={session}
        onClose={() => {
          setServiceAction(null);
          setServiceDetail(null);
        }}
        onSaved={() => {
          setServiceAction(null);
          setServiceDetail(null);
          onReload();
        }}
      />
    </View>
  );
}

function MasterDataModal({
  visible,
  mode,
  sectionKey,
  initialData,
  table,
  session,
  onClose,
  onSaved
}: {
  visible: boolean;
  mode: "view" | "edit" | "add" | null;
  sectionKey: string;
  initialData: Record<string, unknown>;
  table: NonNullable<AppSection["table"]>;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const config = MASTER_FORMS[sectionKey];
  const [form, setForm] = useState<Record<string, string>>({});
  const [operations, setOperations] = useState<string[]>([]);
  const [ports, setPorts] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const readonly = mode === "view";

  useEffect(() => {
    if (!visible || !config || !mode) return;
    setMessage("");

    const nextForm = Object.fromEntries(
      config.fields.map((field) => {
        const value = readMasterValue(initialData, field);
        return [field.key, value];
      })
    );

    if (mode === "add") {
      nextForm[config.codeKey] = config.fallbackCode;
      if (config.ultimoEndpoint && config.codePrefix && config.codeSuffix) {
        apiRequest<{ ultimo?: number }>(config.ultimoEndpoint, { session })
          .then((payload) => {
            const nextNumber = Number(payload.ultimo || 0) + 1;
            setForm((current) => ({
              ...current,
              [config.codeKey]: `${config.codePrefix}-${String(nextNumber).padStart(4, "0")}-${config.codeSuffix}`
            }));
          })
          .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo generar el codigo."));
      }
    }

    setForm(nextForm);
  }, [config, initialData, mode, session, visible]);

  useEffect(() => {
    if (!visible || sectionKey !== "surveyores") return;
    Promise.all([
      apiRequest("/servicios_md/?page=1&page_size=500", { session }),
      apiRequest("/cpp/puertos_all", { session })
    ])
      .then(([servicePayload, portsPayload]) => {
        setOperations(toOptions(servicePayload, ["nombre", "Nombre"]));
        setPorts(toOptions(portsPayload, ["puerto", "nombre", "name"]));
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudieron cargar operaciones o puertos."));
  }, [sectionKey, session, visible]);

  if (!config || !mode) return null;

  function optionsFor(field: MasterField) {
    if (field.dynamicOptions === "operations") return operations;
    if (field.dynamicOptions === "ports") return ports;
    return field.options || [];
  }

  function update(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    if (readonly) return;
    const missing = config.fields.find((field) => field.required && !String(form[field.key] || "").trim());
    if (missing) {
      setMessage(`${missing.label} es obligatorio.`);
      return;
    }

    const endpoint = mode === "add" ? table.createEndpoint : table.updateEndpoint;
    const method = mode === "add" ? "POST" : "PUT";
    if (!endpoint) return;

    setBusy(true);
    setMessage("");
    try {
      await apiRequest(endpointWithId(endpoint, form[config.codeKey] || ""), {
        method,
        session,
        body: normalizeMasterPayload(sectionKey, form)
      });
      onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>
            {mode === "view" ? "Ver" : mode === "edit" ? "Editar" : "Agregar"} {config.title}
          </Text>
          <Pressable style={styles.modalClose} onPress={onClose}>
            <Text style={styles.modalCloseText}>Cerrar</Text>
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          {config.fields.map((field) => {
            const options = optionsFor(field);
            if (options.length && !readonly && !field.readonly) {
              return (
                <SelectField
                  key={field.key}
                  label={field.label}
                  value={form[field.key] || ""}
                  options={options}
                  onChange={(value) => update(field.key, value)}
                />
              );
            }

            return (
              <View key={field.key} style={styles.formField}>
                <Text style={styles.label}>{field.label}</Text>
                <TextInput
                  editable={!readonly && !field.readonly}
                  value={form[field.key] || ""}
                  onChangeText={(value) => update(field.key, value)}
                  style={[styles.input, (readonly || field.readonly) && styles.readonlyInput]}
                />
              </View>
            );
          })}
          {!readonly ? <PrimaryButton label="Guardar" loading={busy} onPress={save} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function readMasterValue(data: Record<string, unknown>, field: MasterField) {
  const keys = [field.key, ...(field.source || [])];
  for (const key of keys) {
    const value = data[key];
    if (value !== undefined && value !== null) return formatValue(value) === "-" ? "" : formatValue(value);
  }
  return "";
}

function normalizeMasterPayload(sectionKey: string, form: Record<string, string>) {
  if (sectionKey === "empleados") {
    return {
      ...form,
      salario: form.salario ? form.salario.replace(",", ".") : null
    };
  }

  if (sectionKey === "surveyores") {
    return {
      ...form,
      honorario: form.honorario ? form.honorario.replace(",", ".") : null
    };
  }

  if (sectionKey === "servicios-md") {
    return {
      ...form,
      costo: form.costo ? form.costo.replace(",", ".") : null
    };
  }

  return form;
}

function buildAccountingPeriods() {
  const today = new Date();
  const current = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
  const previousDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  const previous = `${previousDate.getFullYear()}-${String(previousDate.getMonth() + 1).padStart(2, "0")}`;
  return [previous, current];
}

function currentAccountingPeriod() {
  const periods = buildAccountingPeriods();
  return periods[periods.length - 1];
}

function previousAccountingPeriod() {
  const periods = buildAccountingPeriods();
  return periods[0];
}

function clientLabelsAndCodes(payload: unknown) {
  const labels: string[] = [];
  const codes: Record<string, string> = {};

  pickList(payload).forEach((item) => {
    const row = asRecord(item);
    if (!row) return;
    const code = formatValue(row.codigo ?? row.Codigo);
    const name = formatValue(row.nombrecomercial ?? row.nombrejuridico ?? row.NombreComercial ?? row.NombreJuridico);
    if (!name || name === "-") return;
    const label = code && code !== "-" ? `${code} - ${name}` : name;
    labels.push(label);
    if (code && code !== "-") codes[label] = code;
  });

  return { labels, codes };
}

function buildCsv(rows: Record<string, unknown>[], columns: string[]) {
  const escapeCell = (value: unknown) => `"${formatValue(value).replace(/"/g, '""')}"`;
  return [columns.map(escapeCell).join(","), ...rows.map((row) => columns.map((column) => escapeCell(row[column])).join(","))].join("\n");
}

function currentYearPeriod(period: string) {
  const fallback = new Date();
  const [year, month] = period ? period.split("-") : [String(fallback.getFullYear()), String(fallback.getMonth() + 1).padStart(2, "0")];
  return { year: year || String(fallback.getFullYear()), month: month || String(fallback.getMonth() + 1).padStart(2, "0") };
}

function filterAccountingRowsByPeriodRange(rows: Record<string, unknown>[], from: string, to: string) {
  return rows.filter((row) => {
    const period = formatValue(row.period);
    return period >= from && period <= to;
  });
}

function accountingPeriodSummary(rows: Record<string, unknown>[]) {
  const periods = new Map<string, Set<string>>();
  rows.forEach((row) => {
    const period = formatValue(row.period);
    const entryId = formatValue(row.entry_id);
    if (!period || period === "-") return;
    if (!periods.has(period)) periods.set(period, new Set());
    periods.get(period)?.add(entryId);
  });

  return Array.from(periods.entries())
    .map(([period, entries]) => ({ period, count: entries.size }))
    .sort((a, b) => b.period.localeCompare(a.period));
}

function FinanceFilters({
  sectionKey,
  session,
  onLoading,
  onMessage,
  onRows,
  rows = [],
  columns = []
}: {
  sectionKey: string;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onLoading: (loading: boolean) => void;
  onMessage: (message: string) => void;
  onRows: (rows: Record<string, unknown>[]) => void;
  rows?: Record<string, unknown>[];
  columns?: string[];
}) {
  const enabled = ["billing", "invoicing", "collections", "bank-reconciliation", "invoice-to-pay", "accounting"].includes(sectionKey);
  const [clientes, setClientes] = useState<string[]>(["ALL"]);
  const [clientCodes, setClientCodes] = useState<Record<string, string>>({});
  const [accounts, setAccounts] = useState<string[]>(["TODOS"]);
  const accountingPeriods = useMemo(() => buildAccountingPeriods(), []);
  const [form, setForm] = useState<Record<string, string>>({
    cliente: sectionKey === "billing" ? "" : "ALL",
    fecha_desde: "",
    fecha_hasta: "",
    tipo_factura: "",
    tipo_documento: "",
    bucket_aging: "",
    estado_factura: "",
    disputada: "",
    referencia: "",
    ver_todos: "false",
    obligation_type: "",
    payee: "",
    status: "ALL",
    issue_date_from: "",
    issue_date_to: "",
    due_date_from: "",
    due_date_to: "",
    payment_date_from: "",
    payment_date_to: "",
    period: currentAccountingPeriod(),
    search_mode: "SINGLE",
    period_from: previousAccountingPeriod(),
    period_to: currentAccountingPeriod(),
    origin: "TODOS",
    account: "TODOS",
    report: "ASIENTOS",
    report_format: "CSV"
  });

  useEffect(() => {
    if (!enabled) return;
    apiRequest("/clientes?page=1&page_size=500", { session })
      .then((payload) => {
        const names = toOptions(payload, ["nombrecomercial", "nombrejuridico", "NombreComercial", "NombreJuridico"]);
        const { labels, codes } = clientLabelsAndCodes(payload);
        const needsCode = sectionKey === "bank-reconciliation";
        setClientCodes(codes);
        setClientes(sectionKey === "billing" ? names : ["ALL", ...(needsCode ? labels : names)]);
      })
      .catch(() => setClientes(sectionKey === "billing" ? [] : ["ALL"]));
  }, [enabled, sectionKey, session]);

  useEffect(() => {
    if (sectionKey !== "accounting") return;
    setForm((current) => ({
      ...current,
      period: currentAccountingPeriod(),
      search_mode: "SINGLE",
      period_from: previousAccountingPeriod(),
      period_to: currentAccountingPeriod(),
      origin: "TODOS",
      account: "TODOS",
      report: "ASIENTOS",
      report_format: "CSV"
    }));
    onRows([]);
    onMessage("");
    apiRequest("/accounting/accounts", { session })
      .then((payload) => {
        const rows = extractRows(payload);
        const labels = rows
          .map((row) => {
            const code = formatValue(row.account_code);
            const name = formatValue(row.account_name);
            return code && code !== "-" ? `${code} - ${name}` : "";
          })
          .filter(Boolean);
        setAccounts(["TODOS", ...labels]);
      })
      .catch(() => setAccounts(["TODOS"]));
  }, [sectionKey, session]);

  if (!enabled) return null;

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function appendParam(params: URLSearchParams, key: string, value?: string) {
    const clean = String(value || "").trim();
    if (!clean || clean === "ALL") return;
    params.set(key, clean);
  }

  async function search() {
    const params = new URLSearchParams();
    let endpoint = "";

    if (sectionKey === "billing") {
      if (!form.cliente.trim()) {
        onMessage("Seleccione un cliente para buscar servicios finalizados sin factura.");
        return;
      }
      params.set("cliente", form.cliente.trim());
      endpoint = `/invoicing/facturables?${params.toString()}`;
    }

    if (sectionKey === "invoicing") {
      appendParam(params, "cliente", form.cliente);
      appendParam(params, "fecha_desde", form.fecha_desde);
      appendParam(params, "fecha_hasta", form.fecha_hasta);
      appendParam(params, "tipo_factura", form.tipo_factura);
      appendParam(params, "tipo_documento", form.tipo_documento);
      params.set("page", "1");
      params.set("page_size", "50");
      endpoint = `/billing/search?${params.toString()}`;
    }

    if (sectionKey === "collections") {
      appendParam(params, "cliente", form.cliente);
      appendParam(params, "bucket_aging", form.bucket_aging);
      appendParam(params, "estado_factura", form.estado_factura);
      if (form.disputada) params.set("disputada", form.disputada === "True" ? "true" : "false");
      params.set("page", "1");
      params.set("page_size", "50");
      endpoint = `/collections/search?${params.toString()}`;
    }

    if (sectionKey === "bank-reconciliation") {
      const selectedClientCode = clientCodes[form.cliente] || "";
      appendParam(params, "codigo_cliente", selectedClientCode);
      appendParam(params, "referencia", form.referencia);
      params.set("ver_todos", form.ver_todos === "true" ? "true" : "false");
      params.set("page", "1");
      params.set("page_size", "50");
      if (form.ver_todos !== "true" && !selectedClientCode && !form.referencia.trim()) {
        onMessage("Seleccione cliente, referencia o active Ver todos.");
        return;
      }
      endpoint = `/bank-reconciliation?${params.toString()}`;
    }

    if (sectionKey === "invoice-to-pay") {
      appendParam(params, "obligation_type", form.obligation_type);
      appendParam(params, "payee", form.payee);
      appendParam(params, "status", form.status);
      appendParam(params, "issue_date_from", form.issue_date_from);
      appendParam(params, "issue_date_to", form.issue_date_to);
      appendParam(params, "due_date_from", form.due_date_from);
      appendParam(params, "due_date_to", form.due_date_to);
      appendParam(params, "payment_date_from", form.payment_date_from);
      appendParam(params, "payment_date_to", form.payment_date_to);
      endpoint = `/invoice-to-pay/search${params.toString() ? `?${params.toString()}` : ""}`;
    }

    if (sectionKey === "accounting") {
      if (!form.tc_rate) {
        onMessage("Debe obtener el Tipo de Cambio antes de consultar asientos.");
        onRows([]);
        return;
      }

      if (form.search_mode === "RANGE") {
        if (!form.period_from || !form.period_to) {
          onMessage("Seleccione periodo desde y hasta.");
          return;
        }
        if (form.period_from > form.period_to) {
          onMessage("El periodo inicial no puede ser mayor al final.");
          return;
        }
      } else {
        params.set("period", currentAccountingPeriod());
      }
      appendParam(params, "origin", form.origin);
      if (form.account && form.account !== "TODOS") {
        params.set("account_code", form.account.split(" - ")[0]);
      }
      endpoint = `/accounting/ledger${params.toString() ? `?${params.toString()}` : ""}`;
    }

    onLoading(true);
    onMessage("");
    try {
      let syncSummary: Record<string, unknown> | null = null;
      if (sectionKey === "accounting") {
        syncSummary = await apiRequest<Record<string, unknown>>("/accounting/sync/all", { method: "POST", session });
      }
      const payload = await apiRequest(endpoint, { session });
      const rawRows = rowsForSection(sectionKey, payload);
      const nextRows =
        sectionKey === "accounting" && form.search_mode === "RANGE"
          ? filterAccountingRowsByPeriodRange(rawRows, form.period_from, form.period_to)
          : rawRows;
      onRows(nextRows);
      if (sectionKey === "accounting" && !nextRows.length) {
        const allPayload = await apiRequest("/accounting/ledger", { session });
        const allRows = rowsForSection(sectionKey, allPayload);
        const summary = accountingPeriodSummary(allRows);
        const latest = summary[0];
        if (latest) {
          onMessage(
            `Sin asientos en ${form.search_mode === "RANGE" ? `${form.period_from} a ${form.period_to}` : currentAccountingPeriod()}. Ultimo periodo con asientos: ${latest.period} (${latest.count}).`
          );
        } else {
          onMessage("No existen asientos contables despues de sincronizar.");
        }
      } else if (sectionKey === "accounting" && syncSummary) {
        onMessage(`Asientos cargados. Nuevos creados: ${formatValue(syncSummary.created)}.`);
      }
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo aplicar el filtro.");
    } finally {
      onLoading(false);
    }
  }

  function clear() {
    setForm({
      cliente: sectionKey === "billing" ? "" : "ALL",
      fecha_desde: "",
      fecha_hasta: "",
      tipo_factura: "",
      tipo_documento: "",
      bucket_aging: "",
      estado_factura: "",
      disputada: "",
      referencia: "",
      ver_todos: "false",
      obligation_type: "",
      payee: "",
      status: "ALL",
      issue_date_from: "",
      issue_date_to: "",
      due_date_from: "",
      due_date_to: "",
      payment_date_from: "",
      payment_date_to: "",
      period: currentAccountingPeriod(),
      search_mode: "SINGLE",
      period_from: previousAccountingPeriod(),
      period_to: currentAccountingPeriod(),
      origin: "TODOS",
      account: "TODOS",
      report: "ASIENTOS",
      report_format: "CSV"
    });
  }

  async function fetchExchangeRate() {
    onLoading(true);
    onMessage("");
    try {
      const data = await apiRequest<Record<string, unknown>>("/exchange-rate/today", { session });
      const rate = Number(data.rate || 0);
      setForm((current) => ({
        ...current,
        tc_rate: Number.isFinite(rate) && rate > 0 ? rate.toFixed(2) : formatValue(data.rate),
        tc_date: formatValue(data.date)
      }));
      onMessage("Tipo de cambio cargado.");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo obtener el tipo de cambio.");
    } finally {
      onLoading(false);
    }
  }

  async function openClosingStatus() {
    const period = form.search_mode === "RANGE" ? form.period_to : form.period;
    if (!period) {
      onMessage("Seleccione un periodo para revisar el cierre.");
      return;
    }
    const { year, month } = currentYearPeriod(period);
    onLoading(true);
    onMessage("");
    try {
      const status = await apiRequest<Record<string, unknown>>(
        `/closing/period/status?company_code=MSL-CR&fiscal_year=${year}&period=${Number(month)}&ledger=0L`,
        { session }
      );
      onMessage(
        `Cierre ${period}: GL ${formatValue(status.gl_closed)}, TB ${formatValue(status.tb_closed)}, PNL ${formatValue(
          status.pnl_closed
        )}, FS ${formatValue(status.fs_closed)}.`
      );
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo revisar el cierre contable.");
    } finally {
      onLoading(false);
    }
  }

  async function shareAccountingReport() {
    const label = `${form.report || "ASIENTOS"}_${form.period || form.period_to || "TODOS"}`;

    if (form.report_format === "EXCEL" || form.report_format === "PDF") {
      const params = new URLSearchParams();
      params.set("report", form.report || "ASIENTOS");
      if (form.search_mode === "RANGE") {
        if (form.period_from) params.set("period_from", form.period_from);
        if (form.period_to) params.set("period_to", form.period_to);
      } else {
        params.set("period", currentAccountingPeriod());
      }
      if (form.origin && form.origin !== "TODOS") params.set("origin", form.origin);
      if (form.account && form.account !== "TODOS") params.set("account_code", form.account.split(" - ")[0]);

      const format = form.report_format === "PDF" ? "pdf" : "excel";
      const url = `${API_BASE_URL}/accounting/reports/${format}?${params.toString()}`;
      onMessage("");
      try {
        const supported = await Linking.canOpenURL(url);
        if (!supported) throw new Error("El telefono no puede abrir la descarga.");
        await Linking.openURL(url);
        onMessage(`Descarga ${form.report_format} abierta.`);
      } catch (err) {
        const message = err instanceof Error ? err.message : "No se pudo abrir la descarga.";
        Alert.alert("Reporte contable", message);
        onMessage(message);
      }
      return;
    }

    if (!rows.length) {
      onMessage("Primero busque asientos para generar el reporte CSV.");
      return;
    }

    const csv = buildCsv(rows, columns.length ? columns : Object.keys(rows[0] || {}));
    onMessage("");
    try {
      const result = await Share.share({
        title: label,
        message: `${label}\n\n${csv}`
      });

      if (result.action === Share.sharedAction) {
        onMessage("Reporte generado y enviado al menu de compartir.");
      } else {
        onMessage("Reporte generado. Se cerro el menu de compartir sin enviar.");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo generar el reporte.";
      Alert.alert("Reporte contable", message);
      onMessage(message);
    }
  }

  return (
    <View style={styles.financeFilterBox}>
      <Text style={styles.cardTitle}>Filtros</Text>

      {sectionKey === "billing" ? (
        <>
          <SelectField label="Cliente" value={form.cliente} options={clientes} onChange={(value) => setValue("cliente", value)} />
          <Text style={styles.helperText}>
            {rows.length ? "Seleccione una linea para facturar manualmente o cargar XML." : "Sin pendientes por facturar para el cliente seleccionado."}
          </Text>
        </>
      ) : null}

      {sectionKey === "invoicing" ? (
        <>
          <SelectField label="Cliente" value={form.cliente} options={clientes} onChange={(value) => setValue("cliente", value)} />
          <Text style={styles.label}>Desde</Text>
          <TextInput style={styles.input} value={form.fecha_desde} onChangeText={(value) => setValue("fecha_desde", value)} placeholder="YYYY-MM-DD" />
          <Text style={styles.label}>Hasta</Text>
          <TextInput style={styles.input} value={form.fecha_hasta} onChangeText={(value) => setValue("fecha_hasta", value)} placeholder="YYYY-MM-DD" />
          <SelectField label="Tipo Factura" value={form.tipo_factura || "Todos"} options={["Todos", "MANUAL", "ELECTRONICA"]} onChange={(value) => setValue("tipo_factura", value === "Todos" ? "" : value)} />
          <SelectField label="Documento" value={form.tipo_documento || "Todos"} options={["Todos", "FACTURA", "NOTA_CREDITO"]} onChange={(value) => setValue("tipo_documento", value === "Todos" ? "" : value)} />
        </>
      ) : null}

      {sectionKey === "collections" ? (
        <>
          <SelectField label="Cliente" value={form.cliente} options={clientes} onChange={(value) => setValue("cliente", value)} />
          <SelectField label="Aging" value={form.bucket_aging || "Todos"} options={["Todos", "CURRENT", "1-30", "31-60", "61-90", "90+"]} onChange={(value) => setValue("bucket_aging", value === "Todos" ? "" : value)} />
          <SelectField label="Estado" value={form.estado_factura || "Todos"} options={["Todos", "EMITIDA", "PENDIENTE_PAGO", "PAGADA", "DISPUTADA", "WRITE_OFF"]} onChange={(value) => setValue("estado_factura", value === "Todos" ? "" : value)} />
          <SelectField label="Disputada" value={form.disputada || "Todos"} options={["Todos", "True", "False"]} onChange={(value) => setValue("disputada", value === "Todos" ? "" : value)} />
        </>
      ) : null}

      {sectionKey === "bank-reconciliation" ? (
        <>
          <SelectField label="Cliente" value={form.cliente} options={clientes} onChange={(value) => setValue("cliente", value)} />
          <Text style={styles.label}>Referencia Bancaria / Comprobante</Text>
          <TextInput style={styles.input} value={form.referencia} onChangeText={(value) => setValue("referencia", value)} placeholder="Referencia o comprobante" />
          <SelectField label="Ver todos" value={form.ver_todos === "true" ? "Si" : "No"} options={["No", "Si"]} onChange={(value) => setValue("ver_todos", value === "Si" ? "true" : "false")} />
        </>
      ) : null}

      {sectionKey === "invoice-to-pay" ? (
        <>
          <SelectField label="Obligacion" value={form.obligation_type || "Todos"} options={["Todos", "SURVEYOR", "SUPPLIER", "MANUAL"]} onChange={(value) => setValue("obligation_type", value === "Todos" ? "" : value)} />
          <Text style={styles.label}>Beneficiario</Text>
          <TextInput style={styles.input} value={form.payee} onChangeText={(value) => setValue("payee", value)} placeholder="Nombre del beneficiario" />
          <SelectField label="Status" value={form.status} options={["ALL", "PENDING", "PARTIAL", "PAID"]} onChange={(value) => setValue("status", value)} />
          <Text style={styles.label}>Fecha factura desde</Text>
          <TextInput style={styles.input} value={form.issue_date_from} onChangeText={(value) => setValue("issue_date_from", value)} placeholder="YYYY-MM-DD" />
          <Text style={styles.label}>Fecha factura hasta</Text>
          <TextInput style={styles.input} value={form.issue_date_to} onChangeText={(value) => setValue("issue_date_to", value)} placeholder="YYYY-MM-DD" />
          <Text style={styles.label}>Fecha vencimiento desde</Text>
          <TextInput style={styles.input} value={form.due_date_from} onChangeText={(value) => setValue("due_date_from", value)} placeholder="YYYY-MM-DD" />
          <Text style={styles.label}>Fecha vencimiento hasta</Text>
          <TextInput style={styles.input} value={form.due_date_to} onChangeText={(value) => setValue("due_date_to", value)} placeholder="YYYY-MM-DD" />
          <Text style={styles.label}>Ultimo pago desde</Text>
          <TextInput style={styles.input} value={form.payment_date_from} onChangeText={(value) => setValue("payment_date_from", value)} placeholder="YYYY-MM-DD" />
          <Text style={styles.label}>Ultimo pago hasta</Text>
          <TextInput style={styles.input} value={form.payment_date_to} onChangeText={(value) => setValue("payment_date_to", value)} placeholder="YYYY-MM-DD" />
        </>
      ) : null}

      {sectionKey === "accounting" ? (
        <>
          <View style={styles.accountingTcBox}>
            <View style={styles.accountingTcFields}>
              <View style={styles.accountingTcItem}>
                <Text style={styles.label}>TC</Text>
                <TextInput editable={false} style={[styles.input, styles.readonlyInput]} value={form.tc_rate || ""} />
              </View>
              <View style={styles.accountingTcItem}>
                <Text style={styles.label}>Fecha TC</Text>
                <TextInput editable={false} style={[styles.input, styles.readonlyInput]} value={form.tc_date || ""} />
              </View>
            </View>
            <Pressable style={styles.actionButton} onPress={fetchExchangeRate}>
              <Text style={styles.actionButtonText}>Buscar TC</Text>
            </Pressable>
          </View>
          <SelectField label="Buscar por" value={form.search_mode === "RANGE" ? "Rango" : "Periodo"} options={["Periodo", "Rango"]} onChange={(value) => setValue("search_mode", value === "Rango" ? "RANGE" : "SINGLE")} />
          {form.search_mode === "RANGE" ? (
            <>
              <SelectField label="Desde" value={form.period_from || previousAccountingPeriod()} options={accountingPeriods} onChange={(value) => setValue("period_from", value)} />
              <SelectField label="Hasta" value={form.period_to || currentAccountingPeriod()} options={accountingPeriods} onChange={(value) => setValue("period_to", value)} />
            </>
          ) : (
            <View style={styles.formField}>
              <Text style={styles.label}>Periodo actual</Text>
              <TextInput editable={false} style={[styles.input, styles.readonlyInput]} value={currentAccountingPeriod()} />
            </View>
          )}
          <SelectField label="Origen" value={form.origin} options={["TODOS", "ITP", "COLLECTIONS", "INVOICING", "MANUAL", "CASH_APP", "REVERSAL"]} onChange={(value) => setValue("origin", value)} />
          <SelectField label="Cuenta" value={form.account} options={accounts} onChange={(value) => setValue("account", value)} />
          <View style={styles.kpiGrid}>
            <View style={styles.kpiCard}>
              <Text style={styles.kpiLabel}>Total Debe</Text>
              <Text style={styles.kpiValue}>{formatValue(rows.reduce((sum, row) => sum + Number(row.debit || 0), 0))}</Text>
            </View>
            <View style={styles.kpiCard}>
              <Text style={styles.kpiLabel}>Total Haber</Text>
              <Text style={styles.kpiValue}>{formatValue(rows.reduce((sum, row) => sum + Number(row.credit || 0), 0))}</Text>
            </View>
          </View>
          <View style={styles.reportBox}>
            <Text style={styles.cardTitle}>Reportes</Text>
            <SelectField label="Reporte" value={form.report} options={["ASIENTOS", "MAYOR", "BC", "ESF", "ER", "FC"]} onChange={(value) => setValue("report", value)} />
            <SelectField label="Formato" value={form.report_format} options={["CSV", "EXCEL", "PDF"]} onChange={(value) => setValue("report_format", value)} />
            <View style={styles.financeFilterActions}>
              <Pressable style={styles.actionButton} onPress={shareAccountingReport}>
                <Text style={styles.actionButtonText}>Descargar Reporte</Text>
              </Pressable>
              <Pressable style={styles.modalClose} onPress={openClosingStatus}>
                <Text style={styles.modalCloseText}>Mayorizar / Cierre</Text>
              </Pressable>
            </View>
            {form.report_format !== "CSV" ? (
              <Text style={styles.helperText}>La descarga se abre desde el backend con los filtros contables seleccionados.</Text>
            ) : null}
          </View>
        </>
      ) : null}

      <View style={styles.financeFilterActions}>
        <Pressable style={styles.actionButton} onPress={search}>
          <Text style={styles.actionButtonText}>Buscar</Text>
        </Pressable>
        <Pressable style={styles.modalClose} onPress={clear}>
          <Text style={styles.modalCloseText}>Limpiar</Text>
        </Pressable>
      </View>
    </View>
  );
}

function pickList(payload: unknown, key = "data") {
  if (Array.isArray(payload)) return payload;
  const obj = asRecord(payload);
  const value = obj?.[key];
  return Array.isArray(value) ? value : [];
}

function toOptions(payload: unknown, labelKeys: string[]) {
  return pickList(payload)
    .map((item) => {
      if (typeof item === "string") return item;
      const obj = asRecord(item);
      if (!obj) return "";
      for (const key of labelKeys) {
        const value = obj[key];
        if (value) return formatValue(value);
      }
      return "";
    })
    .filter(Boolean);
}

function SelectField({
  label,
  value,
  options,
  onChange
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const filteredOptions = Array.from(new Set(options)).filter(Boolean);
  return (
    <View style={styles.formField}>
      <Text style={styles.label}>{label}</Text>
      <Pressable style={styles.selectBox} onPress={() => setOpen((current) => !current)}>
        <Text style={styles.selectText}>{value || "Seleccionar"}</Text>
      </Pressable>
      {open ? (
        <View style={styles.optionList}>
          <ScrollView nestedScrollEnabled style={styles.optionScroll}>
            {filteredOptions.map((option) => (
              <Pressable
                key={option}
                style={styles.optionItem}
                onPress={() => {
                  onChange(option);
                  setOpen(false);
                }}
              >
                <Text style={styles.optionText}>{option}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      ) : null}
    </View>
  );
}

function ServiceCreateModal({
  visible,
  session,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const today = new Date();
  const [form, setForm] = useState({
    tipo: "Buque",
    buque_contenedor: "",
    cliente: "",
    contacto: "",
    detalle: "",
    continente: "",
    pais: "",
    puerto: "",
    operacion: "",
    surveyor: "",
    honorarios: "",
    costo_operativo: "",
    fecha_inicio: today.toISOString().slice(0, 10),
    hora_inicio: `${String(today.getHours()).padStart(2, "0")}:${String(today.getMinutes()).padStart(2, "0")}`
  });
  const [clientes, setClientes] = useState<string[]>([]);
  const [continentes, setContinentes] = useState<string[]>([]);
  const [paises, setPaises] = useState<string[]>([]);
  const [puertos, setPuertos] = useState<string[]>([]);
  const [operaciones, setOperaciones] = useState<string[]>([]);
  const [surveyores, setSurveyores] = useState<string[]>([]);
  const [surveyorRows, setSurveyorRows] = useState<Record<string, unknown>[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!visible) return;
    setMessage("");
    Promise.all([
      apiRequest("/clientes?page=1&page_size=500", { session }),
      apiRequest("/cpp/continentes", { session }),
      apiRequest("/servicios_md/?page=1&page_size=500", { session }),
      apiRequest("/surveyores/?page=1&page_size=500", { session })
    ])
      .then(([clientesPayload, continentesPayload, serviciosPayload, surveyoresPayload]) => {
        setClientes(toOptions(clientesPayload, ["nombrecomercial", "nombrejuridico", "NombreComercial", "codigo"]));
        setContinentes(toOptions(continentesPayload, ["nombre", "continente"]));
        setOperaciones(toOptions(serviciosPayload, ["nombre", "Nombre"]));
        const rows = pickList(surveyoresPayload) as Record<string, unknown>[];
        setSurveyorRows(rows);
        setSurveyores(
          Array.from(
            new Set(
              rows
                .map((row) => `${formatValue(row.nombre)} ${formatValue(row.apellidos)}`.trim())
                .filter((name) => name && name !== "- -")
            )
          ).sort()
        );
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudieron cargar los catalogos."));
  }, [session, visible]);

  useEffect(() => {
    if (!form.continente) return;
    apiRequest(`/cpp/paises?continente=${encodeURIComponent(form.continente)}`, { session })
      .then((payload) => setPaises(toOptions(payload, ["nombre", "pais", "name"])))
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudieron cargar paises."));
  }, [form.continente, session]);

  useEffect(() => {
    if (!form.pais) return;
    apiRequest(`/cpp/puertos?pais=${encodeURIComponent(form.pais)}`, { session })
      .then((payload) => setPuertos(toOptions(payload, ["nombre", "puerto", "name"])))
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudieron cargar puertos."));
  }, [form.pais, session]);

  useEffect(() => {
    if (!form.surveyor || !form.operacion) return;
    const match = surveyorRows.find((row) => {
      const name = `${formatValue(row.nombre)} ${formatValue(row.apellidos)}`.trim().toLowerCase();
      return name === form.surveyor.toLowerCase() && formatValue(row.operacion).toLowerCase() === form.operacion.toLowerCase();
    });
    setForm((current) => ({ ...current, honorarios: match ? formatValue(match.honorario) : "" }));
  }, [form.operacion, form.surveyor, surveyorRows]);

  function update(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function save() {
    if (!form.tipo || !form.buque_contenedor || !form.cliente || !form.continente || !form.pais || !form.puerto) {
      setMessage("Complete tipo, buque/contenedor, cliente, continente, pais y puerto.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest("/servicios/add", {
        method: "POST",
        session,
        body: {
          ...form,
          honorarios: Number(String(form.honorarios || "0").replace(",", "")),
          costo_operativo: Number(String(form.costo_operativo || "0").replace(",", ""))
        }
      });
      onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar el servicio.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Agregar Servicio</Text>
          <Pressable style={styles.modalClose} onPress={onClose}>
            <Text style={styles.modalCloseText}>Cerrar</Text>
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          <Text style={styles.helperText}>Consecutivo automatico al guardar</Text>
          <SelectField label="Tipo" value={form.tipo} options={["Buque", "Contenedor"]} onChange={(value) => update("tipo", value)} />
          <Text style={styles.label}>Buque / Contenedor</Text>
          <TextInput style={styles.input} value={form.buque_contenedor} onChangeText={(value) => update("buque_contenedor", value)} />
          <SelectField label="Cliente" value={form.cliente} options={clientes} onChange={(value) => update("cliente", value)} />
          <Text style={styles.label}>Contacto</Text>
          <TextInput style={styles.input} value={form.contacto} onChangeText={(value) => update("contacto", value)} />
          <Text style={styles.label}>Detalle</Text>
          <TextInput style={styles.input} value={form.detalle} onChangeText={(value) => update("detalle", value)} />
          <SelectField
            label="Continente"
            value={form.continente}
            options={continentes}
            onChange={(value) => setForm((current) => ({ ...current, continente: value, pais: "", puerto: "" }))}
          />
          <SelectField
            label="Pais"
            value={form.pais}
            options={paises}
            onChange={(value) => setForm((current) => ({ ...current, pais: value, puerto: "" }))}
          />
          <SelectField label="Puerto" value={form.puerto} options={puertos} onChange={(value) => update("puerto", value)} />
          <SelectField label="Operacion" value={form.operacion} options={operaciones} onChange={(value) => update("operacion", value)} />
          <SelectField label="Surveyor" value={form.surveyor} options={surveyores} onChange={(value) => update("surveyor", value)} />
          <Text style={styles.label}>Honorarios</Text>
          <TextInput style={[styles.input, styles.readonlyInput]} editable={false} value={form.honorarios} />
          <Text style={styles.label}>Costo operativo</Text>
          <TextInput keyboardType="decimal-pad" style={styles.input} value={form.costo_operativo} onChangeText={(value) => update("costo_operativo", value)} />
          <Text style={styles.label}>Fecha inicio</Text>
          <TextInput style={styles.input} value={form.fecha_inicio} onChangeText={(value) => update("fecha_inicio", value)} placeholder="YYYY-MM-DD" />
          <Text style={styles.label}>Hora inicio</Text>
          <TextInput style={styles.input} value={form.hora_inicio} onChangeText={(value) => update("hora_inicio", value)} placeholder="HH:MM" />
          <PrimaryButton label="Guardar Servicio" loading={busy} onPress={save} />
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function ServiceActionModal({
  visible,
  action,
  service,
  session,
  onClose,
  onSaved
}: {
  visible: boolean;
  action: string | null;
  service: Record<string, unknown> | null;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>({});
  const [delayRows, setDelayRows] = useState([{ f1: "", h1: "", f2: "", h2: "" }]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const consec = service ? formatValue(service.consec) : "";
  const mode = action || "";

  useEffect(() => {
    if (!visible || !service) return;
    setMessage("");
    setForm({
      surveyor: formatValue(service.surveyor),
      honorarios: formatValue(service.honorarios),
      costo_operativo: formatValue(service.costo_operativo),
      costo_tarjetas: formatValue(service.costo_tarjetas),
      fecha_inicio: formatValue(service.fecha_inicio),
      hora_inicio: formatValue(service.hora_inicio),
      fecha_fin: formatValue(service.fecha_fin),
      hora_fin: formatValue(service.hora_fin),
      demoras: formatValue(service.demoras),
      razon_cancelacion: "",
      comentario_cancelacion: ""
    });
    setDelayRows([{ f1: "", h1: "", f2: "", h2: "" }]);
  }, [service, visible]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function toNumber(value: unknown) {
    const cleaned = String(value ?? "").trim().replace(",", ".");
    if (!cleaned || cleaned === "-") return 0;
    const parsed = Number(cleaned);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function allowsCardCost() {
    const pais = String(service?.pais ?? "").trim().toLowerCase();
    const surveyor = String(form.surveyor || service?.surveyor || "").trim().toLowerCase();
    return pais !== "costa rica" && surveyor.includes("pabel") && surveyor.includes("barreto");
  }

  function validateRequiredDateTime(dateValue: string, timeValue: string, label: string) {
    if (!dateValue.trim() || !timeValue.trim()) {
      setMessage(`Debe ingresar fecha y hora de ${label}.`);
      return false;
    }
    return true;
  }

  function validateFinalCosts() {
    const honorarios = toNumber(form.honorarios || service?.honorarios);
    const costoOperativo = toNumber(form.costo_operativo || service?.costo_operativo);
    const costoTarjetas = toNumber(form.costo_tarjetas || service?.costo_tarjetas);
    const pais = String(service?.pais ?? "").trim().toLowerCase();
    const surveyor = String(form.surveyor || service?.surveyor || "").trim().toLowerCase();

    if (honorarios <= 0 && costoOperativo <= 0 && costoTarjetas <= 0) {
      setMessage("Debe existir al menos un valor mayor a 0.00: honorarios, costo operativo o costo tarjetas.");
      return false;
    }

    if (pais === "costa rica" && surveyor.includes("pabel") && costoTarjetas <= 0) {
      setMessage("Para Costa Rica con Pabel Pena el costo tarjetas es obligatorio y debe ser mayor a 0.00.");
      return false;
    }

    return true;
  }

  function updateDelayRow(index: number, key: "f1" | "h1" | "f2" | "h2", value: string) {
    setDelayRows((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, [key]: value } : row)));
  }

  function addDelayRow() {
    setDelayRows((current) => [...current, { f1: "", h1: "", f2: "", h2: "" }]);
  }

  function removeDelayRow(index: number) {
    setDelayRows((current) => (current.length <= 1 ? current : current.filter((_, rowIndex) => rowIndex !== index)));
  }

  function calculateDelayMinutes() {
    let total = 0;

    for (const row of delayRows) {
      if (!row.f1.trim() || !row.h1.trim() || !row.f2.trim() || !row.h2.trim()) {
        setMessage("Todas las fechas y horas de demoras son obligatorias.");
        return null;
      }

      const start = new Date(`${row.f1.trim()}T${row.h1.trim()}:00`);
      const end = new Date(`${row.f2.trim()}T${row.h2.trim()}:00`);
      const minutes = Math.floor((end.getTime() - start.getTime()) / 60000);

      if (!Number.isFinite(minutes) || minutes < 0) {
        setMessage("Revise que las fechas y horas de demoras sean validas.");
        return null;
      }

      total += minutes;
    }

    return total;
  }

  async function submit() {
    if (!consec) return;
    setMessage("");

    if (mode === "Generar Consecutivo" && !validateRequiredDateTime(form.fecha_inicio, form.hora_inicio, "inicio")) return;
    if (mode === "Finalizar" && (!validateFinalCosts() || !validateRequiredDateTime(form.fecha_fin, form.hora_fin, "finalizacion"))) return;
    if (mode === "Cancelar" && (!form.razon_cancelacion.trim() || !form.comentario_cancelacion.trim())) {
      setMessage("Debe seleccionar un motivo y escribir una descripcion adicional.");
      return;
    }

    const delayTotal = mode === "Demoras" ? calculateDelayMinutes() : null;
    if (mode === "Demoras" && delayTotal === null) return;

    setBusy(true);
    try {
      if (mode === "edit") {
        const cardCostAllowed = allowsCardCost();
        await apiRequest(`/servicios/editar/${consec}`, {
          method: "PUT",
          session,
          body: {
            surveyor: form.surveyor,
            honorarios: toNumber(form.honorarios),
            costo_operativo: toNumber(form.costo_operativo),
            costo_tarjetas: cardCostAllowed ? toNumber(form.costo_tarjetas) : null,
            fecha_inicio: form.fecha_inicio,
            hora_inicio: form.hora_inicio
          }
        });
      } else if (mode === "Generar Consecutivo") {
        await apiRequest(`/servicios/confirmar/${consec}`, {
          method: "PUT",
          session,
          body: { fecha_inicio: form.fecha_inicio, hora_inicio: form.hora_inicio }
        });
      } else if (mode === "Finalizar") {
        await apiRequest(`/servicios/cerrar/${consec}`, {
          method: "PUT",
          session,
          body: { fecha_fin: form.fecha_fin, hora_fin: form.hora_fin }
        });
        await apiRequest(`/servicios/generar_informe/${consec}`, { method: "PUT", session });
      } else if (mode === "Cancelar") {
        await apiRequest(`/servicios/cancelar/${consec}`, {
          method: "PUT",
          session,
          body: {
            estado: "Cancelado",
            razon_cancelacion: form.razon_cancelacion,
            comentario_cancelacion: form.comentario_cancelacion
          }
        });
      } else if (mode === "Demoras") {
        await apiRequest(`/servicios/demoras/${consec}`, {
          method: "PUT",
          session,
          body: { total: String(delayTotal ?? 0) }
        });
      }
      onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo ejecutar la accion.");
    } finally {
      setBusy(false);
    }
  }

  const readonly = mode === "view";
  const title = mode === "view" ? "Ver Servicio" : mode === "edit" ? "Editar Servicio" : mode;
  const cardCostAllowed = allowsCardCost();

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>
            {title} {consec ? `#${consec}` : ""}
          </Text>
          <Pressable style={styles.modalClose} onPress={onClose}>
            <Text style={styles.modalCloseText}>Cerrar</Text>
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          {readonly && service
            ? Object.entries(service).map(([key, value]) => (
                <View key={key} style={styles.fieldRow}>
                  <Text style={styles.fieldKey}>{key.replaceAll("_", " ")}</Text>
                  <Text style={styles.fieldValue}>{formatValue(value)}</Text>
                </View>
              ))
            : null}

          {mode === "edit" ? (
            <>
              <Text style={styles.label}>Surveyor</Text>
              <TextInput style={styles.input} value={form.surveyor} onChangeText={(value) => setValue("surveyor", value)} />
              <Text style={styles.label}>Honorarios</Text>
              <TextInput keyboardType="decimal-pad" style={styles.input} value={form.honorarios} onChangeText={(value) => setValue("honorarios", value)} />
              <Text style={styles.label}>Costo operativo</Text>
              <TextInput keyboardType="decimal-pad" style={styles.input} value={form.costo_operativo} onChangeText={(value) => setValue("costo_operativo", value)} />
              <Text style={styles.label}>Costo tarjetas</Text>
              <TextInput
                editable={cardCostAllowed}
                keyboardType="decimal-pad"
                style={[styles.input, !cardCostAllowed && styles.readonlyInput]}
                value={cardCostAllowed ? form.costo_tarjetas : ""}
                onChangeText={(value) => setValue("costo_tarjetas", value)}
              />
              <Text style={styles.label}>Fecha inicio</Text>
              <TextInput style={styles.input} value={form.fecha_inicio} onChangeText={(value) => setValue("fecha_inicio", value)} placeholder="YYYY-MM-DD" />
              <Text style={styles.label}>Hora inicio</Text>
              <TextInput style={styles.input} value={form.hora_inicio} onChangeText={(value) => setValue("hora_inicio", value)} placeholder="HH:MM" />
            </>
          ) : null}

          {mode === "Generar Consecutivo" ? (
            <>
              <Text style={styles.helperText}>El backend asignara num_informe y pasara el servicio a En Operacion.</Text>
              <Text style={styles.label}>Fecha inicio</Text>
              <TextInput style={styles.input} value={form.fecha_inicio} onChangeText={(value) => setValue("fecha_inicio", value)} placeholder="YYYY-MM-DD" />
              <Text style={styles.label}>Hora inicio</Text>
              <TextInput style={styles.input} value={form.hora_inicio} onChangeText={(value) => setValue("hora_inicio", value)} placeholder="HH:MM" />
            </>
          ) : null}

          {mode === "Finalizar" ? (
            <>
              <View style={styles.summaryBox}>
                {["cliente", "buque_contenedor", "operacion", "detalle", "surveyor", "pais", "honorarios", "costo_operativo", "costo_tarjetas", "fecha_inicio", "hora_inicio"].map((key) => (
                  <View key={key} style={styles.fieldRow}>
                    <Text style={styles.fieldKey}>{key.replaceAll("_", " ")}</Text>
                    <Text style={styles.fieldValue}>{formatValue(service?.[key])}</Text>
                  </View>
                ))}
              </View>
              <Text style={styles.label}>Fecha finalizacion</Text>
              <TextInput style={styles.input} value={form.fecha_fin} onChangeText={(value) => setValue("fecha_fin", value)} placeholder="YYYY-MM-DD" />
              <Text style={styles.label}>Hora finalizacion</Text>
              <TextInput style={styles.input} value={form.hora_fin} onChangeText={(value) => setValue("hora_fin", value)} placeholder="HH:MM" />
            </>
          ) : null}

          {mode === "Cancelar" ? (
            <>
              <SelectField
                label="Motivo de cancelacion"
                value={form.razon_cancelacion}
                options={["Precio", "Buque atraca en otro puerto", "Respuesta tardia", "Buque no requerira los servicios"]}
                onChange={(value) => setValue("razon_cancelacion", value)}
              />
              <Text style={styles.label}>Descripcion adicional</Text>
              <TextInput
                multiline
                style={[styles.input, styles.multilineInput]}
                value={form.comentario_cancelacion}
                onChangeText={(value) => setValue("comentario_cancelacion", value)}
              />
            </>
          ) : null}

          {mode === "Demoras" ? (
            <>
              <Text style={styles.helperText}>Agregue cada demora con inicio y fin. La app suma el total en minutos igual que desktop.</Text>
              {delayRows.map((row, index) => (
                <View key={index} style={styles.delayBox}>
                  <View style={styles.delayHeader}>
                    <Text style={styles.cardTitle}>Demora {index + 1}</Text>
                    {delayRows.length > 1 ? (
                      <Pressable style={styles.smallDangerButton} onPress={() => removeDelayRow(index)}>
                        <Text style={styles.smallDangerButtonText}>X</Text>
                      </Pressable>
                    ) : null}
                  </View>
                  <Text style={styles.label}>Fecha inicio</Text>
                  <TextInput style={styles.input} value={row.f1} onChangeText={(value) => updateDelayRow(index, "f1", value)} placeholder="YYYY-MM-DD" />
                  <Text style={styles.label}>Hora inicio</Text>
                  <TextInput style={styles.input} value={row.h1} onChangeText={(value) => updateDelayRow(index, "h1", value)} placeholder="HH:MM" />
                  <Text style={styles.label}>Fecha fin</Text>
                  <TextInput style={styles.input} value={row.f2} onChangeText={(value) => updateDelayRow(index, "f2", value)} placeholder="YYYY-MM-DD" />
                  <Text style={styles.label}>Hora fin</Text>
                  <TextInput style={styles.input} value={row.h2} onChangeText={(value) => updateDelayRow(index, "h2", value)} placeholder="HH:MM" />
                </View>
              ))}
              <Pressable style={styles.secondaryButton} onPress={addDelayRow}>
                <Text style={styles.secondaryButtonText}>+ Anadir demora</Text>
              </Pressable>
            </>
          ) : null}

          {!readonly ? <PrimaryButton label="Confirmar" loading={busy} onPress={submit} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function ListView({ rows }: { rows: Record<string, unknown>[] }) {
  return (
    <View style={styles.list}>
      {rows.slice(0, 50).map((row, index) => {
        const entries = Object.entries(row).filter(([, value]) => value !== null && value !== undefined).slice(0, 6);
        const title = formatValue(row.nombre || row.nombrecomercial || row.consecutivo || row.id || row.numero_factura || `Registro ${index + 1}`);
        return (
          <View key={`${title}-${index}`} style={styles.rowCard}>
            <Text style={styles.rowTitle} numberOfLines={1}>
              {title}
            </Text>
            {entries.map(([key, value]) => (
              <View key={key} style={styles.fieldRow}>
                <Text style={styles.fieldKey}>{key.replaceAll("_", " ")}</Text>
                <Text style={styles.fieldValue} numberOfLines={2}>
                  {formatValue(value)}
                </Text>
              </View>
            ))}
          </View>
        );
      })}
    </View>
  );
}

function ObjectCards({ obj }: { obj: Record<string, unknown> }) {
  return (
    <View style={styles.list}>
      {Object.entries(obj).slice(0, 30).map(([key, value]) => (
        <View key={key} style={styles.rowCard}>
          <Text style={styles.fieldKey}>{key.replaceAll("_", " ")}</Text>
          <Text style={styles.fieldValue}>{formatValue(value)}</Text>
        </View>
      ))}
    </View>
  );
}

function PrimaryButton({ label, loading, onPress }: { label: string; loading: boolean; onPress: () => void }) {
  return (
    <Pressable style={styles.primaryButton} onPress={onPress} disabled={loading}>
      {loading ? <ActivityIndicator color="white" /> : <Text style={styles.primaryButtonText}>{label}</Text>}
    </Pressable>
  );
}

function AppRoot() {
  const { session, loading } = useAuth();

  if (loading) {
    return (
      <View style={styles.loadingScreen}>
        <ActivityIndicator color={BLUE} />
      </View>
    );
  }

  return session ? <Shell /> : <LoginScreen />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoot />
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  app: { flex: 1, backgroundColor: "#F5F7FA" },
  barFill: { backgroundColor: BLUE, borderRadius: 999, height: 10 },
  barLabel: { color: "#475467", fontSize: 12, marginBottom: 5 },
  barRow: { marginTop: 10 },
  barTrack: { backgroundColor: "#E4EAF2", borderRadius: 999, height: 10, overflow: "hidden" },
  brand: { color: BLUE, fontSize: 28, fontWeight: "800", marginBottom: 8, textAlign: "center" },
  cardTitle: { color: "#101828", fontSize: 15, fontWeight: "800" },
  chart: { backgroundColor: "white", borderColor: BORDER, borderRadius: 8, borderWidth: 1, marginTop: 12, padding: 14 },
  content: { flex: 1 },
  contentInner: { padding: 14, paddingBottom: 32 },
  dashboardBarLabel: { color: "#344054", flex: 1, fontSize: 12, fontWeight: "800" },
  dashboardBarRow: { marginTop: 12 },
  dashboardBarTop: { alignItems: "center", flexDirection: "row", gap: 8, justifyContent: "space-between", marginBottom: 6 },
  dashboardBarValue: { color: BLUE, fontSize: 12, fontWeight: "900" },
  dashboardFilters: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 12,
    padding: 12
  },
  dashboardHeader: {
    alignItems: "center",
    flexDirection: "row",
    gap: 12,
    justifyContent: "space-between"
  },
  dashboardTitle: { color: "#101828", flex: 1, fontSize: 20, fontWeight: "900" },
  empty: { color: "#697386", fontSize: 15, marginTop: 16 },
  error: { color: "#B42318", fontSize: 14, marginTop: 14 },
  delayBox: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 12,
    padding: 12
  },
  delayHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  fieldKey: { color: "#667085", flex: 1, fontSize: 12, fontWeight: "700", textTransform: "capitalize" },
  fieldRow: { flexDirection: "row", gap: 10, marginTop: 6 },
  fieldValue: { color: "#1D2939", flex: 1.3, fontSize: 12, textAlign: "right" },
  financeFilterActions: { flexDirection: "row", gap: 10, marginTop: 2 },
  financeFilterBox: {
    backgroundColor: "#F8FAFC",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 12,
    padding: 12
  },
  headerButton: { borderColor: "white", borderRadius: 6, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 8 },
  headerButtonText: { color: "white", fontSize: 13, fontWeight: "700" },
  headerSub: { color: "#D8E7F8", fontSize: 12, marginTop: 2 },
  headerTitle: { color: "white", fontSize: 20, fontWeight: "800" },
  input: {
    borderColor: BORDER,
    borderRadius: 6,
    borderWidth: 1,
    fontSize: 16,
    marginBottom: 14,
    paddingHorizontal: 12,
    paddingVertical: 11
  },
  kpiCard: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    flexBasis: "48%",
    padding: 12
  },
  kpiGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginTop: 10 },
  kpiLabel: { color: "#667085", fontSize: 11, fontWeight: "700", textTransform: "capitalize" },
  kpiValue: { color: BLUE, fontSize: 22, fontWeight: "900", marginTop: 6 },
  label: { color: "#344054", fontSize: 13, fontWeight: "700", marginBottom: 6 },
  list: { marginTop: 12 },
  loader: { marginTop: 16 },
  loadingScreen: { alignItems: "center", flex: 1, justifyContent: "center" },
  loginLogo: { alignSelf: "center", height: 82, marginBottom: 10, width: 82 },
  loginWrap: { flexGrow: 1, justifyContent: "center", padding: 22 },
  moduleTab: {
    backgroundColor: "rgba(255,255,255,0.12)",
    borderColor: "rgba(255,255,255,0.35)",
    borderRadius: 999,
    borderWidth: 1,
    marginRight: 8,
    paddingHorizontal: 14,
    paddingVertical: 9
  },
  moduleTabActive: { backgroundColor: "white" },
  moduleTabText: { color: "white", fontSize: 13, fontWeight: "800" },
  moduleTabTextActive: { color: BLUE },
  moduleTabs: { paddingHorizontal: 14, paddingTop: 10 },
  moduleTitle: { color: "#101828", fontSize: 21, fontWeight: "800", marginBottom: 12 },
  panel: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    padding: 18
  },
  primaryButton: { alignItems: "center", backgroundColor: BLUE, borderRadius: 6, marginTop: 6, paddingVertical: 13 },
  primaryButtonText: { color: "white", fontSize: 15, fontWeight: "800" },
  qr: { alignSelf: "center", height: 220, marginBottom: 16, width: 220 },
  rememberRow: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 12 },
  rememberText: { color: "#344054", fontSize: 13, fontWeight: "700" },
  rowCard: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 10,
    padding: 12
  },
  rowTitle: { color: "#101828", fontSize: 15, fontWeight: "800", marginBottom: 4 },
  screen: { flex: 1, backgroundColor: "#F5F7FA" },
  secondaryButton: { alignItems: "center", borderColor: BLUE, borderRadius: 6, borderWidth: 1, marginTop: 10, paddingVertical: 12 },
  secondaryButtonText: { color: BLUE, fontSize: 14, fontWeight: "800" },
  smallDangerButton: { alignItems: "center", backgroundColor: "#F4CCCC", borderRadius: 4, height: 28, justifyContent: "center", width: 32 },
  smallDangerButtonText: { color: "#7A271A", fontSize: 13, fontWeight: "900" },
  actionBar: { gap: 8, paddingVertical: 12 },
  actionButton: { backgroundColor: BLUE, borderRadius: 6, paddingHorizontal: 12, paddingVertical: 10 },
  actionButtonText: { color: "white", fontSize: 12, fontWeight: "800" },
  accountingTcBox: {
    backgroundColor: "#F8FAFC",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 10,
    padding: 10
  },
  accountingTcFields: { flexDirection: "row", gap: 10 },
  accountingTcItem: { flex: 1 },
  formField: { marginBottom: 8 },
  helperText: { color: "#667085", fontSize: 13, fontWeight: "700", marginBottom: 12 },
  modalBody: { padding: 16, paddingBottom: 36 },
  modalClose: { borderColor: BLUE, borderRadius: 6, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 8 },
  modalCloseText: { color: BLUE, fontSize: 13, fontWeight: "800" },
  modalHeader: {
    alignItems: "center",
    borderBottomColor: BORDER,
    borderBottomWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    padding: 14
  },
  modalScreen: { backgroundColor: "#F5F7FA", flex: 1 },
  modalTitle: { color: "#101828", flex: 1, fontSize: 18, fontWeight: "800", paddingRight: 10 },
  multilineInput: { minHeight: 110, textAlignVertical: "top" },
  readonlyInput: { backgroundColor: "#EEF2F6", color: "#344054" },
  optionItem: { borderBottomColor: BORDER, borderBottomWidth: 1, paddingHorizontal: 10, paddingVertical: 10 },
  optionList: { backgroundColor: "white", borderColor: BORDER, borderRadius: 6, borderWidth: 1, marginBottom: 10 },
  optionScroll: { maxHeight: 180 },
  optionText: { color: "#101828", fontSize: 13, fontWeight: "700" },
  selectBox: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 6,
    borderWidth: 1,
    marginBottom: 10,
    paddingHorizontal: 12,
    paddingVertical: 12
  },
  selectText: { color: "#101828", fontSize: 14, fontWeight: "700" },
  summaryBox: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 14,
    padding: 12
  },
  reportBox: {
    backgroundColor: "#F8FAFC",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 12,
    marginTop: 4,
    padding: 10
  },
  sectionTab: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 999,
    borderWidth: 1,
    marginRight: 8,
    paddingHorizontal: 12,
    paddingVertical: 9
  },
  sectionTabActive: { backgroundColor: BLUE, borderColor: BLUE },
  sectionTabs: { paddingBottom: 4 },
  sectionText: { color: "#344054", fontSize: 12, fontWeight: "800" },
  sectionTextActive: { color: "white" },
  tableCell: {
    borderRightColor: BORDER,
    borderRightWidth: 1,
    color: "#101828",
    fontSize: 11,
    paddingHorizontal: 8,
    paddingVertical: 9,
    width: 132
  },
  tableCount: { color: "#667085", fontSize: 12, fontWeight: "800" },
  tableHeader: { backgroundColor: BLUE, flexDirection: "row" },
  tableHeaderCell: {
    borderRightColor: "rgba(255,255,255,0.25)",
    borderRightWidth: 1,
    color: "white",
    fontSize: 11,
    fontWeight: "900",
    paddingHorizontal: 8,
    paddingVertical: 10,
    textTransform: "capitalize",
    width: 132
  },
  tableRow: { backgroundColor: "white", borderBottomColor: BORDER, borderBottomWidth: 1, flexDirection: "row" },
  tableRows: { maxHeight: 430 },
  tableRowSelected: { backgroundColor: "#E8F1FC" },
  tableSearch: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 6,
    borderWidth: 1,
    flex: 1,
    fontSize: 14,
    paddingHorizontal: 10,
    paddingVertical: 9
  },
  tableShell: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 12,
    overflow: "hidden",
    padding: 10
  },
  tableToolbar: { alignItems: "center", flexDirection: "row", gap: 10, marginBottom: 10 },
  subtitle: { color: "#101828", fontSize: 18, fontWeight: "800", marginBottom: 14 },
  title: { color: "#101828", fontSize: 22, fontWeight: "800", marginBottom: 16, textAlign: "center" },
  top: { backgroundColor: BLUE, paddingBottom: 12 },
  topRow: {
    alignItems: "center",
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingTop: 12
  }
});

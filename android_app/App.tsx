import * as LocalAuthentication from "expo-local-authentication";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
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

  useEffect(() => {
    if (activeModule?.code !== "informes" || activeSection || !session) return;
    const statusSection = activeModule.sections.find((section) => section.key === "status-informes");
    if (statusSection) openSection(statusSection);
  }, [activeModule, activeSection, session]);

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
            {activeModule.code !== "informes" ? (
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
            ) : null}

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

  if (moduleCode === "hhrre" && section) {
    return <HHRRSectionMobile section={section} initialPayload={payload} session={session} />;
  }

  if (moduleCode === "comercial" && section) {
    return <ComercialSectionMobile section={section} initialPayload={payload} session={session} />;
  }

  if (moduleCode === "informes" && section) {
    return <InformesSectionMobile section={section} initialPayload={payload} session={session} />;
  }

  if (section?.key === "credit-hold") {
    return <CreditControlMobile clients={rows} session={session} />;
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

function uniqueStrings(rows: Record<string, unknown>[], key: string) {
  return Array.from(new Set(rows.map((row) => formatValue(row[key])).filter((value) => value && value !== "-"))).sort();
}

function displayBase(value: string) {
  return value.replace(/\s+\([^)]*\)$/, "").trim();
}

function comercialAppend(params: URLSearchParams, key: string, value: string) {
  const clean = value.trim();
  if (clean && clean !== "Todos") params.append(key, clean);
}

function buildQuotationText(cliente: string, services: Record<string, unknown>[], idioma: string, validez: string) {
  const days = Number(validez || 15);
  const validDate = new Date();
  validDate.setDate(validDate.getDate() + (Number.isFinite(days) ? days : 15));
  const validYmd = validDate.toISOString().slice(0, 10);
  const servicesText = services.map((item) => `- ${formatValue(item.servicio)}: $ ${Number(item.precio || 0).toFixed(2)} USD`).join("\n");
  const total = services.reduce((sum, item) => sum + Number(item.precio || 0), 0);
  const name = cliente || (idioma === "EN" ? "Client" : "Cliente");

  if (idioma === "EN") {
    return `Dear ${name},\n\nWe are pleased to submit our quotation for the following services:\n\n${servicesText}\n\nTotal amount: USD ${total.toFixed(2)}\n\nThis quotation is valid until ${validYmd}.\nPayment terms: 30 days from invoice date.\n\nSincerely,\nMarine Surveyors & Logistics Group SRL`;
  }

  return `Estimado ${name},\n\nPor medio de la presente compartimos la cotizacion para los siguientes servicios:\n\n${servicesText}\n\nMonto total: $ ${total.toFixed(2)} USD\n\nEsta cotizacion tiene una validez hasta el ${validYmd}.\nTerminos de pago: 30 dias fecha factura.\n\nAtentamente,\nMarine Surveyors & Logistics Group SRL`;
}

function ComercialSectionMobile({
  section,
  initialPayload,
  session
}: {
  section: AppSection;
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  if (section.key === "board") return <ComercialBoardView initialPayload={initialPayload} session={session} />;
  if (section.key === "clientes-comercial") return <ComercialClientesView initialPayload={initialPayload} session={session} />;
  if (section.key === "precios") return <ComercialPreciosView initialPayload={initialPayload} session={session} />;
  if (section.key === "cotizaciones") return <ComercialCotizacionesView initialPayload={initialPayload} session={session} />;
  if (section.key === "analytics-clientes") return <ComercialClientAnalyticsView initialPayload={initialPayload} session={session} />;
  if (section.key === "analytics-puertos") return <ComercialKpisView title="Analytics Puertos" endpoint="/comercial/analytics/puertos/kpis" initialPayload={initialPayload} session={session} />;
  if (section.key === "analytics-servicios") return <ComercialKpisView title="Analytics Servicios" endpoint="/comercial/analytics/servicios/kpis" initialPayload={initialPayload} session={session} />;
  return <ListView rows={rowsFromAny(initialPayload)} />;
}

function ComercialBoardView({
  initialPayload,
  session
}: {
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const currentYear = String(new Date().getFullYear());
  const [rows, setRows] = useState(rowsFromAny(initialPayload));
  const [selected, setSelected] = useState<number | null>(null);
  const [filters, setFilters] = useState({
    cliente: "",
    pais: "",
    puerto: "",
    surveyor: "",
    year: "",
    confirmado: true,
    operacion: true,
    finalizado: false,
    cancelado: false
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = [
    "consec",
    "tipo",
    "estado",
    "num_informe",
    "buque_contenedor",
    "cliente",
    "operacion",
    "detalle",
    "surveyor",
    "continente",
    "pais",
    "puerto",
    "fecha_inicio",
    "hora_inicio",
    "fecha_fin",
    "hora_fin",
    "demoras",
    "duracion"
  ];

  async function load() {
    const params = new URLSearchParams();
    comercialAppend(params, "cliente", filters.cliente);
    comercialAppend(params, "pais", filters.pais);
    comercialAppend(params, "puerto", filters.puerto);
    comercialAppend(params, "surveyor", filters.surveyor);
    if (filters.year) params.set("year", filters.year);
    if (filters.confirmado) params.append("estados", "Confirmado");
    if (filters.operacion) params.append("estados", "En Operación");
    if (filters.finalizado) params.append("estados", "FINALIZADO");
    if (filters.cancelado) params.append("estados", "Cancelado");
    if (!params.has("estados") && !params.toString()) {
      params.append("estados", "Confirmado");
      params.append("estados", "En Operación");
    }

    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest(`/comercial/board?${params.toString()}`, { session });
      const nextRows = rowsFromAny(payload).sort((a, b) => Number(b.consec || 0) - Number(a.consec || 0));
      setRows(nextRows);
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar pizarra comercial.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, [session.usuario, session.rol]);

  const years = Array.from(new Set([currentYear, ...rows.map((row) => String(formatValue(row.fecha_inicio)).slice(0, 4)).filter((year) => /^\d{4}$/.test(year))])).sort().reverse();

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Comercial - Pizarra Operativa</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Cliente" value={filters.cliente} options={["", ...uniqueStrings(rows, "cliente")]} onChange={(cliente) => setFilters((f) => ({ ...f, cliente }))} />
        <SelectField label="Pais" value={filters.pais} options={["", ...uniqueStrings(rows, "pais")]} onChange={(pais) => setFilters((f) => ({ ...f, pais }))} />
        <SelectField label="Puerto" value={filters.puerto} options={["", ...uniqueStrings(rows, "puerto")]} onChange={(puerto) => setFilters((f) => ({ ...f, puerto }))} />
        <SelectField label="Surveyor" value={filters.surveyor} options={["", ...uniqueStrings(rows, "surveyor")]} onChange={(surveyor) => setFilters((f) => ({ ...f, surveyor }))} />
        <SelectField label="Anio" value={filters.year} options={["", ...years]} onChange={(year) => setFilters((f) => ({ ...f, year }))} />
        <View style={styles.commercialStatusRow}>
          {[
            ["confirmado", "Confirmado"],
            ["operacion", "En Operación"],
            ["finalizado", "Finalizado"],
            ["cancelado", "Cancelado"]
          ].map(([key, label]) => (
            <Pressable key={key} style={[styles.statusChip, filters[key as keyof typeof filters] ? styles.statusChipActive : null]} onPress={() => setFilters((f) => ({ ...f, [key]: !f[key as keyof typeof filters] }))}>
              <Text style={[styles.statusChipText, filters[key as keyof typeof filters] ? styles.statusChipTextActive : null]}>{label}</Text>
            </Pressable>
          ))}
        </View>
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => setFilters({ cliente: "", pais: "", puerto: "", surveyor: "", year: "", confirmado: true, operacion: true, finalizado: false, cancelado: false })}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <Text style={styles.tableCount}>{rows.length} resultados</Text>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
    </View>
  );
}

function ComercialClientesView({
  initialPayload,
  session
}: {
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [rows, setRows] = useState(rowsFromAny(initialPayload));
  const [selected, setSelected] = useState<number | null>(null);
  const [filters, setFilters] = useState({ codigo: "", nombre: "" });
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = ["id", "codigo", "nombrecomercial", "nombrejuridico", "pais", "telefono", "correo", "contacto_principal", "fecha_pago"];
  const selectedRow = selected === null ? null : rows[selected] || null;

  async function load() {
    const params = new URLSearchParams();
    comercialAppend(params, "codigo", filters.codigo);
    comercialAppend(params, "nombre", filters.nombre);
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest(`/comercial/clientes${params.toString() ? `?${params.toString()}` : ""}`, { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
      setDetail(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar clientes.");
    } finally {
      setBusy(false);
    }
  }

  async function showDetail() {
    if (!selectedRow) {
      setMessage("Seleccione un cliente.");
      return;
    }
    const id = formatValue(selectedRow.id);
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest(`/comercial/clientes?id=${encodeURIComponent(id)}`, { session });
      setDetail(rowsFromAny(payload)[0] || selectedRow);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo ver cliente.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Comercial - Clientes</Text>
      <View style={styles.financeFilterBox}>
        <Text style={styles.label}>Codigo</Text>
        <TextInput style={styles.input} value={filters.codigo} onChangeText={(codigo) => setFilters((f) => ({ ...f, codigo }))} />
        <Text style={styles.label}>Nombre</Text>
        <TextInput style={styles.input} value={filters.nombre} onChangeText={(nombre) => setFilters((f) => ({ ...f, nombre }))} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
          <Pressable style={styles.actionButton} onPress={showDetail}><Text style={styles.actionButtonText}>Ver</Text></Pressable>
        </View>
      </View>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      {detail ? (
        <View style={styles.summaryBox}>
          {Object.entries(detail).slice(0, 18).map(([key, value]) => (
            <View key={key} style={styles.fieldRow}>
              <Text style={styles.fieldKey}>{key.replaceAll("_", " ")}</Text>
              <Text style={styles.fieldValue}>{formatValue(value)}</Text>
            </View>
          ))}
        </View>
      ) : null}
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
    </View>
  );
}

function ComercialPreciosView({
  initialPayload,
  session
}: {
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [rows, setRows] = useState(rowsFromAny(initialPayload));
  const [meta, setMeta] = useState<Record<string, unknown>>({});
  const [selected, setSelected] = useState<number | null>(null);
  const [filters, setFilters] = useState({ servicio: "", cliente: "", continente: "", pais: "", puerto: "" });
  const [modalMode, setModalMode] = useState<"add" | "edit" | null>(null);
  const [form, setForm] = useState({ servicio: "", cliente: "", continente: "", pais: "", puerto: "", precio: "", activo: "true" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = ["id", "servicio", "cliente", "continente", "pais", "puerto", "precio", "activo"];
  const selectedRow = selected === null ? null : rows[selected] || null;
  const ubicaciones = (Array.isArray(meta.ubicaciones) ? meta.ubicaciones : []).map((item) => asRecord(item)).filter(Boolean) as Record<string, unknown>[];
  const servicios = (Array.isArray(meta.servicios) ? meta.servicios : []).map((item) => asRecord(item)).filter(Boolean).map((item) => `${formatValue(item?.nombre)} (${formatValue(item?.codigo)})`);
  const clientes = (Array.isArray(meta.clientes) ? meta.clientes : []).map((item) => asRecord(item)).filter(Boolean).map((item) => `${formatValue(item?.nombrejuridico ?? item?.nombre)} (${formatValue(item?.codigo)})`);

  function locationOptions(field: string, source: Record<string, string>) {
    return [
      "",
      ...Array.from(
        new Set(
          ubicaciones
            .filter((row) => (!source.continente || row.continente === source.continente) && (!source.pais || row.pais === source.pais))
            .map((row) => formatValue(row[field]))
            .filter((value) => value !== "-")
        )
      ).sort()
    ];
  }

  async function loadMeta() {
    try {
      const payload = await apiRequest<Record<string, unknown>>("/comercial/precios/meta", { session });
      setMeta(payload || {});
    } catch {
      setMeta({});
    }
  }

  async function load() {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest("/comercial/precios", { session });
      const allRows = rowsFromAny(payload);
      const filtered = allRows.filter((row) => {
        return (!filters.servicio || formatValue(row.servicio) === displayBase(filters.servicio))
          && (!filters.cliente || formatValue(row.cliente) === displayBase(filters.cliente))
          && (!filters.continente || formatValue(row.continente) === filters.continente)
          && (!filters.pais || formatValue(row.pais) === filters.pais)
          && (!filters.puerto || formatValue(row.puerto) === filters.puerto);
      });
      setRows(filtered);
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar precios.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadMeta();
  }, [session.usuario, session.rol]);

  function openPrice(mode: "add" | "edit") {
    if (mode === "edit" && !selectedRow) {
      setMessage("Seleccione un precio.");
      return;
    }
    const source = mode === "edit" ? selectedRow || {} : {};
    setForm({
      servicio: formatValue(source.servicio) === "-" ? "" : formatValue(source.servicio),
      cliente: formatValue(source.cliente) === "-" ? "" : formatValue(source.cliente),
      continente: formatValue(source.continente) === "-" ? "" : formatValue(source.continente),
      pais: formatValue(source.pais) === "-" ? "" : formatValue(source.pais),
      puerto: formatValue(source.puerto) === "-" ? "" : formatValue(source.puerto),
      precio: formatValue(source.precio) === "-" ? "" : formatValue(source.precio),
      activo: String(source.activo ?? true)
    });
    setModalMode(mode);
  }

  async function savePrice() {
    const payload: Record<string, unknown> = {
      servicio: displayBase(form.servicio),
      cliente: displayBase(form.cliente),
      continente: form.continente || null,
      pais: form.pais || null,
      puerto: form.puerto || null,
      precio: Number(form.precio || 0)
    };
    if (modalMode === "edit") payload.activo = form.activo === "true";
    setBusy(true);
    setMessage("");
    try {
      if (modalMode === "add") {
        await apiRequest("/comercial/precios", { method: "POST", body: payload, session });
      } else if (selectedRow) {
        await apiRequest(`/comercial/precios/${selectedRow.id}`, { method: "PUT", body: payload, session });
      }
      setModalMode(null);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar precio.");
    } finally {
      setBusy(false);
    }
  }

  async function deletePrice() {
    if (!selectedRow) {
      setMessage("Seleccione un precio.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/comercial/precios/${selectedRow.id}`, { method: "DELETE", session });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo eliminar precio.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Comercial - Precios</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Servicio" value={filters.servicio} options={["", ...servicios]} onChange={(servicio) => setFilters((f) => ({ ...f, servicio }))} />
        <SelectField label="Cliente" value={filters.cliente} options={["", ...clientes]} onChange={(cliente) => setFilters((f) => ({ ...f, cliente }))} />
        <SelectField label="Continente" value={filters.continente} options={locationOptions("continente", {})} onChange={(continente) => setFilters((f) => ({ ...f, continente, pais: "", puerto: "" }))} />
        <SelectField label="Pais" value={filters.pais} options={locationOptions("pais", { continente: filters.continente })} onChange={(pais) => setFilters((f) => ({ ...f, pais, puerto: "" }))} />
        <SelectField label="Puerto" value={filters.puerto} options={locationOptions("puerto", { continente: filters.continente, pais: filters.pais })} onChange={(puerto) => setFilters((f) => ({ ...f, puerto }))} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => setFilters({ servicio: "", cliente: "", continente: "", pais: "", puerto: "" })}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={() => openPrice("add")}><Text style={styles.actionButtonText}>Agregar</Text></Pressable>
        <Pressable style={styles.actionButton} onPress={() => openPrice("edit")}><Text style={styles.actionButtonText}>Editar</Text></Pressable>
        <Pressable style={styles.modalClose} onPress={deletePrice}><Text style={styles.modalCloseText}>Eliminar</Text></Pressable>
      </ScrollView>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Modal visible={modalMode !== null} animationType="slide" onRequestClose={() => setModalMode(null)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}><Text style={styles.modalTitle}>{modalMode === "add" ? "Agregar Precio" : "Editar Precio"}</Text><Pressable style={styles.modalClose} onPress={() => setModalMode(null)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable></View>
          <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
            <SelectField label="Servicio" value={form.servicio} options={servicios} onChange={(servicio) => setForm((f) => ({ ...f, servicio }))} />
            <SelectField label="Cliente" value={form.cliente} options={clientes} onChange={(cliente) => setForm((f) => ({ ...f, cliente }))} />
            <SelectField label="Continente" value={form.continente} options={locationOptions("continente", {})} onChange={(continente) => setForm((f) => ({ ...f, continente, pais: "", puerto: "" }))} />
            <SelectField label="Pais" value={form.pais} options={locationOptions("pais", { continente: form.continente })} onChange={(pais) => setForm((f) => ({ ...f, pais, puerto: "" }))} />
            <SelectField label="Puerto" value={form.puerto} options={locationOptions("puerto", { continente: form.continente, pais: form.pais })} onChange={(puerto) => setForm((f) => ({ ...f, puerto }))} />
            <Text style={styles.label}>Precio</Text><TextInput keyboardType="decimal-pad" style={styles.input} value={form.precio} onChangeText={(precio) => setForm((f) => ({ ...f, precio }))} />
            {modalMode === "edit" ? <SelectField label="Activo" value={form.activo} options={["true", "false"]} onChange={(activo) => setForm((f) => ({ ...f, activo }))} /> : null}
            <PrimaryButton label="Guardar" loading={busy} onPress={savePrice} />
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function ComercialCotizacionesView({
  initialPayload,
  session
}: {
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [rows, setRows] = useState(rowsFromAny(initialPayload));
  const [meta, setMeta] = useState<Record<string, unknown>>({});
  const [selected, setSelected] = useState<number | null>(null);
  const [filters, setFilters] = useState({ cliente: "", servicio: "", continente: "", pais: "", puerto: "", status: "" });
  const [showNew, setShowNew] = useState(false);
  const [quote, setQuote] = useState({ cliente: "", servicio: "", continente: "", pais: "", puerto: "", idioma: "ES", validez: "15" });
  const [quotationNumber, setQuotationNumber] = useState("");
  const [selectedServices, setSelectedServices] = useState<Record<string, unknown>[]>([]);
  const [previewText, setPreviewText] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = ["id", "quotation_number", "cliente", "servicio", "continente", "pais", "puerto", "precio", "idioma", "validez", "status", "created_at"];
  const selectedRow = selected === null ? null : rows[selected] || null;
  const precios = (Array.isArray(meta.precios) ? meta.precios : []).map((item) => asRecord(item)).filter(Boolean) as Record<string, unknown>[];
  const activePrecios = precios.filter((row) => row.activo !== false);
  const metaClientes = (Array.isArray(meta.clientes) ? meta.clientes : []).map((item) => asRecord(item)).filter(Boolean) as Record<string, unknown>[];
  const metaServicios = (Array.isArray(meta.servicios) ? meta.servicios : []).map((item) => asRecord(item)).filter(Boolean) as Record<string, unknown>[];
  const metaUbicaciones = (Array.isArray(meta.ubicaciones) ? meta.ubicaciones : []).map((item) => asRecord(item)).filter(Boolean) as Record<string, unknown>[];

  function quoteOptions(field: string, source: Record<string, string>) {
    if (!activePrecios.length) {
      if (field === "cliente") return ["", ...metaClientes.map((row) => formatValue(row.nombre)).filter((value) => value !== "-")];
      if (field === "servicio") return ["", ...metaServicios.map((row) => formatValue(row.nombre)).filter((value) => value !== "-")];
      return [
        "",
        ...Array.from(
          new Set(
            metaUbicaciones
              .filter((row) => (!source.continente || row.continente === source.continente) && (!source.pais || row.pais === source.pais))
              .map((row) => formatValue(row[field]))
              .filter((value) => value !== "-")
          )
        ).sort()
      ];
    }

    return [
      "",
      ...Array.from(
        new Set(
          activePrecios
            .filter((row) => (!source.cliente || row.cliente === source.cliente) && (!source.continente || row.continente === source.continente) && (!source.pais || row.pais === source.pais) && (!source.puerto || row.puerto === source.puerto))
            .map((row) => formatValue(row[field]))
            .filter((value) => value !== "-")
        )
      ).sort()
    ];
  }

  async function loadMeta() {
    setMessage("");
    const payload = await apiRequest<Record<string, unknown>>("/comercial/cotizaciones/meta", { session }).catch((err) => {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar catalogos de cotizacion.");
      return null;
    });
    if (payload) {
      setMeta(payload);
    } else {
      const pricesPayload = await apiRequest("/comercial/precios", { session }).catch(() => null);
      const priceRows = rowsFromAny(pricesPayload);
      if (priceRows.length) {
        setMeta({ precios: priceRows });
        setMessage("");
      } else {
        setMeta({});
      }
    }

    const nextNumber = await apiRequest<Record<string, unknown>>("/comercial/cotizaciones/next-quotation-number", { session }).catch(() => null);
    setQuotationNumber(formatValue(nextNumber?.quotation_number) === "-" ? "" : formatValue(nextNumber?.quotation_number));
  }

  async function load() {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => comercialAppend(params, key, value));
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest(`/comercial/cotizaciones${params.toString() ? `?${params.toString()}` : ""}`, { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar cotizaciones.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    loadMeta();
  }, [session.usuario, session.rol]);

  function currentQuoteMatch() {
    return activePrecios.find((row) =>
      row.cliente === quote.cliente
      && row.servicio === quote.servicio
      && (!quote.continente || row.continente === quote.continente)
      && (!quote.pais || row.pais === quote.pais)
      && (!quote.puerto || row.puerto === quote.puerto)
    );
  }

  function refreshPreview(nextServices = selectedServices, nextQuote = quote) {
    setPreviewText(buildQuotationText(nextQuote.cliente, nextServices, nextQuote.idioma, nextQuote.validez));
  }

  function openNewQuote() {
    const blank = { cliente: "", servicio: "", continente: "", pais: "", puerto: "", idioma: "ES", validez: "15" };
    setQuote(blank);
    setSelectedServices([]);
    setPreviewText(buildQuotationText("", [], "ES", "15"));
    setMessage("");
    setShowNew(true);
  }

  function addQuoteService() {
    const match = currentQuoteMatch();
    if (!quote.cliente || !quote.servicio || !match) {
      setMessage("Seleccione cliente, servicio y una combinacion con precio configurado.");
      return;
    }
    const duplicated = selectedServices.some((item) =>
      item.cliente === match.cliente
      && item.servicio === match.servicio
      && item.continente === match.continente
      && item.pais === match.pais
      && item.puerto === match.puerto
    );
    if (duplicated) {
      setMessage("Ese servicio ya fue agregado.");
      return;
    }
    const next = [...selectedServices, match];
    setSelectedServices(next);
    setQuote((current) => {
      const nextQuote = { ...current, servicio: "" };
      refreshPreview(next, nextQuote);
      return nextQuote;
    });
    setMessage("");
  }

  function removeQuoteService(index: number) {
    const next = selectedServices.filter((_, current) => current !== index);
    setSelectedServices(next);
    refreshPreview(next);
  }

  function updateQuoteField(key: keyof typeof quote, value: string) {
    setQuote((current) => {
      const next = { ...current, [key]: value };
      if (["cliente", "idioma", "validez"].includes(key)) {
        setPreviewText(buildQuotationText(next.cliente, selectedServices, next.idioma, next.validez));
      }
      return next;
    });
  }

  async function exportQuote(format: "word" | "pdf") {
    const pendingMatch = currentQuoteMatch();
    const servicesToExport = selectedServices.length ? selectedServices : pendingMatch ? [pendingMatch] : [];
    const textToExport = selectedServices.length ? previewText : buildQuotationText(quote.cliente, servicesToExport, quote.idioma, quote.validez);
    if (!servicesToExport.length) {
      setMessage("Debe agregar al menos un servicio.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>("/comercial/cotizaciones/export-ticket", {
        method: "POST",
        body: {
          quotation_number: quotationNumber,
          cliente: quote.cliente,
          servicio: servicesToExport.map((item) => formatValue(item.servicio)).join(", "),
          idioma: quote.idioma,
          texto: textToExport
        },
        session
      });
      const ticket = formatValue(payload.ticket);
      const params = new URLSearchParams({
        request_user: session.usuario,
        request_role: session.rol,
        ticket
      });
      const url = `${API_BASE_URL}/comercial/cotizaciones/export/${format}?${params.toString()}`;
      const supported = await Linking.canOpenURL(url);
      if (!supported) {
        await Share.share({ message: url });
      } else {
        await Linking.openURL(url);
      }
      setMessage(`Abriendo descarga ${format.toUpperCase()}...`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo abrir la descarga.");
    } finally {
      setBusy(false);
    }
  }

  async function saveQuote() {
    const pendingMatch = currentQuoteMatch();
    const servicesToSave = selectedServices.length ? selectedServices : pendingMatch ? [pendingMatch] : [];
    if (!quote.cliente || !servicesToSave.length) {
      setMessage("Debe seleccionar cliente y agregar al menos un servicio.");
      return;
    }
    const total = servicesToSave.reduce((sum, item) => sum + Number(item.precio || 0), 0);
    const body: Record<string, unknown> = {
      cliente: quote.cliente,
      servicio: servicesToSave.map((item) => formatValue(item.servicio)).join(", "),
      continente: quote.continente || servicesToSave[0]?.continente || null,
      pais: quote.pais || servicesToSave[0]?.pais || null,
      puerto: quote.puerto || servicesToSave[0]?.puerto || null,
      precio: total,
      idioma: quote.idioma,
      validez: Number(quote.validez || 15),
      status: "PENDIENTE"
    };
    servicesToSave.slice(0, 4).forEach((item, index) => {
      body[`servicio_${index + 1}`] = formatValue(item.servicio);
      body[`precio_${index + 1}`] = Number(item.precio || 0);
    });
    setBusy(true);
    setMessage("");
    try {
      await apiRequest("/comercial/cotizaciones", {
        method: "POST",
        body,
        session
      });
      setShowNew(false);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo crear cotizacion.");
    } finally {
      setBusy(false);
    }
  }

  async function updateQuote(status: "APROBADO" | "CANCELADO") {
    if (!selectedRow) {
      setMessage("Seleccione una cotizacion.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/comercial/cotizaciones/${selectedRow.id}`, {
        method: "PUT",
        body: status === "CANCELADO" ? { status, razon_cancelacion: "Cancelada desde app" } : { status },
        session
      });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo actualizar cotizacion.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Comercial - Cotizaciones</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Cliente" value={filters.cliente} options={quoteOptions("cliente", {})} onChange={(cliente) => setFilters((f) => ({ ...f, cliente }))} />
        <SelectField label="Servicio" value={filters.servicio} options={quoteOptions("servicio", { cliente: filters.cliente })} onChange={(servicio) => setFilters((f) => ({ ...f, servicio }))} />
        <SelectField label="Continente" value={filters.continente} options={quoteOptions("continente", { cliente: filters.cliente })} onChange={(continente) => setFilters((f) => ({ ...f, continente, pais: "", puerto: "" }))} />
        <SelectField label="Pais" value={filters.pais} options={quoteOptions("pais", { cliente: filters.cliente, continente: filters.continente })} onChange={(pais) => setFilters((f) => ({ ...f, pais, puerto: "" }))} />
        <SelectField label="Puerto" value={filters.puerto} options={quoteOptions("puerto", { cliente: filters.cliente, continente: filters.continente, pais: filters.pais })} onChange={(puerto) => setFilters((f) => ({ ...f, puerto }))} />
        <SelectField label="Status" value={filters.status} options={["", "PENDIENTE", "APROBADO", "CANCELADO"]} onChange={(status) => setFilters((f) => ({ ...f, status }))} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => setFilters({ cliente: "", servicio: "", continente: "", pais: "", puerto: "", status: "" })}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={openNewQuote}><Text style={styles.actionButtonText}>Nueva Cotizacion</Text></Pressable>
        <Pressable style={styles.actionButton} onPress={() => updateQuote("APROBADO")}><Text style={styles.actionButtonText}>Aprobar</Text></Pressable>
        <Pressable style={styles.modalClose} onPress={() => updateQuote("CANCELADO")}><Text style={styles.modalCloseText}>Cancelar</Text></Pressable>
      </ScrollView>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Modal visible={showNew} animationType="slide" onRequestClose={() => setShowNew(false)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}><Text style={styles.modalTitle}>Nueva Cotizacion</Text><Pressable style={styles.modalClose} onPress={() => setShowNew(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable></View>
          <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
            {quotationNumber ? <Text style={styles.helperText}>{quotationNumber}</Text> : null}
            <SelectField label="Cliente" value={quote.cliente} options={quoteOptions("cliente", {})} onChange={(cliente) => updateQuoteField("cliente", cliente)} />
            <SelectField label="Continente" value={quote.continente} options={quoteOptions("continente", { cliente: quote.cliente })} onChange={(continente) => setQuote((f) => ({ ...f, continente, pais: "", puerto: "", servicio: "" }))} />
            <SelectField label="Pais" value={quote.pais} options={quoteOptions("pais", { cliente: quote.cliente, continente: quote.continente })} onChange={(pais) => setQuote((f) => ({ ...f, pais, puerto: "", servicio: "" }))} />
            <SelectField label="Puerto" value={quote.puerto} options={quoteOptions("puerto", { cliente: quote.cliente, continente: quote.continente, pais: quote.pais })} onChange={(puerto) => setQuote((f) => ({ ...f, puerto, servicio: "" }))} />
            <SelectField label="Servicio" value={quote.servicio} options={quoteOptions("servicio", { cliente: quote.cliente, continente: quote.continente, pais: quote.pais, puerto: quote.puerto })} onChange={(servicio) => updateQuoteField("servicio", servicio)} />
            <Pressable style={styles.secondaryButton} onPress={addQuoteService}><Text style={styles.secondaryButtonText}>Agregar Servicio</Text></Pressable>
            <HRMiniTable rows={selectedServices} columns={["servicio", "precio", "continente", "pais", "puerto"]} selectedIndex={null} onSelect={removeQuoteService} />
            <Text style={styles.helperText}>Toque una linea de servicios cotizados para quitarla.</Text>
            <SelectField label="Idioma" value={quote.idioma} options={["ES", "EN"]} onChange={(idioma) => updateQuoteField("idioma", idioma)} />
            <Text style={styles.label}>Validez dias</Text><TextInput keyboardType="number-pad" style={styles.input} value={quote.validez} onChangeText={(validez) => updateQuoteField("validez", validez)} />
            <Text style={styles.label}>Texto de la Cotizacion</Text>
            <TextInput multiline style={[styles.input, styles.quotationPreviewInput]} value={previewText} onChangeText={setPreviewText} />
            <ScrollView horizontal contentContainerStyle={styles.actionBar}>
              <Pressable style={styles.actionButton} onPress={() => exportQuote("word")}><Text style={styles.actionButtonText}>Exportar WORD</Text></Pressable>
              <Pressable style={styles.actionButton} onPress={() => exportQuote("pdf")}><Text style={styles.actionButtonText}>Exportar PDF</Text></Pressable>
            </ScrollView>
            <PrimaryButton label="Confirmar y Guardar" loading={busy} onPress={saveQuote} />
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function ComercialClientAnalyticsView({
  initialPayload,
  session
}: {
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [data, setData] = useState(initialPayload);
  const [filters, setFilters] = useState({ year: String(new Date().getFullYear()), cliente: "", servicio: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const rows = rowsFromAny(data);
  const obj = asRecord(data) || {};

  async function load() {
    const params = new URLSearchParams();
    comercialAppend(params, "year", filters.year);
    comercialAppend(params, "cliente", filters.cliente);
    comercialAppend(params, "servicio", filters.servicio);
    setBusy(true);
    setMessage("");
    try {
      setData(await apiRequest(`/comercial/client-view?${params.toString()}`, { session }));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar analytics clientes.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Analytics Clientes</Text>
      <View style={styles.financeFilterBox}>
        <Text style={styles.label}>Anio</Text><TextInput keyboardType="number-pad" style={styles.input} value={filters.year} onChangeText={(year) => setFilters((f) => ({ ...f, year }))} />
        <SelectField label="Cliente" value={filters.cliente} options={["", ...uniqueStrings(rows, "cliente")]} onChange={(cliente) => setFilters((f) => ({ ...f, cliente }))} />
        <SelectField label="Servicio" value={filters.servicio} options={["", ...uniqueStrings(rows, "servicios")]} onChange={(servicio) => setFilters((f) => ({ ...f, servicio }))} />
        <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
      </View>
      <KpiGrid numbers={flattenNumbers(obj.kpis).slice(0, 8)} />
      <HRMiniTable rows={rows} columns={["cliente", "servicios", "buque_contenedor", "frecuencia", "valor_facturado", "margen_bruto", "margen_neto", "rentabilidad_pct"]} selectedIndex={null} onSelect={() => undefined} />
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
    </View>
  );
}

function ComercialKpisView({
  title,
  endpoint,
  initialPayload,
  session
}: {
  title: string;
  endpoint: string;
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [data, setData] = useState(initialPayload);
  const [filters, setFilters] = useState({ year_from: String(new Date().getFullYear()), year_to: String(new Date().getFullYear()), continente: "", pais: "", puerto: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const obj = asRecord(data) || {};

  async function load() {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => comercialAppend(params, key, value));
    setBusy(true);
    setMessage("");
    try {
      setData(await apiRequest(`${endpoint}?${params.toString()}`, { session }));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar analytics.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>{title}</Text>
      <View style={styles.financeFilterBox}>
        <Text style={styles.label}>Year from</Text><TextInput keyboardType="number-pad" style={styles.input} value={filters.year_from} onChangeText={(year_from) => setFilters((f) => ({ ...f, year_from }))} />
        <Text style={styles.label}>Year to</Text><TextInput keyboardType="number-pad" style={styles.input} value={filters.year_to} onChangeText={(year_to) => setFilters((f) => ({ ...f, year_to }))} />
        <Text style={styles.label}>Continente</Text><TextInput style={styles.input} value={filters.continente} onChangeText={(continente) => setFilters((f) => ({ ...f, continente }))} />
        <Text style={styles.label}>Pais</Text><TextInput style={styles.input} value={filters.pais} onChangeText={(pais) => setFilters((f) => ({ ...f, pais }))} />
        <Text style={styles.label}>Puerto</Text><TextInput style={styles.input} value={filters.puerto} onChangeText={(puerto) => setFilters((f) => ({ ...f, puerto }))} />
        <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
      </View>
      <KpiGrid numbers={flattenNumbers(obj.kpis || obj).slice(0, 8)} />
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
    </View>
  );
}

type InformeAction = {
  key: string;
  label: string;
  endpoint: string;
  method?: "GET" | "POST" | "PUT";
  body?: Record<string, unknown>;
  file?: boolean;
};

type InformeConfig = {
  title: string;
  idField: string;
  columns: string[];
  detailEndpoint?: string;
  updateEndpoint?: string;
  createEndpoint?: string;
  statusField?: string;
  filters?: string[];
  actions: InformeAction[];
};

type InformeCreateField = {
  key: string;
  label: string;
  type?: "text" | "date" | "datetime" | "multiline" | "checkbox" | "section";
};

type InformeCreateConfig = {
  key: string;
  group: "Informe contenedor" | "Informe buque" | "Certificados";
  title: string;
  endpoint: string;
  dateFormat?: "ymd" | "dmy";
  fields: InformeCreateField[];
};

const INFORMES_CONFIG: Record<string, InformeConfig> = {
  "status-informes": {
    title: "Status Informes",
    idField: "consec",
    detailEndpoint: "/status-informes/record/{id}",
    updateEndpoint: "/status-informes/record/{id}",
    statusField: "status_informe",
    columns: ["consec", "num_informe", "buque_contenedor", "cliente", "operacion", "pais", "puerto", "fecha_inicio", "status_informe"],
    filters: ["status_informe", "cliente", "operacion", "pais", "puerto"],
    actions: []
  },
  container: {
    title: "Informes de Contenedores",
    idField: "id",
    detailEndpoint: "/container-reports/{id}",
    updateEndpoint: "/container-reports/{id}",
    createEndpoint: "/container-reports",
    statusField: "status",
    columns: ["id", "report_number", "no", "customer", "vessel", "port", "date", "status"],
    filters: ["status", "customer", "vessel", "port"],
    actions: [
      { key: "excel", label: "Excel", endpoint: "/container-reports/{id}/excel", file: true },
      { key: "pdf", label: "PDF", endpoint: "/container-reports/{id}/download-pdf", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/container-reports/{id}", method: "PUT", body: { status: "Approved" } },
      { key: "reject", label: "Rechazar", endpoint: "/container-reports/{id}", method: "PUT", body: { status: "Rejected" } }
    ]
  },
  "grain-sampling": {
    title: "Vessel Grain Sampling",
    idField: "id",
    detailEndpoint: "/vessel-grain-sampling/{id}",
    updateEndpoint: "/vessel-grain-sampling/{id}",
    createEndpoint: "/vessel-grain-sampling",
    statusField: "status",
    columns: ["id", "cert_no", "vessel_name", "requested_by", "place_date", "sampling_start_time", "status"],
    filters: ["status", "requested_by", "vessel_name", "cert_no"],
    actions: [
      { key: "word", label: "Word", endpoint: "/vessel-grain-sampling/{id}/generate-word", method: "POST", file: true },
      { key: "approve", label: "Aprobar/PDF", endpoint: "/vessel-grain-sampling/{id}/approve", method: "PUT", file: true },
      { key: "reject", label: "Rechazar", endpoint: "/vessel-grain-sampling/{id}/reject", method: "PUT" },
      { key: "presentation", label: "Presentacion PDF", endpoint: "/vessel-grain-sampling/{id}/presentation-pdf", method: "POST", file: true },
      { key: "unified", label: "Unified PDF", endpoint: "/vessel-grain-sampling/{id}/unified-pdf", method: "POST", file: true }
    ]
  },
  "truck-supervision": {
    title: "Truck Supervision",
    idField: "id",
    detailEndpoint: "/vessel-truck-supervision/{id}",
    updateEndpoint: "/vessel-truck-supervision/{id}",
    createEndpoint: "/vessel-truck-supervision/",
    statusField: "status",
    columns: ["id", "cert_no", "vessel_name", "customer", "port", "report_date", "status"],
    filters: ["status", "customer", "vessel_name", "port", "country", "cert_no"],
    actions: [
      { key: "approve", label: "Aprobar/PDF", endpoint: "/vessel-truck-supervision/{id}/approve", method: "POST", file: true },
      { key: "reject", label: "Rechazar", endpoint: "/vessel-truck-supervision/{id}/reject", method: "PUT" },
      { key: "presentation", label: "Presentacion PDF", endpoint: "/vessel-truck-supervision/{id}/presentation", file: true },
      { key: "unified", label: "Unified PDF", endpoint: "/vessel-truck-supervision/{id}/unified", file: true }
    ]
  },
  "draft-survey": {
    title: "Draft Survey",
    idField: "general_id",
    detailEndpoint: "/draft-survey/{id}",
    updateEndpoint: "/draft-survey/{id}",
    createEndpoint: "/draft-survey/",
    statusField: "status",
    columns: ["general_id", "cert_no", "vessel_name", "client", "port", "country", "survey_date", "status"],
    filters: ["status", "client", "vessel_name", "port", "country"],
    actions: [
      { key: "reject", label: "Rechazar", endpoint: "/draft-survey/{id}", method: "PUT", body: { status: "Rejected" } }
    ]
  },
  bunker: {
    title: "Vessel Bunker",
    idField: "id",
    detailEndpoint: "/vessel-bunker-reports/{id}",
    updateEndpoint: "/vessel-bunker-reports/{id}",
    createEndpoint: "/vessel-bunker-reports/",
    statusField: "status",
    columns: ["id", "bunker_cert_no", "vessel", "client", "port", "country", "attendance_date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "excel", label: "Excel", endpoint: "/vessel-bunker-excel/generate/{id}", file: true },
      { key: "pdf", label: "PDF", endpoint: "/vessel-bunker-excel/generate-pdf/{id}", file: true },
      { key: "presentation", label: "Presentacion", endpoint: "/vessel-bunker-reports/presentation/{id}", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/vessel-bunker-reports/{id}", method: "PUT", body: { status: "Approved" } },
      { key: "reject", label: "Rechazar", endpoint: "/vessel-bunker-reports/{id}", method: "PUT", body: { status: "Rejected" } }
    ]
  },
  "cargo-condition": {
    title: "Cargo Condition Survey",
    idField: "id",
    detailEndpoint: "/vessel-cargo-condition-surveys/{id}",
    updateEndpoint: "/vessel-cargo-condition-surveys/{id}",
    createEndpoint: "/vessel-cargo-condition-surveys/",
    statusField: "status",
    columns: ["id", "report_number", "vessel", "client", "port", "country", "date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "word", label: "Word", endpoint: "/vessel-cargo-condition-surveys/word/{id}", file: true },
      { key: "presentation", label: "Presentacion", endpoint: "/vessel-cargo-condition-surveys/presentation/{id}", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/vessel-cargo-condition-surveys/{id}", method: "PUT", body: { status: "Approved" } },
      { key: "reject", label: "Rechazar", endpoint: "/vessel-cargo-condition-surveys/{id}", method: "PUT", body: { status: "Rejected" } }
    ]
  },
  "crane-inspection": {
    title: "Crane Inspection",
    idField: "id",
    detailEndpoint: "/vessel-crane-inspection/{id}",
    updateEndpoint: "/vessel-crane-inspection/{id}",
    createEndpoint: "/vessel-crane-inspection/",
    statusField: "status",
    columns: ["id", "report_number", "vessel", "client", "port", "country", "inspection_date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "approve", label: "Aprobar", endpoint: "/vessel-crane-inspection/{id}", method: "PUT", body: { status: "Approved" } },
      { key: "reject", label: "Rechazar", endpoint: "/vessel-crane-inspection/{id}", method: "PUT", body: { status: "Rejected" } }
    ]
  },
  "vessel-condition": {
    title: "Vessel Condition Survey",
    idField: "id",
    detailEndpoint: "/vessel-condition-surveys/id/{id}",
    updateEndpoint: "/vessel-condition-surveys/id/{id}",
    createEndpoint: "/vessel-condition-surveys",
    statusField: "status",
    columns: ["id", "report_number", "vessel", "client", "port", "country", "inspection_date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "word", label: "Word", endpoint: "/vessel-condition-surveys/word/{id}", file: true },
      { key: "presentation", label: "Presentacion", endpoint: "/vessel-condition-surveys/presentation/{id}", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/vessel-condition-surveys/id/{id}", method: "PUT", body: { status: "Approved" } },
      { key: "reject", label: "Rechazar", endpoint: "/vessel-condition-surveys/id/{id}", method: "PUT", body: { status: "Rejected" } }
    ]
  },
  "port-captancy": {
    title: "Port Captancy",
    idField: "id",
    detailEndpoint: "/port-captancy-reports/id/{id}",
    updateEndpoint: "/port-captancy-reports/{report_number}",
    createEndpoint: "/port-captancy-reports",
    statusField: "status",
    columns: ["id", "report_number", "vessel", "client", "port", "country", "date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "word", label: "Word", endpoint: "/port-captancy-reports/{id}/word", file: true },
      { key: "presentation", label: "Presentacion", endpoint: "/port-captancy-reports/presentation/{id}", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/port-captancy-reports/{id}", method: "PUT", body: { status: "Approved" } },
      { key: "reject", label: "Rechazar", endpoint: "/port-captancy-reports/{id}", method: "PUT", body: { status: "Rejected" } }
    ]
  },
  "weight-certificate": {
    title: "Weight Certificate",
    idField: "id",
    detailEndpoint: "/weight-certificates/{id}",
    updateEndpoint: "/weight-certificates/{id}",
    createEndpoint: "/weight-certificates",
    statusField: "status",
    columns: ["id", "certificate_no", "vessel", "client", "port", "country", "date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "word", label: "Word", endpoint: "/weight-certificates/{id}/word", file: true },
      { key: "pdf", label: "PDF", endpoint: "/weight-certificates/{id}/pdf", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/weight-certificates/{id}", method: "PUT", body: { status: "approve" } },
      { key: "reject", label: "Rechazar", endpoint: "/weight-certificates/{id}", method: "PUT", body: { status: "reject" } }
    ]
  },
  "holds-certificate": {
    title: "Vessel Holds Inspection Certificate",
    idField: "id",
    detailEndpoint: "/vessel-holds-inspection-certificates/{id}",
    updateEndpoint: "/vessel-holds-inspection-certificates/{id}",
    createEndpoint: "/vessel-holds-inspection-certificates",
    statusField: "status",
    columns: ["id", "certificate_no", "vessel", "client", "port", "country", "date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "excel", label: "Excel", endpoint: "/vessel-holds-inspection-certificates/{id}/excel", file: true },
      { key: "pdf", label: "PDF", endpoint: "/vessel-holds-inspection-certificates/{id}/pdf", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/vessel-holds-inspection-certificates/{id}", method: "PUT", body: { status: "Approve" } },
      { key: "reject", label: "Rechazar", endpoint: "/vessel-holds-inspection-certificates/{id}", method: "PUT", body: { status: "Reject" } }
    ]
  },
  "sampling-certificate": {
    title: "Sampling Certificate",
    idField: "id",
    detailEndpoint: "/sampling-certificates/{id}",
    updateEndpoint: "/sampling-certificates/{id}",
    createEndpoint: "/sampling-certificates",
    statusField: "status",
    columns: ["id", "certificate_no", "vessel", "client", "port", "country", "date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "excel", label: "Excel", endpoint: "/sampling-certificates/{id}/excel", file: true },
      { key: "pdf", label: "PDF", endpoint: "/sampling-certificates/{id}/pdf", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/sampling-certificates/{id}", method: "PUT", body: { status: "Approve" } },
      { key: "reject", label: "Rechazar", endpoint: "/sampling-certificates/{id}", method: "PUT", body: { status: "Reject" } }
    ]
  },
  "sealing-certificate": {
    title: "Sealing Certificate",
    idField: "id",
    detailEndpoint: "/sealing-certificates/{id}",
    updateEndpoint: "/sealing-certificates/{id}",
    createEndpoint: "/sealing-certificates",
    statusField: "status",
    columns: ["id", "certificate_no", "vessel", "client", "port", "country", "date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "excel", label: "Excel", endpoint: "/sealing-certificates/{id}/excel", file: true },
      { key: "pdf", label: "PDF", endpoint: "/sealing-certificates/{id}/pdf", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/sealing-certificates/{id}", method: "PUT", body: { status: "Approve" } },
      { key: "reject", label: "Rechazar", endpoint: "/sealing-certificates/{id}", method: "PUT", body: { status: "Reject" } }
    ]
  },
  "lashing-certificate": {
    title: "Lashing Certificate",
    idField: "id",
    detailEndpoint: "/lashing-certificates/{id}",
    updateEndpoint: "/lashing-certificates/{id}",
    createEndpoint: "/lashing-certificates",
    statusField: "status",
    columns: ["id", "certificate_no", "vessel", "client", "port", "country", "date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "word", label: "Word", endpoint: "/lashing-certificates/{id}/word", file: true },
      { key: "pdf", label: "PDF", endpoint: "/lashing-certificates/{id}/pdf", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/lashing-certificates/{id}", method: "PUT", body: { status: "Approve" } },
      { key: "reject", label: "Rechazar", endpoint: "/lashing-certificates/{id}", method: "PUT", body: { status: "Reject" } }
    ]
  }
};

function endpointForRow(template: string, row: Record<string, unknown>, idField: string) {
  return template.replace(/\{([^}]+)\}/g, (_, rawKey: string) => {
    const key = rawKey === "id" ? idField : rawKey;
    const value = row[key] ?? row[idField] ?? "";
    return encodeURIComponent(formatValue(value));
  });
}

function cleanFilePart(value: string) {
  return value.replace(/[^a-zA-Z0-9._-]+/g, "_").replace(/^_+|_+$/g, "") || "erp_som_file";
}

function extensionForInformeAction(action: InformeAction) {
  const value = `${action.key} ${action.label} ${action.endpoint}`.toLowerCase();
  if (value.includes("xlsx") || value.includes("excel")) return "xlsx";
  if (value.includes("docx") || value.includes("word")) return "docx";
  if (value.includes("pdf") || value.includes("presentation") || value.includes("unified")) return "pdf";
  return "bin";
}

async function downloadSessionFile(
  endpoint: string,
  session: LoginResponse | null | { usuario: string; rol: string },
  filename: string,
  method: "GET" | "POST" | "PUT" = "GET",
  body?: Record<string, unknown>
) {
  const file = new FileSystem.File(FileSystem.Paths.cache, filename);
  const headers: Record<string, string> = session
    ? {
        Accept: "application/octet-stream, application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*",
        "X-User": session.usuario,
        "X-Role": session.rol,
        "X-User-Role": session.rol
      }
    : { Accept: "application/octet-stream, application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*" };
  if (body) headers["Content-Type"] = "application/json";

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined
  });
  const bytes = new Uint8Array(await response.arrayBuffer());

  if (!response.ok) {
    let detail = `Error descargando archivo (${response.status}).`;
    try {
      const text = new TextDecoder().decode(bytes);
      const parsed = JSON.parse(text) as Record<string, unknown>;
      detail = formatValue(parsed.detail || parsed.error || parsed.message || text);
    } catch {
      // Keep the generic download error when the response is not readable JSON.
    }
    throw new Error(detail);
  }

  file.write(bytes);

  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(file.uri);
    return;
  }

  await Linking.openURL(file.uri);
}

function unwrapRecordPayload(payload: unknown) {
  const obj = asRecord(payload);
  if (!obj) return null;
  const data = asRecord(obj.data);
  if (data) return data;
  return obj;
}

const INFORME_REVIEW_OPTIONS = [
  { key: "status-informes", label: "Status de Informes" },
  { key: "container", label: "Informes de contenedores" },
  { key: "grain-sampling", label: "Informe de muestreos de granos" },
  { key: "truck-supervision", label: "Informe Truck Supervision" },
  { key: "draft-survey", label: "Informe Draft Survey" },
  { key: "bunker", label: "Informe Vessel Bunker" },
  { key: "cargo-condition", label: "Informe Cargo Condition Survey" },
  { key: "crane-inspection", label: "Informe Crane Inspection" },
  { key: "vessel-condition", label: "Informe Vessel Condition Survey" },
  { key: "port-captancy", label: "Informe Port Captancy" },
  { key: "weight-certificate", label: "Informe Weight Certificate" },
  { key: "holds-certificate", label: "Informe Vessel Holds Inspection" },
  { key: "sampling-certificate", label: "Informe Sampling Certificate" },
  { key: "sealing-certificate", label: "Informe Sealing Certificate" },
  { key: "lashing-certificate", label: "Informe Lashing Certificate" }
];

const COMMON_REPORT_FIELDS: InformeCreateField[] = [
  { key: "report_number", label: "Num informe" },
  { key: "vessel", label: "Buque" },
  { key: "client", label: "Cliente" },
  { key: "country", label: "Pais" },
  { key: "port", label: "Puerto" },
  { key: "date", label: "Fecha", type: "date" },
  { key: "remarks", label: "Observaciones", type: "multiline" }
];

const CONTAINER_REPORT_FIELDS: InformeCreateField[] = [
  { key: "section_link", label: "Report Link", type: "section" },
  { key: "linked_report_number", label: "Report Number" },
  { key: "linked_service_client", label: "Client" },
  { key: "linked_service_country", label: "Country" },
  { key: "linked_service_port", label: "Port" },
  { key: "linked_service_operation", label: "Operation" },
  { key: "container_type_text", label: "Container Type" },
  { key: "section_general", label: "General Information", type: "section" },
  { key: "report_no", label: "No." },
  { key: "bl", label: "B / L" },
  { key: "seals", label: "Seals" },
  { key: "appointment", label: "Appointment" },
  { key: "shippers", label: "Shippers" },
  { key: "inspection_place", label: "Inspection Place" },
  { key: "contact_person", label: "Contact Person" },
  { key: "on_behalf_of", label: "On Behalf Of" },
  { key: "consignee_notify", label: "Consig./Notify" },
  { key: "vessel", label: "Vessel" },
  { key: "contact_datetime", label: "Contact D/Time", type: "datetime" },
  { key: "init_inspection_datetime", label: "Init Insp. D/Time", type: "datetime" },
  { key: "init_to", label: "To", type: "datetime" },
  { key: "final_inspection_datetime", label: "Final Insp. D/Time", type: "datetime" },
  { key: "final_to", label: "To", type: "datetime" },
  { key: "section_description", label: "Container Description", type: "section" },
  { key: "container_size_20", label: "20 Foot", type: "checkbox" },
  { key: "container_size_40", label: "40 Foot", type: "checkbox" },
  { key: "container_type_dry", label: "Dry", type: "checkbox" },
  { key: "container_type_reefer", label: "Reefer", type: "checkbox" },
  { key: "container_type_iso", label: "ISO Tank", type: "checkbox" },
  { key: "container_type_flat_rack", label: "Flat Rack", type: "checkbox" },
  { key: "container_load_fcl", label: "FCL", type: "checkbox" },
  { key: "container_load_lcl", label: "LCL", type: "checkbox" },
  { key: "section_cause", label: "Cause of Inspection", type: "section" },
  { key: "cause_seals_bl", label: "Seals != BL", type: "checkbox" },
  { key: "cause_change_seals", label: "Change Seals", type: "checkbox" },
  { key: "cause_customs", label: "Customs", type: "checkbox" },
  { key: "cause_transfer", label: "Transfer", type: "checkbox" },
  { key: "cause_leaking", label: "Leaking", type: "checkbox" },
  { key: "cause_damage", label: "Damage", type: "checkbox" },
  { key: "cause_stuff_condition", label: "Stuff / D Condition", type: "checkbox" },
  { key: "cause_detail", label: "Detail of Cause (if necessary)", type: "multiline" },
  { key: "section_goods", label: "Goods & Packages", type: "section" },
  { key: "goods_description", label: "Goods", type: "multiline" },
  { key: "package_carton", label: "Carton", type: "checkbox" },
  { key: "package_bags", label: "Bags", type: "checkbox" },
  { key: "package_boxes", label: "Boxes", type: "checkbox" },
  { key: "package_drums", label: "Drums", type: "checkbox" },
  { key: "package_pallets", label: "Pallets", type: "checkbox" },
  { key: "package_bulk", label: "Bulk", type: "checkbox" },
  { key: "package_bales", label: "Bales", type: "checkbox" },
  { key: "package_crates", label: "Crates", type: "checkbox" },
  { key: "package_other", label: "Other", type: "checkbox" },
  { key: "qty_1_left", label: "Qty 1st Left" },
  { key: "qty_1_right", label: "Qty 1st Right" },
  { key: "qty_2_left", label: "Qty 2nd Left" },
  { key: "qty_2_right", label: "Qty 2nd Right" },
  { key: "qty_3_left", label: "Qty 3rd Left" },
  { key: "qty_3_right", label: "Qty 3rd Right" },
  { key: "package_marking", label: "Package & Marking Description", type: "multiline" },
  { key: "goods_condition", label: "Goods Condition", type: "multiline" },
  { key: "section_narratives", label: "Conditions and Narratives", type: "section" },
  { key: "damage_details", label: "Details of Damage / Shortage", type: "multiline" },
  { key: "remarks", label: "Remarks", type: "multiline" },
  { key: "conclusion", label: "Conclusion", type: "multiline" },
  { key: "picture_link", label: "Picture Link" },
  { key: "section_docs", label: "Collected Documents", type: "section" },
  { key: "doc_bl", label: "B/L", type: "checkbox" },
  { key: "doc_packing_list", label: "Packing List", type: "checkbox" },
  { key: "doc_shipping_invoice", label: "Shipping Invoice", type: "checkbox" },
  { key: "doc_cargo_manifest", label: "Cargo Manifest", type: "checkbox" },
  { key: "doc_commercial_invoice", label: "Commercial Invoice", type: "checkbox" },
  { key: "doc_delivery_record", label: "Delivery / Received Record", type: "checkbox" },
  { key: "doc_notice_loss", label: "Notice of Loss / Damage", type: "checkbox" },
  { key: "doc_insurance_policy", label: "Insurance Policy", type: "checkbox" },
  { key: "doc_other", label: "Other", type: "checkbox" },
  { key: "section_quality", label: "Quality", type: "section" },
  { key: "quality_packing_exam", label: "Packing Examination", type: "checkbox" },
  { key: "quality_un_witness", label: "UN / Stuffed Witness", type: "checkbox" },
  { key: "quality_visual_exam", label: "Visual Examination", type: "checkbox" },
  { key: "quality_product_exam", label: "Product Examination", type: "checkbox" },
  { key: "quality_documents", label: "Quality Documents", type: "checkbox" },
  { key: "quality_sanitary_cert", label: "Sanitary Certificate", type: "checkbox" },
  { key: "quality_phytosanitary_cert", label: "Phytosanitary Cert.", type: "checkbox" },
  { key: "quality_factory_cert", label: "Factory Certificate", type: "checkbox" },
  { key: "quality_origin_cert", label: "Certificate of Origin", type: "checkbox" },
  { key: "section_persons", label: "Persons Present at Survey", type: "section" },
  { key: "person_1_name", label: "Person 1 Name" },
  { key: "person_1_position", label: "Person 1 Position" },
  { key: "person_2_name", label: "Person 2 Name" },
  { key: "person_2_position", label: "Person 2 Position" },
  { key: "person_3_name", label: "Person 3 Name" },
  { key: "person_3_position", label: "Person 3 Position" },
  { key: "section_inspected", label: "Inspected Container", type: "section" },
  { key: "ic_manuf", label: "Manuf. No." },
  { key: "ic_csc", label: "CSC Saf. Apr." },
  { key: "ic_max_gw", label: "Max. Gross Weight (Kgs)" },
  { key: "ic_tare", label: "Tare (Kgs)" },
  { key: "section_details", label: "General Details", type: "section" },
  { key: "new_commodity", label: "New Commodity", type: "checkbox" },
  { key: "used_commodity", label: "Used Commodity", type: "checkbox" },
  { key: "net_weight", label: "Net W. (Kgs)" },
  { key: "gross_weight", label: "Gross W. (Kgs)" },
  { key: "volume", label: "Volume (m3)" },
  { key: "section_transfer", label: "Transfer To Container", type: "section" },
  { key: "tr_number", label: "Number" },
  { key: "tr_manuf", label: "Manuf. No." },
  { key: "tr_csc", label: "CSC Saf. Apr." },
  { key: "tr_seal", label: "Seal No." },
  { key: "tr_max_gw", label: "Max. Gross Weight (Kgs)" },
  { key: "tr_tare", label: "Tare (Kgs)" },
  { key: "section_scope", label: "Scope of Inspection", type: "section" },
  { key: "scope_100", label: "100%", type: "checkbox" },
  { key: "scope_random", label: "Random", type: "checkbox" },
  { key: "scope_items", label: "No. Items" }
];

const GRAIN_SAMPLING_FIELDS: InformeCreateField[] = [
  { key: "section_selector", label: "Report Header", type: "section" },
  { key: "cert_no", label: "CERT No." },
  { key: "service_port", label: "Puerto" },
  { key: "service_country", label: "Pais" },
  { key: "place_date", label: "Fecha", type: "date" },
  { key: "section_main", label: "Main Information", type: "section" },
  { key: "vessel_name", label: "Buque" },
  { key: "requested_by", label: "Cliente" },
  { key: "captain", label: "Capitan" },
  { key: "chief_officer", label: "Primer Oficial" },
  { key: "section_ship", label: "2. BUQUE", type: "section" },
  { key: "ship_flag", label: "2.2 Bandera / Puerto de Registro" },
  { key: "ship_grt", label: "2.3 GRT" },
  { key: "ship_nrt", label: "2.4 NRT" },
  { key: "ship_imo", label: "2.5 IMO No." },
  { key: "ship_year", label: "2.6 Anio de Construccion" },
  { key: "section_times", label: "3. TIEMPOS", type: "section" },
  { key: "arrival_buoy_time", label: "3.1 Arribo Boya de Mar", type: "datetime" },
  { key: "nor_tendered_time", label: "3.2 N.O.R Tendered", type: "datetime" },
  { key: "holds_opening_time", label: "3.3 Apertura de Bodegas", type: "datetime" },
  { key: "surveyors_onboard_time", label: "3.4 Surveyors a bordo", type: "datetime" },
  { key: "seals_verification_time", label: "3.5 Verificacion de Sellos", type: "datetime" },
  { key: "sampling_start_time", label: "3.6 Inicio de Muestreo", type: "datetime" },
  { key: "sampling_end_time", label: "3.7 Finalizacion Muestreo", type: "datetime" },
  { key: "surveyors_disembark_time", label: "3.8 Surveyors Desembarcando", type: "datetime" },
  { key: "section_products", label: "PRODUCTOS", type: "section" },
  { key: "products_total", label: "Tonelaje Total (MT)" },
  { key: "hold1_product", label: "Bodega 1 Producto" },
  { key: "hold1_tonnage", label: "Bodega 1 Tonelaje (MT)" },
  { key: "hold2_product", label: "Bodega 2 Producto" },
  { key: "hold2_tonnage", label: "Bodega 2 Tonelaje (MT)" },
  { key: "hold3_product", label: "Bodega 3 Producto" },
  { key: "hold3_tonnage", label: "Bodega 3 Tonelaje (MT)" },
  { key: "hold4_product", label: "Bodega 4 Producto" },
  { key: "hold4_tonnage", label: "Bodega 4 Tonelaje (MT)" },
  { key: "hold5_product", label: "Bodega 5 Producto" },
  { key: "hold5_tonnage", label: "Bodega 5 Tonelaje (MT)" },
  { key: "section_sampling", label: "4. TOMA DE MUESTRAS", type: "section" },
  { key: "supervision", label: "Fecha Supervision", type: "datetime" },
  { key: "sample1_hold", label: "Bodega Muestreo 1" },
  { key: "sample1_proa_babor", label: "M1 Proa Babor" },
  { key: "sample1_proa_estribor", label: "M1 Proa Estribor" },
  { key: "sample1_centro", label: "M1 Centro" },
  { key: "sample1_popa_babor", label: "M1 Popa Babor" },
  { key: "sample1_popa_estribor", label: "M1 Popa Estribor" },
  { key: "sample2_hold", label: "Bodega Muestreo 2" },
  { key: "sample2_proa_babor", label: "M2 Proa Babor" },
  { key: "sample2_proa_estribor", label: "M2 Proa Estribor" },
  { key: "sample2_centro", label: "M2 Centro" },
  { key: "sample2_popa_babor", label: "M2 Popa Babor" },
  { key: "sample2_popa_estribor", label: "M2 Popa Estribor" },
  { key: "sample3_hold", label: "Bodega Muestreo 3" },
  { key: "sample3_proa_babor", label: "M3 Proa Babor" },
  { key: "sample3_proa_estribor", label: "M3 Proa Estribor" },
  { key: "sample3_centro", label: "M3 Centro" },
  { key: "sample3_popa_babor", label: "M3 Popa Babor" },
  { key: "sample3_popa_estribor", label: "M3 Popa Estribor" },
  { key: "section_conclusion", label: "Conclusion", type: "section" },
  { key: "conclusion", label: "Conclusion", type: "multiline" }
];

const TRUCK_SUPERVISION_FIELDS: InformeCreateField[] = [
  { key: "section_header", label: "Report Header", type: "section" },
  { key: "cert_no", label: "CERT No." },
  { key: "customer", label: "Customer" },
  { key: "port", label: "Puerto" },
  { key: "country", label: "Pais" },
  { key: "report_date", label: "Fecha", type: "date" },
  { key: "section_ship", label: "2. BUQUE", type: "section" },
  { key: "vessel_name", label: "Nombre" },
  { key: "flag_port_registry", label: "Bandera / Puerto Registro" },
  { key: "grt", label: "GRT" },
  { key: "nrt", label: "NRT" },
  { key: "imo_no", label: "IMO No." },
  { key: "build_year", label: "Anio Construccion" },
  { key: "section_representatives", label: "Representantes", type: "section" },
  { key: "captain", label: "Capitan" },
  { key: "chief_officer", label: "Primer Oficial" },
  { key: "section_times", label: "Tiempos", type: "section" },
  { key: "arrival_date", label: "Fecha Arribo", type: "date" },
  { key: "inspection_date", label: "Fecha Inspeccion", type: "date" },
  { key: "supervision_completed_date", label: "Supervision Completada", type: "date" },
  { key: "section_process", label: "4. Proceso de Supervision", type: "section" },
  { key: "process_text", label: "Proceso de Supervision", type: "multiline" },
  { key: "section_findings", label: "5. Hallazgos", type: "section" },
  { key: "findings_documental_text", label: "5.1 Hallazgos Documentales", type: "multiline" },
  { key: "findings_operational_text", label: "5.2 Hallazgos de Control Operativo", type: "multiline" },
  { key: "incidents_text", label: "5.3 Incidentes", type: "multiline" },
  { key: "section_conclusion", label: "6. Conclusion", type: "section" },
  { key: "conclusion_text", label: "Conclusion", type: "multiline" }
];

const INFORMES_CREATE_CONFIG: InformeCreateConfig[] = [
  {
    key: "container",
    group: "Informe contenedor",
    title: "Informe de Contenedor",
    endpoint: "/container-reports",
    fields: CONTAINER_REPORT_FIELDS
  },
  {
    key: "grain-sampling",
    group: "Informe buque",
    title: "Muestreo de Granos",
    endpoint: "/vessel-grain-sampling",
    dateFormat: "dmy",
    fields: GRAIN_SAMPLING_FIELDS
  },
  {
    key: "truck-supervision",
    group: "Informe buque",
    title: "Truck Supervision",
    endpoint: "/vessel-truck-supervision/",
    dateFormat: "dmy",
    fields: TRUCK_SUPERVISION_FIELDS
  },
  { key: "draft-survey", group: "Informe buque", title: "Draft Survey", endpoint: "/draft-survey/", fields: COMMON_REPORT_FIELDS },
  { key: "bunker", group: "Informe buque", title: "Vessel Bunker", endpoint: "/vessel-bunker-reports/", fields: COMMON_REPORT_FIELDS },
  { key: "cargo-condition", group: "Informe buque", title: "Cargo Condition Survey", endpoint: "/vessel-cargo-condition-surveys/", fields: COMMON_REPORT_FIELDS },
  { key: "crane-inspection", group: "Informe buque", title: "Crane Inspection", endpoint: "/vessel-crane-inspection/", fields: COMMON_REPORT_FIELDS },
  { key: "vessel-condition", group: "Informe buque", title: "Vessel Condition Survey", endpoint: "/vessel-condition-surveys", fields: COMMON_REPORT_FIELDS },
  { key: "port-captancy", group: "Informe buque", title: "Port Captancy", endpoint: "/port-captancy-reports", fields: COMMON_REPORT_FIELDS },
  { key: "weight-certificate", group: "Certificados", title: "Weight Certificate", endpoint: "/weight-certificates", fields: COMMON_REPORT_FIELDS },
  { key: "holds-certificate", group: "Certificados", title: "Holds Inspection Certificate", endpoint: "/vessel-holds-inspection-certificates", fields: COMMON_REPORT_FIELDS },
  { key: "sampling-certificate", group: "Certificados", title: "Sampling Certificate", endpoint: "/sampling-certificates", fields: COMMON_REPORT_FIELDS },
  { key: "sealing-certificate", group: "Certificados", title: "Sealing Certificate", endpoint: "/sealing-certificates", fields: COMMON_REPORT_FIELDS },
  { key: "lashing-certificate", group: "Certificados", title: "Lashing Certificate", endpoint: "/lashing-certificates", fields: COMMON_REPORT_FIELDS }
];

function toDmy(value: string) {
  const parsed = parseYmd(value);
  if (!parsed) return value;
  return `${String(parsed.getDate()).padStart(2, "0")}-${String(parsed.getMonth() + 1).padStart(2, "0")}-${parsed.getFullYear()}`;
}

function InformesSectionMobile({
  section,
  initialPayload,
  session
}: {
  section: AppSection;
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [activeKey, setActiveKey] = useState(section.key);
  const activeOption = INFORME_REVIEW_OPTIONS.find((option) => option.key === activeKey) || INFORME_REVIEW_OPTIONS[0];
  const config = INFORMES_CONFIG[activeKey] || {
    title: activeOption.label || section.label,
    idField: "id",
    columns: rowsFromAny(initialPayload)[0] ? Object.keys(rowsFromAny(initialPayload)[0]).slice(0, 8) : ["id", "status"],
    actions: []
  };
  const activeSection = {
    key: activeKey,
    label: activeOption.label,
    endpoint: section.key === activeKey ? section.endpoint : undefined
  };
  const [rows, setRows] = useState(rowsFromAny(initialPayload));
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [detailForm, setDetailForm] = useState<Record<string, string>>({});
  const [filters, setFilters] = useState({
    status: "",
    search: "",
    continente: "",
    pais: "",
    puerto: "",
    operacion: "",
    year: "",
    month: ""
  });
  const [generateOpen, setGenerateOpen] = useState(false);
  const [generateGroup, setGenerateGroup] = useState<InformeCreateConfig["group"] | null>(null);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [calculatorOpen, setCalculatorOpen] = useState(false);
  const [createConfig, setCreateConfig] = useState<InformeCreateConfig | null>(null);
  const [createForm, setCreateForm] = useState<Record<string, string>>({});
  const [containerSelectorOpen, setContainerSelectorOpen] = useState(false);
  const [grainSelectorOpen, setGrainSelectorOpen] = useState(false);
  const [truckSelectorOpen, setTruckSelectorOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const statusOptions = ["", "Pending", "Pending for review", "Approved", "Rejected", "Approve", "Reject"];

  const visibleRows = rows.filter((row) => {
    const statusField = config.statusField || "status";
    if (filters.status && formatValue(row[statusField]) !== filters.status) return false;
    for (const field of ["continente", "pais", "puerto", "operacion"]) {
      if (filters[field as keyof typeof filters] && formatValue(row[field]).toLowerCase() !== filters[field as keyof typeof filters].toLowerCase()) return false;
    }
    if (filters.year && formatValue(row.year) !== filters.year) return false;
    if (filters.month && formatValue(row.month) !== filters.month) return false;
    if (!filters.search.trim()) return true;
    const needle = filters.search.toLowerCase();
    const fields = config.filters?.length ? config.filters : config.columns;
    return fields.some((field) => formatValue(row[field]).toLowerCase().includes(needle));
  });
  const selectedRow = selected === null ? null : visibleRows[selected] || null;
  async function load() {
    const endpoint = getInformeEndpoint(activeKey, section, activeSection);
    if (!endpoint) return;
    const params = new URLSearchParams();
    if (filters.status && activeKey === "status-informes") params.set("status", filters.status);
    if (activeKey === "status-informes") {
      if (filters.continente) params.set("continente", filters.continente);
      if (filters.pais) params.set("pais", filters.pais);
      if (filters.puerto) params.set("puerto", filters.puerto);
      if (filters.operacion) params.set("operacion", filters.operacion);
      if (filters.year) params.set("year", filters.year);
      if (filters.month) params.set("month", filters.month);
    }
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest(`${endpoint}${params.toString() ? `?${params.toString()}` : ""}`, { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
      setDetail(null);
      setDetailForm({});
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar informes.");
    } finally {
      setBusy(false);
    }
  }

  async function changeReview(label: string) {
    const option = INFORME_REVIEW_OPTIONS.find((item) => item.label === label);
    if (!option) return;
    setActiveKey(option.key);
    setFilters({ status: "", search: "", continente: "", pais: "", puerto: "", operacion: "", year: "", month: "" });
    setRows([]);
    setSelected(null);
    setDetail(null);
    setDetailForm({});
  }

  useEffect(() => {
    setActiveKey(section.key);
    setRows(rowsFromAny(initialPayload));
    setSelected(null);
    setDetail(null);
    setDetailForm({});
  }, [section.key, initialPayload]);

  useEffect(() => {
    if (activeKey === section.key && rows.length) return;
    load();
  }, [activeKey]);

  async function openDetail() {
    if (!selectedRow) {
      setMessage("Seleccione una fila.");
      return;
    }
    if (!config.detailEndpoint) {
      setDetail(selectedRow);
      setDetailForm(recordToEditableForm(selectedRow));
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(endpointForRow(config.detailEndpoint, selectedRow, config.idField), { session });
      const nextDetail = unwrapRecordPayload(payload) || selectedRow;
      setDetail(nextDetail);
      setDetailForm(recordToEditableForm(nextDetail));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo abrir revision.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDetail() {
    if (!detail) return;
    const updateEndpoint = config.updateEndpoint || config.detailEndpoint;
    if (!updateEndpoint) {
      setMessage("Este informe no tiene endpoint de actualizacion.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const row = { ...detail, ...detailForm };
      await apiRequest(endpointForRow(updateEndpoint, row, config.idField), {
        method: "PUT",
        body: detailForm,
        session
      });
      setMessage("Informe actualizado correctamente.");
      setDetail(null);
      setDetailForm({});
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar cambios.");
    } finally {
      setBusy(false);
    }
  }

  async function runInformeAction(action: InformeAction) {
    if (!selectedRow) {
      setMessage("Seleccione una fila.");
      return;
    }
    const endpoint = endpointForRow(action.endpoint, selectedRow, config.idField);
    setBusy(true);
    setMessage("");
    try {
      if (action.file) {
        const rowId = formatValue(selectedRow[config.idField] || selectedRow.id || selectedRow.report_number || selectedRow.cert_no);
        const filename = cleanFilePart(`${config.title}_${action.label}_${rowId}`) + `.${extensionForInformeAction(action)}`;
        await downloadSessionFile(endpoint, session, filename, action.method || "GET", action.body);
        setMessage(`${action.label} generado correctamente.`);
      } else if (action.method === "GET" || !action.method) {
        await apiRequest(endpoint, { session });
        setMessage("Accion ejecutada correctamente.");
      } else {
        await apiRequest(endpoint, { method: action.method, body: action.body, session });
        setMessage("Accion ejecutada correctamente.");
        await load();
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `No se pudo ejecutar ${action.label}.`);
    } finally {
      setBusy(false);
    }
  }

  function openCreate(configToCreate: InformeCreateConfig) {
    setCreateConfig(configToCreate);
    const initial = Object.fromEntries(configToCreate.fields
      .filter((field) => field.type !== "section")
      .map((field) => {
        if (field.type === "date") return [field.key, formatYmd(new Date())];
        if (field.type === "datetime") return [field.key, `${formatYmd(new Date())} 00:00`];
        if (field.type === "checkbox") return [field.key, "false"];
        return [field.key, ""];
      }));
    if (configToCreate.key === "grain-sampling") {
      for (let index = 1; index <= 5; index += 1) initial[`hold${index}_product`] = "MAIZ AMARILLO";
    }
    setCreateForm(initial);
    setGenerateOpen(false);
    setGenerateGroup(null);
  }

  async function submitCreate() {
    if (!createConfig) return;
    setBusy(true);
    setMessage("");
    try {
      const payload: Record<string, string> = { ...createForm, status: "Pending for review" };
      if (createConfig.dateFormat === "dmy") {
        createConfig.fields.forEach((field) => {
          if (field.type === "date" && payload[field.key]) payload[field.key] = toDmy(payload[field.key]);
        });
      }
      createConfig.fields.forEach((field) => {
        if (field.type === "section") delete payload[field.key];
      });
      if (createConfig.key === "grain-sampling") {
        delete payload.service_port;
        delete payload.service_country;
      }
      await apiRequest(createConfig.endpoint, { method: "POST", body: payload, session });
      setCreateConfig(null);
      setCreateForm({});
      setMessage("Informe creado y enviado a revision.");
      if (activeKey === createConfig.key) await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo crear el informe.");
    } finally {
      setBusy(false);
    }
  }

  async function improveContainerTextWithPortia(field: InformeCreateField) {
    const originalText = (createForm[field.key] || "").trim();
    if (!originalText) {
      setMessage("La seccion seleccionada no tiene texto para mejorar.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await apiRequest<Record<string, unknown>>("/reports/ai/improve/container", {
        method: "POST",
        session,
        body: {
          text: originalText,
          container_no: createForm.report_no || createForm.linked_report_number || "",
          cargo: createForm.goods_description || "",
          location: createForm.inspection_place || "",
          condition: "As observed during inspection"
        }
      });
      const nextText = formatValue(response.text || response.improved_text || response.result);
      if (nextText === "-") {
        setMessage("PORTIA no devolvio texto valido.");
        return;
      }
      setCreateForm((current) => ({ ...current, [field.key]: nextText }));
      setMessage(`PORTIA mejoro: ${field.label}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo mejorar el texto.");
    } finally {
      setBusy(false);
    }
  }

  async function improveGrainSamplingWithPortia() {
    const originalText = (createForm.conclusion || "").trim();
    if (!originalText) {
      setMessage("La conclusion no tiene texto para mejorar.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await apiRequest<Record<string, unknown>>("/reports/ai/improve/grain", {
        method: "POST",
        session,
        body: {
          text: originalText,
          language: "ES",
          vessel: createForm.vessel_name || "",
          location: createForm.service_port || "",
          product: createForm.hold1_product || "Bulk Grain",
          authority: createForm.requested_by || ""
        }
      });
      const nextText = formatValue(response.text || response.improved_text || response.result);
      if (nextText === "-") {
        setMessage("PORTIA no devolvio texto valido.");
        return;
      }
      setCreateForm((current) => ({ ...current, conclusion: nextText }));
      setMessage("PORTIA mejoro la conclusion.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo mejorar la conclusion.");
    } finally {
      setBusy(false);
    }
  }

  async function improveTruckSupervisionWithPortia(field: InformeCreateField) {
    const originalText = (createForm[field.key] || "").trim();
    if (!originalText) {
      setMessage("La seccion seleccionada no tiene texto para mejorar.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await apiRequest<Record<string, unknown>>("/reports/ai/improve/truck", {
        method: "POST",
        session,
        body: {
          text: originalText,
          vessel: createForm.vessel_name || "",
          location: createForm.port || "",
          cargo: "Truck Discharge Operation",
          language: "ES"
        }
      });
      const nextText = formatValue(response.text || response.improved_text || response.result);
      if (nextText === "-") {
        setMessage("PORTIA no devolvio texto valido.");
        return;
      }
      setCreateForm((current) => ({ ...current, [field.key]: nextText }));
      setMessage(`PORTIA mejoro: ${field.label}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo mejorar el texto.");
    } finally {
      setBusy(false);
    }
  }

  function resetFilters() {
    setFilters({ status: "", search: "", continente: "", pais: "", puerto: "", operacion: "", year: "", month: "" });
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.moduleTitle}>Informes Maritimos</Text>
      <View style={styles.financeFilterBox}>
        <View style={styles.informesHomeActions}>
          <Pressable style={styles.modalClose} onPress={() => setCalculatorOpen(true)}><Text style={styles.modalCloseText}>Calculadora de proyectos</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => setReviewOpen(true)}><Text style={styles.modalCloseText}>Revisar informes</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => changeReview("Status de Informes")}><Text style={styles.modalCloseText}>Tabla pendientes</Text></Pressable>
          <Pressable
            style={styles.actionButton}
            onPress={() => {
              setGenerateGroup(null);
              setGenerateOpen(true);
            }}
          >
            <Text style={styles.actionButtonText}>Generar informes</Text>
          </Pressable>
        </View>
      </View>
      <Text style={styles.cardTitle}>{config.title}</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Status" value={filters.status} options={statusOptions} onChange={(status) => setFilters((f) => ({ ...f, status }))} />
        {activeKey === "status-informes" ? (
          <>
            <Text style={styles.label}>Continente</Text>
            <TextInput style={styles.input} value={filters.continente} onChangeText={(continente) => setFilters((f) => ({ ...f, continente }))} />
            <Text style={styles.label}>Pais</Text>
            <TextInput style={styles.input} value={filters.pais} onChangeText={(pais) => setFilters((f) => ({ ...f, pais }))} />
            <Text style={styles.label}>Puerto</Text>
            <TextInput style={styles.input} value={filters.puerto} onChangeText={(puerto) => setFilters((f) => ({ ...f, puerto }))} />
            <Text style={styles.label}>Operacion</Text>
            <TextInput style={styles.input} value={filters.operacion} onChangeText={(operacion) => setFilters((f) => ({ ...f, operacion }))} />
            <Text style={styles.label}>Anio</Text>
            <TextInput keyboardType="number-pad" style={styles.input} value={filters.year} onChangeText={(year) => setFilters((f) => ({ ...f, year }))} />
            <Text style={styles.label}>Mes</Text>
            <TextInput keyboardType="number-pad" style={styles.input} value={filters.month} onChangeText={(month) => setFilters((f) => ({ ...f, month }))} />
          </>
        ) : null}
        <Text style={styles.label}>Buscar</Text>
        <TextInput style={styles.input} value={filters.search} onChangeText={(search) => setFilters((f) => ({ ...f, search }))} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Cargar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={resetFilters}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <Text style={styles.tableCount}>{visibleRows.length} registros</Text>
      <HRMiniTable rows={visibleRows} columns={config.columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={openDetail}><Text style={styles.actionButtonText}>Review</Text></Pressable>
        {config.actions.map((action) => (
          <Pressable key={action.key} style={action.key === "reject" ? styles.modalClose : styles.actionButton} onPress={() => runInformeAction(action)}>
            <Text style={action.key === "reject" ? styles.modalCloseText : styles.actionButtonText}>{action.label}</Text>
          </Pressable>
        ))}
      </ScrollView>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Modal visible={detail !== null} animationType="slide" onRequestClose={() => setDetail(null)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Revision - {config.title}</Text>
            <Pressable style={styles.modalClose} onPress={() => setDetail(null)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
            {detail && Object.keys(detailForm).length === 0 ? (
              Object.entries(detail).map(([key, value]) => (
                <View key={key} style={styles.fieldRow}>
                  <Text style={styles.fieldKey}>{key.replaceAll("_", " ")}</Text>
                  <Text style={styles.fieldValue}>{formatValue(value)}</Text>
                </View>
              ))
            ) : null}
            {detail ? Object.keys(detailForm).map((key) => (
              <View key={key} style={styles.formField}>
                <Text style={styles.label}>{key.replaceAll("_", " ")}</Text>
                <TextInput
                  style={[styles.input, detailForm[key]?.length > 80 && styles.multilineInput]}
                  multiline={detailForm[key]?.length > 80}
                  value={detailForm[key]}
                  onChangeText={(value) => setDetailForm((current) => ({ ...current, [key]: value }))}
                />
              </View>
            )) : null}
            <Pressable style={styles.actionButton} onPress={saveDetail}><Text style={styles.actionButtonText}>Guardar Cambios</Text></Pressable>
          </ScrollView>
        </SafeAreaView>
      </Modal>
      <Modal visible={reviewOpen} animationType="slide" onRequestClose={() => setReviewOpen(false)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Revisar informes</Text>
            <Pressable style={styles.modalClose} onPress={() => setReviewOpen(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.modalBody}>
            {INFORME_REVIEW_OPTIONS.filter((option) => option.key !== "status-informes").map((option) => (
              <Pressable
                key={option.key}
                style={styles.secondaryButton}
                onPress={() => {
                  setReviewOpen(false);
                  changeReview(option.label);
                }}
              >
                <Text style={styles.secondaryButtonText}>{option.label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </SafeAreaView>
      </Modal>
      <Modal visible={generateOpen} animationType="slide" onRequestClose={() => setGenerateOpen(false)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Generar Informe Maritimo</Text>
            <Pressable style={styles.modalClose} onPress={() => setGenerateOpen(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.modalBody}>
            {!generateGroup ? (
              <>
                <Pressable style={styles.secondaryButton} onPress={() => openCreate(INFORMES_CREATE_CONFIG.find((item) => item.key === "container") || INFORMES_CREATE_CONFIG[0])}>
                  <Text style={styles.secondaryButtonText}>Contenedor</Text>
                </Pressable>
                <Pressable style={styles.secondaryButton} onPress={() => setGenerateGroup("Informe buque")}>
                  <Text style={styles.secondaryButtonText}>Buque</Text>
                </Pressable>
                <Pressable style={styles.secondaryButton} onPress={() => setGenerateGroup("Certificados")}>
                  <Text style={styles.secondaryButtonText}>Certificado</Text>
                </Pressable>
              </>
            ) : (
              <>
                <Pressable style={styles.modalClose} onPress={() => setGenerateGroup(null)}>
                  <Text style={styles.modalCloseText}>Volver</Text>
                </Pressable>
                <View style={styles.summaryBox}>
                  <Text style={styles.cardTitle}>{generateGroup}</Text>
                  {INFORMES_CREATE_CONFIG.filter((item) => item.group === generateGroup).map((item) => (
                    <Pressable key={item.key} style={styles.secondaryButton} onPress={() => openCreate(item)}>
                      <Text style={styles.secondaryButtonText}>{item.title}</Text>
                    </Pressable>
                  ))}
                </View>
              </>
            )}
          </ScrollView>
        </SafeAreaView>
      </Modal>
      <Modal visible={Boolean(createConfig)} animationType="slide" onRequestClose={() => setCreateConfig(null)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>{createConfig?.title || "Crear informe"}</Text>
            <Pressable style={styles.modalClose} onPress={() => setCreateConfig(null)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
            {createConfig?.fields.map((field) => (
              field.type === "section" ? (
                <View key={field.key} style={styles.summaryBox}>
                  <Text style={styles.cardTitle}>{field.label}</Text>
                </View>
              ) : createConfig.key === "container" && field.key === "linked_report_number" ? (
                <View key={field.key} style={styles.formField}>
                  <Text style={styles.label}>{field.label}</Text>
                  <Pressable style={styles.selectBox} onPress={() => setContainerSelectorOpen(true)}>
                    <Text style={styles.selectText}>{createForm[field.key] || "Select service report"}</Text>
                  </Pressable>
                </View>
              ) : createConfig.key === "grain-sampling" && field.key === "cert_no" ? (
                <View key={field.key} style={styles.formField}>
                  <Text style={styles.label}>{field.label}</Text>
                  <Pressable style={styles.selectBox} onPress={() => setGrainSelectorOpen(true)}>
                    <Text style={styles.selectText}>{createForm[field.key] || "Seleccionar informe de servicio"}</Text>
                  </Pressable>
                </View>
              ) : createConfig.key === "truck-supervision" && field.key === "cert_no" ? (
                <View key={field.key} style={styles.formField}>
                  <Text style={styles.label}>{field.label}</Text>
                  <Pressable style={styles.selectBox} onPress={() => setTruckSelectorOpen(true)}>
                    <Text style={styles.selectText}>{createForm[field.key] || "Seleccionar informe de servicio"}</Text>
                  </Pressable>
                </View>
              ) : field.type === "date" ? (
                <DateField key={field.key} label={field.label} value={createForm[field.key] || ""} onChange={(value) => setCreateForm((current) => ({ ...current, [field.key]: value }))} />
              ) : field.type === "datetime" ? (
                <DateTimeField key={field.key} label={field.label} value={createForm[field.key] || ""} onChange={(value) => setCreateForm((current) => ({ ...current, [field.key]: value }))} />
              ) : field.type === "checkbox" ? (
                <View key={field.key} style={styles.rememberRow}>
                  <Text style={styles.rememberText}>{field.label}</Text>
                  <Switch
                    value={createForm[field.key] === "true"}
                    onValueChange={(value) => setCreateForm((current) => ({ ...current, [field.key]: value ? "true" : "false" }))}
                    trackColor={{ true: BLUE }}
                  />
                </View>
              ) : (
                <View key={field.key} style={styles.formField}>
                  <Text style={styles.label}>{field.label}</Text>
                  <TextInput
                    style={[styles.input, field.type === "multiline" && styles.multilineInput]}
                    multiline={field.type === "multiline"}
                    value={createForm[field.key] || ""}
                    onChangeText={(value) => setCreateForm((current) => ({ ...current, [field.key]: value }))}
                  />
                  {createConfig.key === "container" && field.type === "multiline" ? (
                    <Pressable style={styles.secondaryButton} onPress={() => improveContainerTextWithPortia(field)}>
                      <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
                    </Pressable>
                  ) : createConfig.key === "grain-sampling" && field.key === "conclusion" ? (
                    <Pressable style={styles.secondaryButton} onPress={improveGrainSamplingWithPortia}>
                      <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
                    </Pressable>
                  ) : createConfig.key === "truck-supervision" && field.type === "multiline" ? (
                    <Pressable style={styles.secondaryButton} onPress={() => improveTruckSupervisionWithPortia(field)}>
                      <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
                    </Pressable>
                  ) : null}
                </View>
              )
            ))}
            <Pressable style={styles.actionButton} onPress={submitCreate}><Text style={styles.actionButtonText}>Enviar a revision</Text></Pressable>
          </ScrollView>
        </SafeAreaView>
      </Modal>
      <ContainerReportSelectorModal
        visible={containerSelectorOpen}
        session={session}
        onClose={() => setContainerSelectorOpen(false)}
        onSelect={(report) => {
          setCreateForm((current) => ({ ...current, ...containerFormFromServiceReport(report) }));
          setContainerSelectorOpen(false);
        }}
      />
      <GrainServiceSelectorModal
        visible={grainSelectorOpen}
        session={session}
        onClose={() => setGrainSelectorOpen(false)}
        onSelect={(report) => {
          setCreateForm((current) => ({ ...current, ...grainFormFromServiceReport(report) }));
          setGrainSelectorOpen(false);
        }}
      />
      <TruckServiceSelectorModal
        visible={truckSelectorOpen}
        session={session}
        onClose={() => setTruckSelectorOpen(false)}
        onSelect={(report) => {
          setCreateForm((current) => ({ ...current, ...truckFormFromServiceReport(report) }));
          setTruckSelectorOpen(false);
        }}
      />
      <ProjectCalculatorModal visible={calculatorOpen} session={session} onClose={() => setCalculatorOpen(false)} />
    </View>
  );
}

function getInformeEndpoint(activeKey: string, currentSection: AppSection, activeSection: AppSection) {
  if (currentSection.key === activeKey && currentSection.endpoint) return currentSection.endpoint;
  const config = INFORMES_CONFIG[activeKey];
  if (activeKey === "status-informes") return "/status-informes";
  if (activeKey === "container") return "/container-reports/list";
  return config?.createEndpoint || activeSection.endpoint;
}

function recordToEditableForm(record: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(record)
      .filter(([key, value]) => !["created_at", "updated_at"].includes(key) && (value === null || ["string", "number", "boolean"].includes(typeof value)))
      .map(([key, value]) => [key, value === null || value === undefined ? "" : String(value)])
  );
}

function composeServiceDateTime(row: Record<string, unknown>) {
  const date = formatValue(row.fecha_inicio);
  const time = formatValue(row.hora_inicio);
  if (date === "-") return "";
  return time === "-" ? `${date} 00:00` : `${date} ${time.slice(0, 5)}`;
}

function containerFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const client = formatValue(row.cliente);
  const vessel = formatValue(row.buque_contenedor);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const operation = formatValue(row.operacion);
  const detail = formatValue(row.detalle);
  const contact = formatValue(row.contacto);
  const serviceDateTime = composeServiceDateTime(row);

  return {
    linked_report_number: reportNumber === "-" ? "" : reportNumber,
    linked_service_client: client === "-" ? "" : client,
    linked_service_country: country === "-" ? "" : country,
    linked_service_port: port === "-" ? "" : port,
    linked_service_operation: operation === "-" ? "" : operation,
    report_no: reportNumber === "-" ? "" : reportNumber,
    vessel: vessel === "-" ? "" : vessel,
    shippers: client === "-" ? "" : client,
    on_behalf_of: client === "-" ? "" : client,
    inspection_place: [port, country].filter((item) => item !== "-").join(", "),
    contact_person: contact === "-" ? "" : contact,
    goods_description: detail === "-" ? "" : detail,
    container_type_text: operation === "-" ? "" : operation,
    contact_datetime: serviceDateTime,
    init_inspection_datetime: serviceDateTime
  };
}

function grainFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const client = formatValue(row.cliente);
  const vessel = formatValue(row.buque_contenedor);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const serviceDate = formatValue(row.fecha_inicio);
  const serviceDateTime = composeServiceDateTime(row);
  const products = Object.fromEntries(Array.from({ length: 5 }, (_, index) => [`hold${index + 1}_product`, "MAIZ AMARILLO"]));

  return {
    ...products,
    cert_no: reportNumber === "-" ? "" : reportNumber,
    service_port: port === "-" ? "" : port,
    service_country: country === "-" ? "" : country,
    place_date: serviceDate === "-" ? formatYmd(new Date()) : serviceDate,
    vessel_name: vessel === "-" ? "" : vessel,
    requested_by: client === "-" ? "" : client,
    sampling_start_time: serviceDateTime,
    supervision: serviceDateTime
  };
}

function monthStartFromService(row: Record<string, unknown>) {
  const exactDate = formatValue(row.fecha_inicio);
  if (exactDate !== "-") return exactDate.slice(0, 10);
  const year = formatValue(row.anio ?? row.year);
  const month = formatValue(row.mes ?? row.month);
  if (year === "-" || month === "-") return formatYmd(new Date());
  return `${year}-${month.padStart(2, "0")}-01`;
}

function truckFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const client = formatValue(row.cliente);
  const vessel = formatValue(row.buque_contenedor);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const reportDate = monthStartFromService(row);

  return {
    cert_no: reportNumber === "-" ? "" : reportNumber,
    customer: client === "-" ? "" : client,
    port: port === "-" ? "" : port,
    country: country === "-" ? "" : country,
    report_date: reportDate,
    vessel_name: vessel === "-" ? "" : vessel,
    inspection_date: reportDate
  };
}

function arrayFromPayload(payload: unknown, key: string) {
  const obj = asRecord(payload);
  const value = obj?.[key];
  return Array.isArray(value) ? value.map((item) => formatValue(item)).filter((item) => item !== "-") : [];
}

function arrayFromNestedPayload(payload: unknown, parentKey: string, key: string) {
  const parent = asRecord(asRecord(payload)?.[parentKey]);
  const value = parent?.[key];
  return Array.isArray(value) ? value.map((item) => formatValue(item)).filter((item) => item !== "-") : [];
}

function ContainerReportSelectorModal({
  visible,
  session,
  onClose,
  onSelect
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
  onSelect: (report: Record<string, unknown>) => void;
}) {
  const [filters, setFilters] = useState({ cliente: "", anio: "", mes: "", buque_contenedor: "" });
  const [clientes, setClientes] = useState<string[]>([]);
  const [anios, setAnios] = useState<string[]>([]);
  const [meses, setMeses] = useState<string[]>([]);
  const [buques, setBuques] = useState<string[]>([]);
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const selectedRow = selected === null ? null : rows[selected] || null;

  async function loadBaseFilters() {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest("/container-reports/filters", { session });
      setClientes(arrayFromPayload(payload, "clientes"));
      setAnios(arrayFromPayload(payload, "anios"));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar filtros.");
    } finally {
      setBusy(false);
    }
  }

  async function loadMonths(cliente: string, anio: string) {
    setMeses([]);
    setBuques([]);
    setRows([]);
    setFilters((current) => ({ ...current, mes: "", buque_contenedor: "" }));
    if (!cliente || !anio) return;
    try {
      const payload = await apiRequest(`/container-reports/filters/months?cliente=${encodeURIComponent(cliente)}&anio=${encodeURIComponent(anio)}`, { session });
      setMeses(arrayFromPayload(payload, "meses"));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar meses.");
    }
  }

  async function loadVessels(nextFilters = filters) {
    setBuques([]);
    setRows([]);
    setFilters((current) => ({ ...current, buque_contenedor: "" }));
    if (!nextFilters.cliente || !nextFilters.anio || !nextFilters.mes) return;
    try {
      const params = new URLSearchParams({
        cliente: nextFilters.cliente,
        anio: nextFilters.anio,
        mes: nextFilters.mes
      });
      const payload = await apiRequest(`/container-reports/filters/vessels?${params.toString()}`, { session });
      setBuques(arrayFromPayload(payload, "buques_contenedor"));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar buques/contenedores.");
    }
  }

  async function searchReports() {
    if (!filters.cliente || !filters.anio || !filters.mes || !filters.buque_contenedor) {
      setMessage("Complete cliente, anio, mes y vessel/container.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const params = new URLSearchParams({
        cliente: filters.cliente,
        buque_contenedor: filters.buque_contenedor,
        anio: filters.anio,
        mes: filters.mes
      });
      const payload = await apiRequest(`/container-reports/informes?${params.toString()}`, { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron buscar informes.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!visible) return;
    setFilters({ cliente: "", anio: "", mes: "", buque_contenedor: "" });
    setMeses([]);
    setBuques([]);
    setRows([]);
    setSelected(null);
    loadBaseFilters();
  }, [visible]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Select Service Report</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody}>
          <SelectField
            label="Client"
            value={filters.cliente}
            options={clientes}
            onChange={(cliente) => {
              const next = { ...filters, cliente, mes: "", buque_contenedor: "" };
              setFilters(next);
              loadMonths(cliente, next.anio);
            }}
          />
          <SelectField
            label="Year"
            value={filters.anio}
            options={anios}
            onChange={(anio) => {
              const next = { ...filters, anio, mes: "", buque_contenedor: "" };
              setFilters(next);
              loadMonths(next.cliente, anio);
            }}
          />
          <SelectField
            label="Month"
            value={filters.mes}
            options={meses}
            onChange={(mes) => {
              const next = { ...filters, mes, buque_contenedor: "" };
              setFilters(next);
              loadVessels(next);
            }}
          />
          <SelectField
            label="Vessel / Container"
            value={filters.buque_contenedor}
            options={buques}
            onChange={(buque_contenedor) => setFilters((current) => ({ ...current, buque_contenedor }))}
          />
          <View style={styles.informesHomeActions}>
            <Pressable style={styles.actionButton} onPress={searchReports}><Text style={styles.actionButtonText}>Search</Text></Pressable>
            <Pressable
              style={styles.modalClose}
              onPress={() => {
                const report = formatValue(selectedRow?.num_informe);
                if (report === "-") {
                  setMessage("Please select a report.");
                } else {
                  onSelect(selectedRow || { num_informe: report });
                }
              }}
            >
              <Text style={styles.modalCloseText}>Use selected report</Text>
            </Pressable>
          </View>
          <Text style={styles.tableCount}>{rows.length} reports</Text>
          <HRMiniTable rows={rows} columns={["num_informe", "cliente", "buque_contenedor", "pais", "puerto", "operacion", "fecha_inicio"]} selectedIndex={selected} onSelect={setSelected} />
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function GrainServiceSelectorModal({
  visible,
  session,
  onClose,
  onSelect
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
  onSelect: (report: Record<string, unknown>) => void;
}) {
  const [filters, setFilters] = useState({
    year: "",
    month: "",
    continente: "",
    pais: "",
    puerto: "",
    cliente: "",
    buque: "",
    operacion: ""
  });
  const [options, setOptions] = useState<Record<string, string[]>>({});
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const selectedRow = selected === null ? null : rows[selected] || null;

  async function loadSelector(nextFilters = filters, includeRows = true) {
    setBusy(true);
    setMessage("");
    try {
      const params = new URLSearchParams();
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value) params.set(key, value);
      });
      const payload = await apiRequest(`/vessel-grain-sampling/services-selector${params.toString() ? `?${params.toString()}` : ""}`, { session });
      setOptions({
        years: arrayFromNestedPayload(payload, "filters", "years"),
        months: arrayFromNestedPayload(payload, "filters", "months"),
        continentes: arrayFromNestedPayload(payload, "filters", "continentes"),
        paises: arrayFromNestedPayload(payload, "filters", "paises"),
        puertos: arrayFromNestedPayload(payload, "filters", "puertos"),
        clientes: arrayFromNestedPayload(payload, "filters", "clientes"),
        buques: arrayFromNestedPayload(payload, "filters", "buques"),
        operaciones: arrayFromNestedPayload(payload, "filters", "operaciones")
      });
      setRows(includeRows ? rowsFromAny(payload) : []);
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar el selector de Grain Sampling.");
    } finally {
      setBusy(false);
    }
  }

  function updateFilter(key: keyof typeof filters, value: string) {
    const next = { ...filters, [key]: value };
    setFilters(next);
    loadSelector(next, true);
  }

  useEffect(() => {
    if (!visible) return;
    const initial = { year: "", month: "", continente: "", pais: "", puerto: "", cliente: "", buque: "", operacion: "" };
    setFilters(initial);
    setRows([]);
    setOptions({});
    setSelected(null);
    loadSelector(initial, true);
  }, [visible]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Select Grain Sampling Service</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody}>
          <SelectField label="Year" value={filters.year} options={options.years || []} onChange={(value) => updateFilter("year", value)} />
          <SelectField label="Month" value={filters.month} options={options.months || []} onChange={(value) => updateFilter("month", value)} />
          <SelectField label="Continente" value={filters.continente} options={options.continentes || []} onChange={(value) => updateFilter("continente", value)} />
          <SelectField label="Pais" value={filters.pais} options={options.paises || []} onChange={(value) => updateFilter("pais", value)} />
          <SelectField label="Puerto" value={filters.puerto} options={options.puertos || []} onChange={(value) => updateFilter("puerto", value)} />
          <SelectField label="Cliente" value={filters.cliente} options={options.clientes || []} onChange={(value) => updateFilter("cliente", value)} />
          <SelectField label="Buque" value={filters.buque} options={options.buques || []} onChange={(value) => updateFilter("buque", value)} />
          <SelectField label="Operacion" value={filters.operacion} options={options.operaciones || []} onChange={(value) => updateFilter("operacion", value)} />
          <View style={styles.informesHomeActions}>
            <Pressable style={styles.actionButton} onPress={() => loadSelector(filters, true)}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
            <Pressable
              style={styles.modalClose}
              onPress={() => {
                if (!selectedRow) {
                  setMessage("Seleccione un informe.");
                } else {
                  onSelect(selectedRow);
                }
              }}
            >
              <Text style={styles.modalCloseText}>Usar informe</Text>
            </Pressable>
          </View>
          <Text style={styles.tableCount}>{rows.length} informes</Text>
          <HRMiniTable rows={rows} columns={["num_informe", "buque_contenedor", "cliente", "pais", "puerto", "operacion", "fecha_inicio"]} selectedIndex={selected} onSelect={setSelected} />
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function TruckServiceSelectorModal({
  visible,
  session,
  onClose,
  onSelect
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
  onSelect: (report: Record<string, unknown>) => void;
}) {
  const [filters, setFilters] = useState({
    anio: "",
    mes: "",
    continente: "",
    pais: "",
    puerto: "",
    cliente: "",
    buque_contenedor: "",
    operacion: ""
  });
  const [options, setOptions] = useState<Record<string, string[]>>({});
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const selectedRow = selected === null ? null : rows[selected] || null;

  async function loadSelector(nextFilters = filters) {
    setBusy(true);
    setMessage("");
    try {
      const params = new URLSearchParams();
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value) params.set(key, value);
      });
      const payload = await apiRequest(`/vessel-truck-supervision/servicios-filter${params.toString() ? `?${params.toString()}` : ""}`, { session });
      setOptions({
        years: arrayFromNestedPayload(payload, "filters", "years"),
        months: arrayFromNestedPayload(payload, "filters", "months"),
        continentes: arrayFromNestedPayload(payload, "filters", "continentes"),
        paises: arrayFromNestedPayload(payload, "filters", "paises"),
        puertos: arrayFromNestedPayload(payload, "filters", "puertos"),
        clientes: arrayFromNestedPayload(payload, "filters", "clientes"),
        buques: arrayFromNestedPayload(payload, "filters", "buques"),
        operaciones: arrayFromNestedPayload(payload, "filters", "operaciones")
      });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar el selector de Truck Supervision.");
    } finally {
      setBusy(false);
    }
  }

  function updateFilter(key: keyof typeof filters, value: string) {
    const next = { ...filters, [key]: value };
    setFilters(next);
    loadSelector(next);
  }

  useEffect(() => {
    if (!visible) return;
    const initial = { anio: "", mes: "", continente: "", pais: "", puerto: "", cliente: "", buque_contenedor: "", operacion: "" };
    setFilters(initial);
    setRows([]);
    setOptions({});
    setSelected(null);
    loadSelector(initial);
  }, [visible]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Buscar Servicio Truck</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody}>
          <SelectField label="Anio" value={filters.anio} options={options.years || []} onChange={(value) => updateFilter("anio", value)} />
          <SelectField label="Mes" value={filters.mes} options={options.months || []} onChange={(value) => updateFilter("mes", value)} />
          <SelectField label="Continente" value={filters.continente} options={options.continentes || []} onChange={(value) => updateFilter("continente", value)} />
          <SelectField label="Pais" value={filters.pais} options={options.paises || []} onChange={(value) => updateFilter("pais", value)} />
          <SelectField label="Puerto" value={filters.puerto} options={options.puertos || []} onChange={(value) => updateFilter("puerto", value)} />
          <SelectField label="Cliente" value={filters.cliente} options={options.clientes || []} onChange={(value) => updateFilter("cliente", value)} />
          <SelectField label="Buque" value={filters.buque_contenedor} options={options.buques || []} onChange={(value) => updateFilter("buque_contenedor", value)} />
          <SelectField label="Operacion" value={filters.operacion} options={options.operaciones || []} onChange={(value) => updateFilter("operacion", value)} />
          <View style={styles.informesHomeActions}>
            <Pressable style={styles.actionButton} onPress={() => loadSelector(filters)}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
            <Pressable
              style={styles.modalClose}
              onPress={() => {
                if (!selectedRow) {
                  setMessage("Seleccione un servicio.");
                } else {
                  onSelect(selectedRow);
                }
              }}
            >
              <Text style={styles.modalCloseText}>Usar servicio</Text>
            </Pressable>
          </View>
          <Text style={styles.tableCount}>{rows.length} servicios</Text>
          <HRMiniTable rows={rows} columns={["num_informe", "buque_contenedor", "cliente", "pais", "puerto", "anio", "mes", "operacion"]} selectedIndex={selected} onSelect={setSelected} />
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function ProjectCalculatorModal({
  visible,
  session,
  onClose
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
}) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [mode, setMode] = useState<"list" | "create">("list");
  const [form, setForm] = useState({
    nombre_proyecto: "",
    moneda: "USD",
    horas: "1",
    minutos: "0",
    persona_1: "",
    persona_2: "",
    persona_3: "",
    gasto_alimentacion: "",
    gasto_comunicacion: "",
    gasto_transporte: "",
    margen: "20",
    precio: "",
    comentarios: ""
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const selectedRow = selected === null ? null : rows[selected] || null;
  const tiempo = (Number(form.horas) || 0) + (Number(form.minutos) || 0) / 60;
  const personalCostos = [form.persona_1, form.persona_2, form.persona_3].map(Number).filter((value) => Number.isFinite(value) && value > 0);
  const totalHonorarios = personalCostos.reduce((sum, value) => sum + value, 0) * tiempo;
  const totalGastos = (Number(form.gasto_alimentacion) || 0) + (Number(form.gasto_comunicacion) || 0) + (Number(form.gasto_transporte) || 0);
  const costoTotal = totalHonorarios + totalGastos;
  const margen = (Number(form.margen) || 0) / 100;
  const suggestedPrice = margen < 1 ? costoTotal / (1 - margen) : 0;
  const precio = Number(form.precio) || suggestedPrice;
  const utilidad = precio ? ((precio - costoTotal) / precio) * 100 : 0;

  async function loadProjects() {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest("/proyectos-calculo", { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar los proyectos.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (visible) {
      setMode("list");
      loadProjects();
    }
  }, [visible]);

  async function createProject() {
    if (!form.nombre_proyecto.trim()) {
      setMessage("Debe ingresar el nombre del proyecto.");
      return;
    }
    if (!personalCostos.length) {
      setMessage("Debe ingresar al menos un costo de personal mayor a 0.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest("/proyectos-calculo", {
        method: "POST",
        session,
        body: {
          nombre_proyecto: form.nombre_proyecto.trim(),
          personal_costos: personalCostos,
          moneda: form.moneda,
          tiempo: Number(tiempo.toFixed(2)),
          total_honorarios: Number(totalHonorarios.toFixed(2)),
          gasto_alimentacion: Number(form.gasto_alimentacion) || 0,
          gasto_comunicacion: Number(form.gasto_comunicacion) || 0,
          gasto_transporte: Number(form.gasto_transporte) || 0,
          total_gastos: Number(totalGastos.toFixed(2)),
          margen: Number(form.margen) || 0,
          precio: Number(precio.toFixed(2)),
          utilidad: Number(utilidad.toFixed(2)),
          comentarios: form.comentarios || null
        }
      });
      setMessage("Proyecto guardado correctamente.");
      setMode("list");
      await loadProjects();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar el proyecto.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Calculadora de proyectos</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          <View style={styles.informesHomeActions}>
            <Pressable style={mode === "list" ? styles.actionButton : styles.modalClose} onPress={() => setMode("list")}>
              <Text style={mode === "list" ? styles.actionButtonText : styles.modalCloseText}>Proyectos existentes</Text>
            </Pressable>
            <Pressable style={mode === "create" ? styles.actionButton : styles.modalClose} onPress={() => setMode("create")}>
              <Text style={mode === "create" ? styles.actionButtonText : styles.modalCloseText}>Nuevo Proyecto</Text>
            </Pressable>
          </View>
          {mode === "list" ? (
            <>
              <Pressable style={styles.secondaryButton} onPress={loadProjects}><Text style={styles.secondaryButtonText}>Cargar proyectos</Text></Pressable>
              <Text style={styles.tableCount}>{rows.length} proyectos</Text>
              <HRMiniTable
                rows={rows}
                columns={["nombre_proyecto", "moneda", "precio", "utilidad", "creado_el"]}
                selectedIndex={selected}
                onSelect={setSelected}
              />
              {selectedRow ? (
                <View style={styles.summaryBox}>
                  {Object.entries(selectedRow).map(([key, value]) => (
                    <View key={key} style={styles.fieldRow}>
                      <Text style={styles.fieldKey}>{key.replaceAll("_", " ")}</Text>
                      <Text style={styles.fieldValue}>{formatValue(value)}</Text>
                    </View>
                  ))}
                </View>
              ) : null}
            </>
          ) : (
            <>
              <Text style={styles.label}>Nombre del Proyecto</Text>
              <TextInput style={styles.input} value={form.nombre_proyecto} onChangeText={(value) => setForm((current) => ({ ...current, nombre_proyecto: value }))} />
              <SelectField label="Moneda" value={form.moneda} options={["USD", "CRC", "EUR"]} onChange={(moneda) => setForm((current) => ({ ...current, moneda }))} />
              <View style={styles.timeRow}>
                <View style={styles.timePart}>
                  <Text style={styles.label}>Horas</Text>
                  <TextInput keyboardType="number-pad" style={styles.input} value={form.horas} onChangeText={(horas) => setForm((current) => ({ ...current, horas }))} />
                </View>
                <View style={styles.timePart}>
                  <Text style={styles.label}>Minutos</Text>
                  <TextInput keyboardType="number-pad" style={styles.input} value={form.minutos} onChangeText={(minutos) => setForm((current) => ({ ...current, minutos }))} />
                </View>
              </View>
              {["persona_1", "persona_2", "persona_3"].map((key, index) => (
                <View key={key} style={styles.formField}>
                  <Text style={styles.label}>Persona {index + 1} costo/hora</Text>
                  <TextInput keyboardType="decimal-pad" style={styles.input} value={form[key as keyof typeof form]} onChangeText={(value) => setForm((current) => ({ ...current, [key]: value }))} />
                </View>
              ))}
              {[
                ["gasto_alimentacion", "Alimentacion"],
                ["gasto_comunicacion", "Comunicacion"],
                ["gasto_transporte", "Transporte"]
              ].map(([key, label]) => (
                <View key={key} style={styles.formField}>
                  <Text style={styles.label}>{label}</Text>
                  <TextInput keyboardType="decimal-pad" style={styles.input} value={form[key as keyof typeof form]} onChangeText={(value) => setForm((current) => ({ ...current, [key]: value }))} />
                </View>
              ))}
              <SelectField label="Margen %" value={form.margen} options={["10", "20", "30", "40", "50", "60", "70", "80", "90"]} onChange={(margen) => setForm((current) => ({ ...current, margen }))} />
              <Text style={styles.label}>Precio editable</Text>
              <TextInput keyboardType="decimal-pad" style={styles.input} value={form.precio} placeholder={suggestedPrice.toFixed(2)} onChangeText={(precio) => setForm((current) => ({ ...current, precio }))} />
              <Text style={styles.label}>Comentarios</Text>
              <TextInput style={[styles.input, styles.multilineInput]} multiline value={form.comentarios} onChangeText={(comentarios) => setForm((current) => ({ ...current, comentarios }))} />
              <View style={styles.summaryBox}>
                <Text style={styles.fieldKey}>Total Honorarios</Text>
                <Text style={styles.fieldValue}>{totalHonorarios.toFixed(2)}</Text>
                <Text style={styles.fieldKey}>Total Gastos</Text>
                <Text style={styles.fieldValue}>{totalGastos.toFixed(2)}</Text>
                <Text style={styles.fieldKey}>Precio</Text>
                <Text style={styles.fieldValue}>{precio.toFixed(2)}</Text>
                <Text style={styles.fieldKey}>Rentabilidad %</Text>
                <Text style={styles.fieldValue}>{utilidad.toFixed(2)}</Text>
              </View>
              <Pressable style={styles.actionButton} onPress={createProject}><Text style={styles.actionButtonText}>Guardar Proyecto</Text></Pressable>
            </>
          )}
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={message.includes("correctamente") ? styles.helperText : styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
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

function isAdminSession(session: NonNullable<ReturnType<typeof useAuth>["session"]>) {
  const role = (session.rol || "").toLowerCase();
  return role === "admin" || role === "master";
}

function previousPayrollPeriod() {
  const today = new Date();
  const closed = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  return {
    year: String(closed.getFullYear()),
    month: String(closed.getMonth() + 1).padStart(2, "0")
  };
}

function rowsFromAny(payload: unknown) {
  return rowsForSection(undefined, payload);
}

function HHRRSectionMobile({
  section,
  initialPayload,
  session
}: {
  section: AppSection;
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  if (section.key === "empleados-hr") return <HREmployeesView initialRows={rowsFromAny(initialPayload)} session={session} />;
  if (section.key === "solicitudes") return <HRRequestsView initialRows={rowsFromAny(initialPayload)} session={session} />;
  if (section.key === "registro-horas") return <HRHoursView initialPayload={initialPayload} session={session} />;
  if (section.key === "payroll") return <HRPayrollView initialRows={rowsFromAny(initialPayload)} session={session} />;
  if (section.key === "colillas") return <HRPayslipsView initialRows={rowsFromAny(initialPayload)} session={session} />;
  if (section.key === "politicas") return <HRPoliciesView initialRows={rowsFromAny(initialPayload)} session={session} />;
  if (section.key === "noticias") return <HRNewsView initialPayload={initialPayload} session={session} />;
  return <ListView rows={rowsFromAny(initialPayload)} />;
}

function HRMiniTable({
  rows,
  columns,
  selectedIndex,
  onSelect
}: {
  rows: Record<string, unknown>[];
  columns: string[];
  selectedIndex: number | null;
  onSelect: (index: number) => void;
}) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator>
      <View>
        <View style={styles.tableHeader}>
          {columns.map((column) => (
            <Text key={column} style={styles.tableHeaderCell} numberOfLines={1}>
              {column.replaceAll("_", " ")}
            </Text>
          ))}
        </View>
        <ScrollView style={styles.tableRows} nestedScrollEnabled>
          {rows.map((row, index) => (
            <Pressable
              key={`${formatValue(row.id ?? row.codigo ?? row.usuario)}-${index}`}
              style={[styles.tableRow, selectedIndex === index && styles.tableRowSelected]}
              onPress={() => onSelect(index)}
            >
              {columns.map((column) => (
                <Text key={column} style={styles.tableCell} numberOfLines={1}>
                  {formatValue(row[column])}
                </Text>
              ))}
            </Pressable>
          ))}
        </ScrollView>
      </View>
    </ScrollView>
  );
}

function formatYmd(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function parseYmd(value: string) {
  if (!value) return null;
  const [year, month, day] = value.split("-").map(Number);
  if (!year || !month || !day) return null;
  const date = new Date(year, month - 1, day);
  return Number.isNaN(date.getTime()) ? null : date;
}

function longEnglishDate(value: string) {
  const date = parseYmd(value);
  if (!date) return "Select date";
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric"
  });
}

function buildCalendarDays(viewDate: Date) {
  const first = new Date(viewDate.getFullYear(), viewDate.getMonth(), 1);
  const startOffset = first.getDay();
  const cursor = new Date(first);
  cursor.setDate(first.getDate() - startOffset);
  return Array.from({ length: 42 }, (_, index) => {
    const next = new Date(cursor);
    next.setDate(cursor.getDate() + index);
    return next;
  });
}

function DateField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const [open, setOpen] = useState(false);
  const [viewDate, setViewDate] = useState(() => parseYmd(value) || new Date());
  const selected = parseYmd(value);
  const days = buildCalendarDays(viewDate);

  function moveMonth(delta: number) {
    setViewDate((current) => new Date(current.getFullYear(), current.getMonth() + delta, 1));
  }

  function select(date: Date) {
    onChange(formatYmd(date));
    setViewDate(date);
    setOpen(false);
  }

  return (
    <View style={styles.formField}>
      <Text style={styles.label}>{label}</Text>
      <Pressable style={styles.selectBox} onPress={() => setOpen(true)}>
        <Text style={styles.selectText}>{longEnglishDate(value)}</Text>
        {value ? <Text style={styles.helperText}>{value}</Text> : null}
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <View style={styles.calendarOverlay}>
          <View style={styles.calendarPanel}>
            <View style={styles.calendarHeader}>
              <Pressable style={styles.modalClose} onPress={() => moveMonth(-1)}><Text style={styles.modalCloseText}>Prev</Text></Pressable>
              <Text style={styles.calendarTitle}>{viewDate.toLocaleDateString("en-US", { month: "long", year: "numeric" })}</Text>
              <Pressable style={styles.modalClose} onPress={() => moveMonth(1)}><Text style={styles.modalCloseText}>Next</Text></Pressable>
            </View>
            <View style={styles.calendarWeek}>
              {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => <Text key={day} style={styles.calendarWeekday}>{day}</Text>)}
            </View>
            <View style={styles.calendarGrid}>
              {days.map((date) => {
                const ymd = formatYmd(date);
                const inMonth = date.getMonth() === viewDate.getMonth();
                const active = selected && ymd === formatYmd(selected);
                return (
                  <Pressable key={ymd} style={[styles.calendarDay, active && styles.calendarDayActive]} onPress={() => select(date)}>
                    <Text style={[styles.calendarDayText, !inMonth && styles.calendarDayMuted, active && styles.calendarDayTextActive]}>{date.getDate()}</Text>
                  </Pressable>
                );
              })}
            </View>
            <View style={styles.financeFilterActions}>
              <Pressable style={styles.actionButton} onPress={() => select(new Date())}><Text style={styles.actionButtonText}>Today</Text></Pressable>
              <Pressable style={styles.modalClose} onPress={() => setOpen(false)}><Text style={styles.modalCloseText}>Cancel</Text></Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

function DateTimeField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const datePart = value?.slice(0, 10) || "";
  const timePart = value?.slice(11, 16) || "00:00";

  function setDate(nextDate: string) {
    onChange(`${nextDate} ${timePart || "00:00"}`);
  }

  function setTime(nextTime: string) {
    onChange(`${datePart || formatYmd(new Date())} ${nextTime}`);
  }

  return (
    <View style={styles.formField}>
      <DateField label={label} value={datePart} onChange={setDate} />
      <Text style={styles.label}>Hora 24h</Text>
      <TextInput
        style={styles.input}
        value={timePart}
        onChangeText={setTime}
        placeholder="00:00"
      />
    </View>
  );
}

function TimeField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  const [hour = "08", minute = "00"] = (value || "08:00").split(":");
  const hours = Array.from({ length: 24 }, (_, index) => String(index).padStart(2, "0"));
  const minutes = Array.from({ length: 12 }, (_, index) => String(index * 5).padStart(2, "0"));
  return (
    <View style={styles.formField}>
      <Text style={styles.label}>{label}</Text>
      <View style={styles.timeRow}>
        <View style={styles.timePart}>
          <SelectField label="Hour" value={hour} options={hours} onChange={(nextHour) => onChange(`${nextHour}:${minute}`)} />
        </View>
        <View style={styles.timePart}>
          <SelectField label="Minute" value={minute} options={minutes} onChange={(nextMinute) => onChange(`${hour}:${nextMinute}`)} />
        </View>
      </View>
    </View>
  );
}

function HREmployeesView({
  initialRows,
  session
}: {
  initialRows: Record<string, unknown>[];
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const admin = isAdminSession(session);
  const [rows, setRows] = useState(initialRows);
  const [selected, setSelected] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [filters, setFilters] = useState({ nombre: "", codigo: "", usuario: "", estado: "" });
  const [modalMode, setModalMode] = useState<"add" | "edit" | "view" | null>(null);
  const [form, setForm] = useState<Record<string, string>>({});
  const columns = ["id", "codigo", "usuario", "nombre", "apellidos", "jornada", "salario", "pago", "estado"];
  const selectedRow = selected === null ? null : rows[selected] || null;

  async function load() {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    Object.entries(filters).forEach(([key, value]) => {
      if (value.trim()) params.set(key, value.trim());
    });
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest(`/hr/employees?${params.toString()}`, { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar empleados.");
    } finally {
      setBusy(false);
    }
  }

  function openForm(mode: "add" | "edit" | "view") {
    if (mode !== "add" && !selectedRow) {
      setMessage("Seleccione un empleado.");
      return;
    }
    const source = mode === "add" ? {} : selectedRow || {};
    const next = Object.fromEntries(HR_EMPLOYEE_FIELDS.map((field) => [field, formatValue(source[field]) === "-" ? "" : formatValue(source[field])]));
    setForm(next);
    setModalMode(mode);
  }

  async function saveEmployee() {
    if (!modalMode || modalMode === "view") return;
    const id = formatValue(selectedRow?.id);
    setBusy(true);
    setMessage("");
    try {
      if (modalMode === "add") {
        await apiRequest("/hr/employees", { method: "POST", body: form, session });
      } else {
        await apiRequest(`/hr/employees/${id}`, { method: "PUT", body: form, session });
      }
      setModalMode(null);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar empleado.");
    } finally {
      setBusy(false);
    }
  }

  if (!admin) return <Text style={styles.empty}>No tienes permisos para administrar empleados.</Text>;

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Empleados HHRR</Text>
      <View style={styles.financeFilterBox}>
        <TextInput style={styles.input} value={filters.nombre} onChangeText={(nombre) => setFilters((f) => ({ ...f, nombre }))} placeholder="Nombre o apellidos" />
        <TextInput style={styles.input} value={filters.codigo} onChangeText={(codigo) => setFilters((f) => ({ ...f, codigo }))} placeholder="Codigo" />
        <TextInput style={styles.input} value={filters.usuario} onChangeText={(usuario) => setFilters((f) => ({ ...f, usuario }))} placeholder="Usuario" />
        <SelectField label="Estado" value={filters.estado || "Todos"} options={["Todos", "Activo", "Inactivo"]} onChange={(estado) => setFilters((f) => ({ ...f, estado: estado === "Todos" ? "" : estado }))} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => setFilters({ nombre: "", codigo: "", usuario: "", estado: "" })}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={() => openForm("view")}><Text style={styles.actionButtonText}>Ver</Text></Pressable>
        <Pressable style={styles.actionButton} onPress={() => openForm("add")}><Text style={styles.actionButtonText}>Agregar</Text></Pressable>
        <Pressable style={styles.actionButton} onPress={() => openForm("edit")}><Text style={styles.actionButtonText}>Editar</Text></Pressable>
      </ScrollView>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Modal visible={modalMode !== null} animationType="slide" onRequestClose={() => setModalMode(null)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>{modalMode === "add" ? "Nuevo empleado" : modalMode === "edit" ? "Editar empleado" : "Ver empleado"}</Text>
            <Pressable style={styles.modalClose} onPress={() => setModalMode(null)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.modalBody}>
            {HR_EMPLOYEE_FIELDS.map((field) => (
              <View key={field} style={styles.formField}>
                <Text style={styles.label}>{field.replaceAll("_", " ")}</Text>
                <TextInput
                  editable={modalMode !== "view" && field !== "codigo" && field !== "id"}
                  value={form[field] || ""}
                  onChangeText={(value) => setForm((current) => ({ ...current, [field]: value }))}
                  style={[styles.input, (modalMode === "view" || field === "codigo" || field === "id") && styles.readonlyInput]}
                />
              </View>
            ))}
            {modalMode !== "view" ? <PrimaryButton label="Guardar" loading={busy} onPress={saveEmployee} /> : null}
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

const HR_EMPLOYEE_FIELDS = [
  "id", "codigo", "cedula_id", "usuario", "nombre", "apellidos", "estado_civil", "genero", "nacionalidad",
  "fecha_nacimiento", "edad", "prefijo", "telefono", "provincia", "canton", "distrito", "direccion",
  "jornada", "salario", "pago", "banco", "cuenta_iban", "moneda", "fecha_ingreso", "horas_contratadas",
  "vacaciones", "estado", "enfermedades", "contacto_emergencia", "telefono_emergencia",
  "activo1", "marca1", "serial1", "activo2", "marca2", "serial2", "activo3", "marca3", "serial3"
];

function HRRequestsView({
  initialRows,
  session
}: {
  initialRows: Record<string, unknown>[];
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const admin = isAdminSession(session);
  const [rows, setRows] = useState(initialRows);
  const [selected, setSelected] = useState<number | null>(null);
  const [filters, setFilters] = useState({ empleado: "", status: "", tipo: "" });
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({ event_type: "VACACIONES", fecha_inicio: "", fecha_fin: "", motivo: "", tipo_licencia: "" });
  const [vacationInfo, setVacationInfo] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = ["id", "empleado", "event_type", "event_date", "period_year", "period_month", "dias", "status", "razon_solicitud", "created_by", "approved_by"];

  function normalize(row: Record<string, unknown>): Record<string, unknown> {
    const payload = asRecord(row.payload) || {};
    return {
      ...row,
      dias: payload.dias_solicitados ?? row.vacaciones ?? "",
      razon_solicitud: row.comentario_solicitud ?? payload.motivo ?? "",
      status: formatValue(row.status).toUpperCase()
    };
  }

  const normalizedRows = rows.map(normalize);
  const visibleRows = normalizedRows.filter((row) => {
    if (filters.empleado && formatValue(row.empleado) !== filters.empleado) return false;
    if (filters.status && formatValue(row.status) !== filters.status) return false;
    if (filters.tipo && formatValue(row.event_type) !== filters.tipo) return false;
    return true;
  });
  const selectedRow = selected === null ? null : visibleRows[selected] || null;
  const empleados = ["", ...Array.from(new Set(normalizedRows.map((row) => formatValue(row.empleado)).filter((value) => value !== "-")))];
  const tipos = ["", ...Array.from(new Set(normalizedRows.map((row) => formatValue(row.event_type)).filter((value) => value !== "-")))];

  async function load() {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest("/hr/events/", { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar solicitudes.");
    } finally {
      setBusy(false);
    }
  }

  async function openRequestForm() {
    setShowForm(true);
    setMessage("");
    try {
      const info = await apiRequest<Record<string, unknown>>("/hr/events/vacaciones/disponibles", { session });
      setVacationInfo(info);
    } catch {
      setVacationInfo(null);
    }
  }

  function daysRequested() {
    if (!form.fecha_inicio || !form.fecha_fin) return 0;
    const start = new Date(`${form.fecha_inicio}T00:00:00`);
    const end = new Date(`${form.fecha_fin}T00:00:00`);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end < start) return 0;
    return Math.floor((end.getTime() - start.getTime()) / 86400000) + 1;
  }

  async function submitRequest() {
    const type = form.event_type;
    const payload: Record<string, unknown> = {};
    if (["VACACIONES", "INCAPACIDAD", "LICENCIA"].includes(type)) {
      const dias = daysRequested();
      if (!form.fecha_inicio || !form.fecha_fin || dias <= 0) {
        setMessage("Complete fechas validas para la solicitud.");
        return;
      }
      payload.fecha_inicio = form.fecha_inicio;
      payload.fecha_fin = form.fecha_fin;
      payload.dias_solicitados = dias;
      if (type === "LICENCIA") payload.tipo_licencia = form.tipo_licencia || "PERSONAL";
    } else {
      if (!form.motivo.trim()) {
        setMessage("Debe indicar motivo.");
        return;
      }
      payload.motivo = form.motivo.trim();
    }

    setBusy(true);
    setMessage("");
    try {
      await apiRequest("/hr/events/", { method: "POST", body: { event_type: type, event_date: new Date().toISOString().slice(0, 10), payload }, session });
      setShowForm(false);
      setForm({ event_type: "VACACIONES", fecha_inicio: "", fecha_fin: "", motivo: "", tipo_licencia: "" });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo crear solicitud.");
    } finally {
      setBusy(false);
    }
  }

  async function updateRequestStatus(action: "approve" | "reject") {
    if (!selectedRow) {
      setMessage("Seleccione una solicitud.");
      return;
    }
    if (!admin) {
      setMessage("No autorizado.");
      return;
    }
    if (formatValue(selectedRow.status) !== "PENDING") {
      setMessage("Solo solicitudes pendientes.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/hr/events/${selectedRow.id}/${action}`, {
        method: "PATCH",
        body: { comentario: action === "approve" ? "Aprobado desde app" : "Rechazado desde app" },
        session
      });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo actualizar solicitud.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Solicitudes HHRR</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Empleado" value={filters.empleado} options={empleados} onChange={(empleado) => setFilters((f) => ({ ...f, empleado }))} />
        <SelectField label="Estado" value={filters.status} options={["", "PENDING", "APPROVED", "REJECTED"]} onChange={(status) => setFilters((f) => ({ ...f, status }))} />
        <SelectField label="Tipo" value={filters.tipo} options={tipos} onChange={(tipo) => setFilters((f) => ({ ...f, tipo }))} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Cargar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => setFilters({ empleado: "", status: "", tipo: "" })}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <HRMiniTable rows={visibleRows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={openRequestForm}><Text style={styles.actionButtonText}>Nueva Solicitud</Text></Pressable>
        {admin ? <Pressable style={styles.actionButton} onPress={() => updateRequestStatus("approve")}><Text style={styles.actionButtonText}>Aprobar</Text></Pressable> : null}
        {admin ? <Pressable style={styles.actionButton} onPress={() => updateRequestStatus("reject")}><Text style={styles.actionButtonText}>Rechazar</Text></Pressable> : null}
      </ScrollView>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Modal visible={showForm} animationType="slide" onRequestClose={() => setShowForm(false)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Nueva Solicitud HHRR</Text>
            <Pressable style={styles.modalClose} onPress={() => setShowForm(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
          </View>
          <ScrollView contentContainerStyle={styles.modalBody}>
            <SelectField label="Tipo de solicitud" value={form.event_type} options={["VACACIONES", "CONSTANCIA_SALARIAL", "CONSTANCIA_LABORAL", "INCAPACIDAD", "LICENCIA"]} onChange={(event_type) => setForm((f) => ({ ...f, event_type }))} />
            {["VACACIONES", "INCAPACIDAD", "LICENCIA"].includes(form.event_type) ? (
              <>
                {form.event_type === "LICENCIA" ? <SelectField label="Tipo licencia" value={form.tipo_licencia || "PERSONAL"} options={["PERSONAL", "PATERNIDAD", "MATERNIDAD", "DUELO", "ESTUDIO"]} onChange={(tipo_licencia) => setForm((f) => ({ ...f, tipo_licencia }))} /> : null}
                <DateField label="Fecha inicio" value={form.fecha_inicio} onChange={(fecha_inicio) => setForm((f) => ({ ...f, fecha_inicio }))} />
                <DateField label="Fecha fin" value={form.fecha_fin} onChange={(fecha_fin) => setForm((f) => ({ ...f, fecha_fin }))} />
                <Text style={styles.helperText}>Dias solicitados: {daysRequested()} | Disponibles: {formatValue(vacationInfo?.dias_disponibles)}</Text>
              </>
            ) : (
              <>
                <Text style={styles.label}>Motivo</Text>
                <TextInput style={styles.input} value={form.motivo} onChangeText={(motivo) => setForm((f) => ({ ...f, motivo }))} />
              </>
            )}
            <PrimaryButton label="Enviar" loading={busy} onPress={submitRequest} />
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function HRHoursView({
  initialPayload,
  session
}: {
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const admin = isAdminSession(session);
  const [rows, setRows] = useState(rowsFromAny(initialPayload));
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [filters, setFilters] = useState({ usuario: "", tipo: "", estado: "" });
  const [form, setForm] = useState({ tipo: "OPERACION", fecha_inicio: "", hora_inicio: "08:00", fecha_fin: "", hora_fin: "17:00", buque: "", comentario: "" });
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = admin ? ["id", "estado", "usuario", "tipo", "fecha_inicio", "fecha_fin", "duracion_horas", "buque", "comentario"] : ["id", "tipo", "fecha_inicio", "fecha_fin", "duracion_horas", "buque", "comentario", "estado"];
  const selectedRow = selected === null ? null : rows[selected] || null;

  async function load() {
    const params = new URLSearchParams({ page: "1", page_size: "100" });
    if (admin && filters.usuario) params.set("usuario", filters.usuario);
    if (filters.tipo) params.set("tipo", filters.tipo);
    if (filters.estado) params.set("estado", filters.estado);
    setBusy(true);
    setMessage("");
    try {
      const [summaryPayload, rowsPayload] = await Promise.all([
        apiRequest<Record<string, unknown>>("/hr/ot-log/me/summary", { session }).catch(() => null),
        apiRequest(`/hr/ot-log?${params.toString()}`, { session })
      ]);
      setSummary(summaryPayload);
      setRows(rowsFromAny(rowsPayload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar registro de horas.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, [session.usuario, session.rol]);

  async function saveHours() {
    if (!form.fecha_inicio || !form.fecha_fin || !form.hora_inicio || !form.hora_fin) {
      setMessage("Complete fecha y hora de inicio/fin.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest("/hr/ot-log", {
        method: "POST",
        body: {
          tipo: form.tipo,
          fecha_inicio: `${form.fecha_inicio}T${form.hora_inicio}:00`,
          fecha_fin: `${form.fecha_fin}T${form.hora_fin}:00`,
          buque: form.buque || null,
          comentario: form.comentario || null
        },
        session
      });
      setShowForm(false);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo registrar horas.");
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(estado: string) {
    if (!selectedRow) {
      setMessage("Seleccione un registro.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/hr/ot-log/${selectedRow.id}/estado`, { method: "PUT", body: { estado }, session });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo actualizar estado.");
    } finally {
      setBusy(false);
    }
  }

  async function deleteLog() {
    if (!selectedRow) {
      setMessage("Seleccione un registro.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/hr/ot-log/${selectedRow.id}`, { method: "DELETE", session });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo eliminar registro.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>{admin ? "Registro de Horas - Administracion" : "Registro de Horas"}</Text>
      <View style={styles.summaryBox}>
        <Text style={styles.helperText}>
          Horas contratadas: {formatValue(summary?.horas_contratadas)} | Registradas: {formatValue(summary?.horas_registradas)} | Pendientes: {formatValue(summary?.horas_pendientes)}
        </Text>
      </View>
      <View style={styles.financeFilterBox}>
        {admin ? <TextInput style={styles.input} value={filters.usuario} onChangeText={(usuario) => setFilters((f) => ({ ...f, usuario }))} placeholder="Usuario" /> : null}
        <SelectField label="Tipo" value={filters.tipo} options={["", "OPERACION", "INFORME"]} onChange={(tipo) => setFilters((f) => ({ ...f, tipo }))} />
        <SelectField label="Estado" value={filters.estado} options={["", "PENDIENTE", "APROBADO", "RECHAZADO"]} onChange={(estado) => setFilters((f) => ({ ...f, estado }))} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Filtrar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => setFilters({ usuario: "", tipo: "", estado: "" })}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={() => setShowForm(true)}><Text style={styles.actionButtonText}>Registrar horas</Text></Pressable>
        {admin ? <Pressable style={styles.actionButton} onPress={() => updateStatus("APROBADO")}><Text style={styles.actionButtonText}>Aprobar</Text></Pressable> : null}
        {admin ? <Pressable style={styles.actionButton} onPress={() => updateStatus("RECHAZADO")}><Text style={styles.actionButtonText}>Rechazar</Text></Pressable> : null}
        {admin ? <Pressable style={styles.modalClose} onPress={deleteLog}><Text style={styles.modalCloseText}>Eliminar</Text></Pressable> : null}
      </ScrollView>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Modal visible={showForm} animationType="slide" onRequestClose={() => setShowForm(false)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}><Text style={styles.modalTitle}>Registrar horas</Text><Pressable style={styles.modalClose} onPress={() => setShowForm(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable></View>
          <ScrollView contentContainerStyle={styles.modalBody}>
            <SelectField label="Tipo" value={form.tipo} options={["OPERACION", "INFORME"]} onChange={(tipo) => setForm((f) => ({ ...f, tipo }))} />
            <DateField label="Fecha inicio" value={form.fecha_inicio} onChange={(fecha_inicio) => setForm((f) => ({ ...f, fecha_inicio }))} />
            <TimeField label="Hora inicio" value={form.hora_inicio} onChange={(hora_inicio) => setForm((f) => ({ ...f, hora_inicio }))} />
            <DateField label="Fecha fin" value={form.fecha_fin} onChange={(fecha_fin) => setForm((f) => ({ ...f, fecha_fin }))} />
            <TimeField label="Hora fin" value={form.hora_fin} onChange={(hora_fin) => setForm((f) => ({ ...f, hora_fin }))} />
            <Text style={styles.label}>Buque</Text><TextInput style={styles.input} value={form.buque} onChangeText={(buque) => setForm((f) => ({ ...f, buque }))} />
            <Text style={styles.label}>Detalle</Text><TextInput multiline style={[styles.input, styles.multilineInput]} value={form.comentario} onChangeText={(comentario) => setForm((f) => ({ ...f, comentario }))} />
            <PrimaryButton label="Registrar" loading={busy} onPress={saveHours} />
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function HRPayrollView({
  initialRows,
  session
}: {
  initialRows: Record<string, unknown>[];
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const admin = isAdminSession(session);
  const [rows, setRows] = useState(initialRows);
  const [selected, setSelected] = useState<number | null>(null);
  const period = previousPayrollPeriod();
  const [year, setYear] = useState(period.year);
  const [month, setMonth] = useState(period.month);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = ["usuario", "nombre", "apellidos", "jornada", "salario", "pago", "estado"];
  const selectedRow = selected === null ? null : rows[selected] || null;

  async function load() {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest("/hr/payroll/employees", { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
      setPreview(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar empleados payroll.");
    } finally {
      setBusy(false);
    }
  }

  async function calculate() {
    if (!selectedRow) {
      setMessage("Seleccione un empleado.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/hr/payroll/calculate?usuario=${encodeURIComponent(formatValue(selectedRow.usuario))}&year=${year}&month=${Number(month)}`, { session });
      setPreview(payload);
      setMessage("Preview de planilla calculado.");
    } catch (err) {
      setPreview(null);
      setMessage(err instanceof Error ? err.message : "No se pudo calcular planilla.");
    } finally {
      setBusy(false);
    }
  }

  async function postPayroll() {
    if (!preview) {
      setMessage("Primero calcule la planilla.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest("/hr/payroll/post", { method: "PUT", body: preview, session });
      setMessage("Planilla registrada correctamente.");
      setPreview(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo registrar planilla.");
    } finally {
      setBusy(false);
    }
  }

  if (!admin) return <Text style={styles.empty}>No tienes permisos para acceder a Payroll.</Text>;

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Payroll / Planilla</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Anio" value={year} options={["2024", "2025", "2026", "2027", "2028", "2029", "2030"]} onChange={setYear} />
        <SelectField label="Mes" value={month} options={["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]} onChange={setMonth} />
        <Text style={styles.helperText}>El backend solo permite generar el periodo cerrado permitido.</Text>
        <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Cargar empleados</Text></Pressable>
      </View>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={calculate}><Text style={styles.actionButtonText}>Calcular</Text></Pressable>
        <Pressable style={styles.actionButton} onPress={postPayroll}><Text style={styles.actionButtonText}>Postear Planilla</Text></Pressable>
      </ScrollView>
      {preview ? (
        <View style={styles.summaryBox}>
          <Text style={styles.cardTitle}>Preview</Text>
          {["salario_base", "horas_ot", "pago_horas_extra", "salario_bruto", "deducciones_trabajador", "impuesto_renta", "salario_neto", "costo_total_empresa"].map((key) => (
            <View key={key} style={styles.fieldRow}>
              <Text style={styles.fieldKey}>{key.replaceAll("_", " ")}</Text>
              <Text style={styles.fieldValue}>{formatValue(preview[key])}</Text>
            </View>
          ))}
        </View>
      ) : null}
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
    </View>
  );
}

function HRPayslipsView({
  initialRows,
  session
}: {
  initialRows: Record<string, unknown>[];
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [rows, setRows] = useState(initialRows);
  const [selected, setSelected] = useState<number | null>(null);
  const period = previousPayrollPeriod();
  const [year, setYear] = useState("");
  const [month, setMonth] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = ["id", "usuario", "year", "month", "salario_neto", "salario_bruto", "horas_extra", "generado_por"];
  const selectedRow = selected === null ? null : rows[selected] || null;

  async function load() {
    const params = new URLSearchParams({ page: "1", page_size: "50" });
    if (year) params.set("year", year);
    if (month) params.set("month", String(Number(month)));
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest(`/hr/payroll/payslips?${params.toString()}`, { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar colillas.");
    } finally {
      setBusy(false);
    }
  }

  async function openPdf() {
    if (!selectedRow) {
      setMessage("Seleccione una colilla.");
      return;
    }
    const params = new URLSearchParams({
      request_user: session.usuario,
      request_role: session.rol,
      target_user: formatValue(selectedRow.usuario)
    });
    const url = `${API_BASE_URL}/hr/payroll/mobile-payslip-pdf/${selectedRow.year}/${selectedRow.month}?${params.toString()}`;
    try {
      await Linking.openURL(url);
      setMessage("Abriendo descarga de colilla.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo abrir la colilla.");
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Colillas de Pago</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Anio" value={year || "Todos"} options={["Todos", "2024", "2025", "2026", "2027", "2028", "2029", "2030"]} onChange={(value) => setYear(value === "Todos" ? "" : value)} />
        <SelectField label="Mes" value={month || "Todos"} options={["Todos", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]} onChange={(value) => setMonth(value === "Todos" ? "" : value)} />
        <Text style={styles.helperText}>Periodo cerrado actual sugerido: {period.month}/{period.year}</Text>
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => { setYear(""); setMonth(""); }}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={openPdf}><Text style={styles.actionButtonText}>Descargar colilla</Text></Pressable>
      </ScrollView>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
    </View>
  );
}

function HRPoliciesView({
  initialRows,
  session
}: {
  initialRows: Record<string, unknown>[];
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const admin = isAdminSession(session);
  const [rows, setRows] = useState(initialRows);
  const [selected, setSelected] = useState<number | null>(null);
  const [categoria, setCategoria] = useState("");
  const [modalMode, setModalMode] = useState<"view" | "add" | "edit" | null>(null);
  const [form, setForm] = useState<Record<string, string>>({ categoria: "", titulo: "", articulo_ref: "", contenido: "", activo: "true" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const columns = ["id", "categoria", "titulo", "articulo_ref", "activo"];
  const selectedRow = selected === null ? null : rows[selected] || null;
  const categorias = ["", ...Array.from(new Set(rows.map((row) => formatValue(row.categoria)).filter((value) => value !== "-")))];

  async function load() {
    const params = new URLSearchParams({ solo_activas: "true" });
    if (categoria) params.set("categoria", categoria);
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest(`/hr/policies?${params.toString()}`, { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar politicas.");
    } finally {
      setBusy(false);
    }
  }

  function openPolicy(mode: "view" | "add" | "edit") {
    if (mode !== "add" && !selectedRow) {
      setMessage("Seleccione una politica.");
      return;
    }
    const source = mode === "add" ? {} : selectedRow || {};
    setForm({
      categoria: formatValue(source.categoria) === "-" ? "" : formatValue(source.categoria),
      titulo: formatValue(source.titulo) === "-" ? "" : formatValue(source.titulo),
      articulo_ref: formatValue(source.articulo_ref) === "-" ? "" : formatValue(source.articulo_ref),
      contenido: formatValue(source.contenido) === "-" ? "" : formatValue(source.contenido),
      activo: String(source.activo ?? true)
    });
    setModalMode(mode);
  }

  async function savePolicy() {
    if (!modalMode || modalMode === "view") return;
    setBusy(true);
    setMessage("");
    try {
      const body = { ...form, activo: form.activo === "true" };
      if (modalMode === "add") await apiRequest("/hr/policies", { method: "POST", body, session });
      else await apiRequest(`/hr/policies/${selectedRow?.id}`, { method: "PUT", body, session });
      setModalMode(null);
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar politica.");
    } finally {
      setBusy(false);
    }
  }

  async function deletePolicy() {
    if (!selectedRow) {
      setMessage("Seleccione una politica.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/hr/policies/${selectedRow.id}`, { method: "DELETE", session });
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo desactivar politica.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Politicas de la Empresa</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Categoria" value={categoria} options={categorias} onChange={setCategoria} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Cargar</Text></Pressable>
          <Pressable style={styles.modalClose} onPress={() => setCategoria("")}><Text style={styles.modalCloseText}>Limpiar</Text></Pressable>
        </View>
      </View>
      <HRMiniTable rows={rows} columns={columns} selectedIndex={selected} onSelect={setSelected} />
      <ScrollView horizontal contentContainerStyle={styles.actionBar}>
        <Pressable style={styles.actionButton} onPress={() => openPolicy("view")}><Text style={styles.actionButtonText}>Ver</Text></Pressable>
        {admin ? <Pressable style={styles.actionButton} onPress={() => openPolicy("add")}><Text style={styles.actionButtonText}>Agregar</Text></Pressable> : null}
        {admin ? <Pressable style={styles.actionButton} onPress={() => openPolicy("edit")}><Text style={styles.actionButtonText}>Editar</Text></Pressable> : null}
        {admin ? <Pressable style={styles.modalClose} onPress={deletePolicy}><Text style={styles.modalCloseText}>Eliminar</Text></Pressable> : null}
      </ScrollView>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
      <Modal visible={modalMode !== null} animationType="slide" onRequestClose={() => setModalMode(null)}>
        <SafeAreaView style={styles.modalScreen}>
          <View style={styles.modalHeader}><Text style={styles.modalTitle}>Politica</Text><Pressable style={styles.modalClose} onPress={() => setModalMode(null)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable></View>
          <ScrollView contentContainerStyle={styles.modalBody}>
            {["categoria", "titulo", "articulo_ref"].map((key) => (
              <View key={key} style={styles.formField}><Text style={styles.label}>{key.replaceAll("_", " ")}</Text><TextInput editable={modalMode !== "view"} style={[styles.input, modalMode === "view" && styles.readonlyInput]} value={form[key] || ""} onChangeText={(value) => setForm((f) => ({ ...f, [key]: value }))} /></View>
            ))}
            <Text style={styles.label}>Contenido</Text>
            <TextInput editable={modalMode !== "view"} multiline style={[styles.input, styles.multilineInput, modalMode === "view" && styles.readonlyInput]} value={form.contenido || ""} onChangeText={(contenido) => setForm((f) => ({ ...f, contenido }))} />
            {modalMode !== "view" ? <PrimaryButton label="Guardar" loading={busy} onPress={savePolicy} /> : null}
          </ScrollView>
        </SafeAreaView>
      </Modal>
    </View>
  );
}

function HRNewsView({
  initialPayload,
  session
}: {
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const admin = isAdminSession(session);
  const [news, setNews] = useState<Record<string, unknown>>(asRecord(initialPayload) || {});
  const [form, setForm] = useState<Record<string, string>>({
    noticia_1: formatValue(asRecord(initialPayload)?.noticia_1) === "-" ? "" : formatValue(asRecord(initialPayload)?.noticia_1),
    noticia_2: formatValue(asRecord(initialPayload)?.noticia_2) === "-" ? "" : formatValue(asRecord(initialPayload)?.noticia_2),
    noticia_3: formatValue(asRecord(initialPayload)?.noticia_3) === "-" ? "" : formatValue(asRecord(initialPayload)?.noticia_3),
    noticia_4: formatValue(asRecord(initialPayload)?.noticia_4) === "-" ? "" : formatValue(asRecord(initialPayload)?.noticia_4),
    noticia_5: formatValue(asRecord(initialPayload)?.noticia_5) === "-" ? "" : formatValue(asRecord(initialPayload)?.noticia_5)
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>("/noticias/latest", { session });
      setNews(payload);
      setForm({
        noticia_1: formatValue(payload.noticia_1) === "-" ? "" : formatValue(payload.noticia_1),
        noticia_2: formatValue(payload.noticia_2) === "-" ? "" : formatValue(payload.noticia_2),
        noticia_3: formatValue(payload.noticia_3) === "-" ? "" : formatValue(payload.noticia_3),
        noticia_4: formatValue(payload.noticia_4) === "-" ? "" : formatValue(payload.noticia_4),
        noticia_5: formatValue(payload.noticia_5) === "-" ? "" : formatValue(payload.noticia_5)
      });
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar noticias.");
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    setBusy(true);
    setMessage("");
    try {
      await apiRequest("/noticias", { method: "POST", body: form, session });
      setMessage("Noticias publicadas.");
      await load();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron publicar noticias.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>Noticias HHRR</Text>
      <View style={styles.summaryBox}>
        {[1, 2, 3, 4, 5].map((index) => {
          const value = news[`noticia_${index}`];
          return value ? <Text key={index} style={styles.helperText}>{formatValue(value)}</Text> : null;
        })}
      </View>
      {admin ? (
        <View style={styles.creditCard}>
          <Text style={styles.cardTitle}>Publicar noticias</Text>
          {[1, 2, 3, 4, 5].map((index) => {
            const key = `noticia_${index}`;
            return <TextInput key={key} style={styles.input} value={form[key] || ""} onChangeText={(value) => setForm((f) => ({ ...f, [key]: value }))} placeholder={`Noticia ${index}`} />;
          })}
          <PrimaryButton label="Publicar" loading={busy} onPress={publish} />
        </View>
      ) : null}
      <Pressable style={styles.modalClose} onPress={load}><Text style={styles.modalCloseText}>Actualizar</Text></Pressable>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={styles.error}>{message}</Text> : null}
    </View>
  );
}

function CreditControlMobile({
  clients,
  session
}: {
  clients: Record<string, unknown>[];
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const { labels, codes } = clientLabelsAndCodes({ data: clients });
  const [selectedClient, setSelectedClient] = useState("");
  const [creditExists, setCreditExists] = useState(false);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Record<string, string>>({
    termino_pago: "",
    limite_credito: "",
    moneda: "USD",
    estado_credito: "ACTIVE",
    hold_manual: "No",
    observaciones: ""
  });
  const [exposure, setExposure] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const selectedCode = selectedClient ? codes[selectedClient] || selectedClient.split(" - ")[0] : "";
  const readonly = creditExists && !editing;

  function update(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function clearCreditData(keepClient = true) {
    if (!keepClient) setSelectedClient("");
    setCreditExists(false);
    setEditing(false);
    setExposure(null);
    setForm({
      termino_pago: "",
      limite_credito: "",
      moneda: "USD",
      estado_credito: "ACTIVE",
      hold_manual: "No",
      observaciones: ""
    });
  }

  async function searchClient() {
    if (!selectedCode) {
      setMessage("Seleccione un cliente.");
      return;
    }

    setBusy(true);
    setMessage("");
    setExposure(null);
    try {
      const credit = await apiRequest<Record<string, unknown>>(`/cliente-credito/${selectedCode}`, { session });
      const exists = Boolean(credit.exists);
      if (!exists) {
        clearCreditData(true);
        setEditing(true);
        setMessage("Este cliente no tiene terminos crediticios asignados. Complete la asignacion inicial.");
        return;
      }

      const data = asRecord(credit.data) || credit;
      setCreditExists(true);
      setEditing(false);
      setForm({
        termino_pago: formatValue(data.termino_pago) === "-" ? "" : formatValue(data.termino_pago),
        limite_credito: formatValue(data.limite_credito) === "-" ? "" : formatValue(data.limite_credito),
        moneda: formatValue(data.moneda) === "-" ? "USD" : formatValue(data.moneda),
        estado_credito: formatValue(data.estado_credito ?? data.estado) === "-" ? "ACTIVE" : formatValue(data.estado_credito ?? data.estado),
        hold_manual: data.hold_manual ? "Si" : "No",
        observaciones: formatValue(data.observaciones) === "-" ? "" : formatValue(data.observaciones)
      });

      const nextExposure = await apiRequest<Record<string, unknown>>(`/cliente-credito/exposure/${selectedCode}`, { session });
      setExposure(nextExposure);
      setMessage("Credito y exposicion cargados.");
    } catch (err) {
      clearCreditData(true);
      setMessage(err instanceof Error ? err.message : "No se pudo consultar el credito del cliente.");
    } finally {
      setBusy(false);
    }
  }

  function validateCreditForm() {
    if (!selectedCode) return "Seleccione un cliente.";
    if (!form.termino_pago.trim()) return "Ingrese termino de pago.";
    if (!form.limite_credito.trim()) return "Ingrese limite de credito.";
    const term = Number(form.termino_pago);
    const limit = Number(form.limite_credito);
    if (!Number.isFinite(term) || term < 0) return "Termino de pago invalido.";
    if (!Number.isFinite(limit) || limit < 0) return "Limite de credito invalido.";
    return "";
  }

  async function saveCredit() {
    const validation = validateCreditForm();
    if (validation) {
      setMessage(validation);
      return;
    }

    const payload = {
      codigo_cliente: selectedCode,
      termino_pago: Number(form.termino_pago),
      limite_credito: Number(form.limite_credito),
      moneda: form.moneda || "USD",
      estado_credito: form.estado_credito || "ACTIVE",
      hold_manual: form.hold_manual === "Si",
      observaciones: form.observaciones
    };

    setBusy(true);
    setMessage("");
    try {
      if (creditExists) {
        await apiRequest(`/cliente-credito/${selectedCode}`, { method: "PUT", body: payload, session });
      } else {
        await apiRequest("/cliente-credito/", { method: "POST", body: payload, session });
      }
      setMessage(creditExists ? "Condiciones crediticias actualizadas." : "Configuracion crediticia creada.");
      await searchClient();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar el credito.");
    } finally {
      setBusy(false);
    }
  }

  function deleteCredit() {
    if (!selectedCode || !creditExists) return;
    Alert.alert("Confirmar", "Eliminar configuracion crediticia de este cliente?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Eliminar",
        style: "destructive",
        onPress: async () => {
          setBusy(true);
          setMessage("");
          try {
            await apiRequest(`/cliente-credito/${selectedCode}`, { method: "DELETE", session });
            clearCreditData(true);
            setMessage("Configuracion crediticia eliminada.");
          } catch (err) {
            setMessage(err instanceof Error ? err.message : "No se pudo eliminar el credito.");
          } finally {
            setBusy(false);
          }
        }
      }
    ]);
  }

  const semaforo = formatValue(exposure?.semaforo);
  const trend = asRecord(exposure?.payment_trend);

  return (
    <View style={styles.creditShell}>
      <Text style={styles.cardTitle}>Credit Control</Text>
      <View style={styles.financeFilterBox}>
        <SelectField label="Cliente" value={selectedClient} options={labels} onChange={setSelectedClient} />
        <View style={styles.financeFilterActions}>
          <Pressable style={styles.actionButton} onPress={searchClient}>
            <Text style={styles.actionButtonText}>Buscar</Text>
          </Pressable>
          <Pressable style={styles.modalClose} onPress={() => clearCreditData(false)}>
            <Text style={styles.modalCloseText}>Limpiar</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.creditCard}>
        <View style={styles.creditHeader}>
          <Text style={styles.cardTitle}>Condiciones crediticias</Text>
          {creditExists ? (
            <View style={[styles.creditStatusBadge, form.hold_manual === "Si" || form.estado_credito === "HOLD" ? styles.creditStatusHold : styles.creditStatusActive]}>
              <Text style={styles.creditStatusText}>{form.hold_manual === "Si" ? "HOLD MANUAL" : form.estado_credito || "ACTIVE"}</Text>
            </View>
          ) : null}
        </View>

        <Text style={styles.label}>Termino de pago (dias)</Text>
        <TextInput
          editable={!readonly}
          keyboardType="numeric"
          value={form.termino_pago}
          onChangeText={(value) => update("termino_pago", value)}
          style={[styles.input, readonly && styles.readonlyInput]}
        />

        <Text style={styles.label}>Limite de credito</Text>
        <TextInput
          editable={!readonly}
          keyboardType="decimal-pad"
          value={form.limite_credito}
          onChangeText={(value) => update("limite_credito", value)}
          style={[styles.input, readonly && styles.readonlyInput]}
        />

        {readonly ? (
          <>
            <Text style={styles.label}>Moneda</Text>
            <TextInput editable={false} value={form.moneda} style={[styles.input, styles.readonlyInput]} />
            <Text style={styles.label}>Estado</Text>
            <TextInput editable={false} value={form.estado_credito} style={[styles.input, styles.readonlyInput]} />
            <Text style={styles.label}>Hold manual</Text>
            <TextInput editable={false} value={form.hold_manual} style={[styles.input, styles.readonlyInput]} />
          </>
        ) : (
          <>
            <SelectField label="Moneda" value={form.moneda} options={["USD", "CRC", "EUR"]} onChange={(value) => update("moneda", value)} />
            <SelectField label="Estado" value={form.estado_credito} options={["ACTIVE", "INACTIVE", "HOLD"]} onChange={(value) => update("estado_credito", value)} />
            <SelectField label="Hold manual" value={form.hold_manual} options={["No", "Si"]} onChange={(value) => update("hold_manual", value)} />
          </>
        )}

        <Text style={styles.label}>Observaciones</Text>
        <TextInput
          editable={!readonly}
          multiline
          value={form.observaciones}
          onChangeText={(value) => update("observaciones", value)}
          style={[styles.input, styles.multilineInput, readonly && styles.readonlyInput]}
        />

        <View style={styles.financeFilterActions}>
          {creditExists && !editing ? (
            <Pressable style={styles.actionButton} onPress={() => setEditing(true)}>
              <Text style={styles.actionButtonText}>Editar</Text>
            </Pressable>
          ) : (
            <PrimaryButton label={creditExists ? "Guardar cambios" : "Asignar credito"} loading={busy} onPress={saveCredit} />
          )}
          {creditExists ? (
            <Pressable style={styles.modalClose} onPress={deleteCredit}>
              <Text style={styles.modalCloseText}>Eliminar</Text>
            </Pressable>
          ) : null}
        </View>
      </View>

      <View style={styles.creditCard}>
        <View style={styles.creditHeader}>
          <Text style={styles.cardTitle}>Exposicion Crediticia</Text>
          {exposure ? (
            <View style={[styles.creditSemaphore, semaforo === "VERDE" ? styles.creditGreen : semaforo === "AMARILLO" ? styles.creditYellow : styles.creditRed]}>
              <Text style={styles.creditSemaphoreText}>
                {semaforo === "VERDE" ? "DISPONIBLE" : semaforo === "AMARILLO" ? "CRITICO" : "SOBREGIRADO"}
              </Text>
            </View>
          ) : null}
        </View>

        <View style={styles.kpiGrid}>
          <View style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>Total facturado</Text>
            <Text style={styles.kpiValue}>{formatValue(exposure?.total_facturado)}</Text>
          </View>
          <View style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>Disponible</Text>
            <Text style={styles.kpiValue}>{formatValue(exposure?.disponible)}</Text>
          </View>
          <View style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>Exposicion</Text>
            <Text style={styles.kpiValue}>{formatValue(exposure?.exposicion)}</Text>
          </View>
          <View style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>Avg dias de pago</Text>
            <Text style={styles.kpiValue}>{formatValue(trend?.avg_days_to_pay)}</Text>
          </View>
        </View>
        <Text style={styles.helperText}>Payment trend: {formatValue(trend?.trend)}</Text>
      </View>

      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={message.includes("no tiene") ? styles.helperText : styles.error}>{message}</Text> : null}
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
  calendarDay: { alignItems: "center", borderRadius: 6, height: 38, justifyContent: "center", width: "14.28%" },
  calendarDayActive: { backgroundColor: BLUE },
  calendarDayMuted: { color: "#98A2B3" },
  calendarDayText: { color: "#101828", fontSize: 13, fontWeight: "800" },
  calendarDayTextActive: { color: "white" },
  calendarGrid: { flexDirection: "row", flexWrap: "wrap", marginTop: 8 },
  calendarHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 10 },
  calendarOverlay: { alignItems: "center", backgroundColor: "rgba(15, 23, 42, 0.45)", flex: 1, justifyContent: "center", padding: 18 },
  calendarPanel: { backgroundColor: "white", borderRadius: 8, padding: 14, width: "100%" },
  calendarTitle: { color: "#101828", fontSize: 17, fontWeight: "900" },
  calendarWeek: { flexDirection: "row" },
  calendarWeekday: { color: "#667085", fontSize: 11, fontWeight: "900", textAlign: "center", width: "14.28%" },
  content: { flex: 1 },
  contentInner: { padding: 14, paddingBottom: 32 },
  creditCard: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 12,
    padding: 12
  },
  creditGreen: { backgroundColor: "#D4EDDA" },
  creditHeader: { alignItems: "center", flexDirection: "row", gap: 10, justifyContent: "space-between", marginBottom: 8 },
  creditRed: { backgroundColor: "#F8D7DA" },
  creditSemaphore: { borderRadius: 6, paddingHorizontal: 10, paddingVertical: 6 },
  creditSemaphoreText: { color: "#101828", fontSize: 11, fontWeight: "900" },
  creditShell: { marginTop: 12 },
  creditStatusActive: { backgroundColor: "#D4EDDA" },
  creditStatusBadge: { borderRadius: 6, paddingHorizontal: 9, paddingVertical: 5 },
  creditStatusHold: { backgroundColor: "#F8D7DA" },
  creditStatusText: { color: "#101828", fontSize: 11, fontWeight: "900" },
  creditYellow: { backgroundColor: "#FFF3CD" },
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
  informesHomeActions: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
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
  quotationPreviewInput: { minHeight: 260, textAlignVertical: "top" },
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
  commercialStatusRow: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 10 },
  statusChip: {
    backgroundColor: "white",
    borderColor: BORDER,
    borderRadius: 999,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 8
  },
  statusChipActive: { backgroundColor: BLUE, borderColor: BLUE },
  statusChipText: { color: "#344054", fontSize: 12, fontWeight: "800" },
  statusChipTextActive: { color: "white" },
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
  timePart: { flex: 1 },
  timeRow: { flexDirection: "row", gap: 10 },
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

import * as LocalAuthentication from "expo-local-authentication";
import * as FileSystem from "expo-file-system/legacy";
import * as DocumentPicker from "expo-document-picker";
import * as IntentLauncher from "expo-intent-launcher";
import * as Notifications from "expo-notifications";
import * as Sharing from "expo-sharing";
import * as SecureStore from "expo-secure-store";
import AsyncStorage from "@react-native-async-storage/async-storage";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  AppState,
  Image,
  Linking,
  Modal,
  Platform,
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

import { API_BASE_URL, apiRequest, confirmTotp, login, LoginResponse, Session, verifyTotp } from "./src/api/client";
import { AuthProvider, useAuth } from "./src/auth/AuthContext";
import { AppModule, AppSection, TableAction, getAllowedModules } from "./src/config/modules";
import { ONG_QUESTIONNAIRES, LograQuestion, LograQuestionnaire } from "./src/config/lograQuestionnaires";

const BLUE = "#003A75";
const BORDER = "#D7DEE8";
const CREDS_KEY = "erp_som_saved_credentials";
const OFFLINE_QUEUE_KEY = "erp_som_offline_queue";
const ONG_NOTIFICATION_IDS_KEY = "erp_som_logra_notification_ids";
const ERP_NOTIFICATION_IDS_KEY = "erp_som_business_notification_ids";
const ONG_AUTOSAVE_DRAFT_KEY = "erp_som_ong_autosave_draft";

const COMPANIES = [
  { code: "MSL-CR", name: "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL", label: "MSL" },
  { code: "MMS-CR", name: "MMS MARITIME MASTER SURVEYORS SRL", label: "MMS" }
];
const DEFAULT_COMPANY = COMPANIES[0];
const MOBILE_APP_VERSION = "1.7.18";

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false
  })
});

type SavedCredentials = {
  usuario: string;
  password: string;
  company_code?: string;
};

type OfflineQueueItem = {
  id: string;
  path: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  session: Session;
  label: string;
  createdAt: string;
  lastError?: string;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : null;
}

function isNetworkFailure(err: unknown) {
  const message = err instanceof Error ? err.message : String(err || "");
  return /network request failed|failed to fetch|network|internet|timeout|timed out|offline/i.test(message);
}

async function readOfflineQueue(): Promise<OfflineQueueItem[]> {
  try {
    const raw = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((item) => asRecord(item)) as OfflineQueueItem[] : [];
  } catch {
    return [];
  }
}

async function writeOfflineQueue(items: OfflineQueueItem[]) {
  await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(items));
}

async function queueOfflineRequest({
  path,
  method,
  body,
  session,
  label
}: {
  path: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  session: Session;
  label: string;
}) {
  const queue = await readOfflineQueue();
  const dedupeKey = `${method} ${path} ${label}`;
  const item: OfflineQueueItem = {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    path,
    method,
    body,
    session,
    label,
    createdAt: new Date().toISOString()
  };
  const nextQueue = queue.filter((queued) => `${queued.method} ${queued.path} ${queued.label}` !== dedupeKey);
  await writeOfflineQueue([...nextQueue, item]);
  return item;
}

async function offlineApiRequest<T>(
  path: string,
  options: {
    method: "POST" | "PUT" | "PATCH" | "DELETE";
    body?: unknown;
    session: Session;
    offlineLabel: string;
  }
): Promise<T | { queuedOffline: true; queuedId: string }> {
  try {
    return await apiRequest<T>(path, options);
  } catch (err) {
    if (!isNetworkFailure(err)) throw err;
    const queued = await queueOfflineRequest({
      path,
      method: options.method,
      body: options.body,
      session: options.session,
      label: options.offlineLabel
    });
    return { queuedOffline: true, queuedId: queued.id };
  }
}

function isQueuedOffline(value: unknown): value is { queuedOffline: true; queuedId: string } {
  return Boolean(asRecord(value)?.queuedOffline);
}

async function syncOfflineQueue(currentSession?: Session | null) {
  const queue = await readOfflineQueue();
  if (!queue.length) return { sent: 0, pending: 0, errors: [] as string[] };

  const remaining: OfflineQueueItem[] = [];
  const errors: string[] = [];
  let sent = 0;

  for (const item of queue) {
    try {
      await apiRequest(item.path, {
        method: item.method,
        body: item.body,
        session: item.session || currentSession
      });
      sent += 1;
    } catch (err) {
      const message = err instanceof Error ? err.message : "No se pudo sincronizar";
      remaining.push({ ...item, lastError: message });
      errors.push(`${item.label}: ${message}`);
    }
  }

  await writeOfflineQueue(remaining);
  return { sent, pending: remaining.length, errors };
}

function withTimeout<T>(promise: Promise<T>, timeoutMs: number, message: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(message)), timeoutMs);
    promise
      .then((value) => {
        clearTimeout(timer);
        resolve(value);
      })
      .catch((err) => {
        clearTimeout(timer);
        reject(err);
      });
  });
}

function useOfflineSync(session: Session | null) {
  const [pendingCount, setPendingCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState("");

  async function refreshCount() {
    const queue = await readOfflineQueue();
    setPendingCount(queue.length);
  }

  async function syncNow(showMessage = true) {
    if (!session || syncing) return;
    setSyncing(true);
    try {
      const result = await syncOfflineQueue(session);
      setPendingCount(result.pending);
      if (showMessage) {
        if (result.sent && !result.pending) setMessage(`Sincronizado: ${result.sent} pendiente(s) enviados.`);
        else if (result.sent || result.pending) setMessage(`Sync: ${result.sent} enviados, ${result.pending} pendientes.`);
        else setMessage("No hay datos pendientes por sincronizar.");
      }
    } finally {
      setSyncing(false);
    }
  }

  useEffect(() => {
    refreshCount();
  }, [session?.usuario]);

  useEffect(() => {
    if (!session) return;
    const timer = setInterval(() => {
      readOfflineQueue().then((queue) => {
        setPendingCount(queue.length);
        if (queue.length) syncNow(false);
      });
    }, 10000);
    return () => clearInterval(timer);
  }, [session?.usuario, syncing]);

  return { pendingCount, syncing, message, setMessage, refreshCount, syncNow };
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

function pickAccountingValue(row: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    const value = row[key];
    if (value !== null && value !== undefined && value !== "") return value;
  }
  return undefined;
}

function normalizeAccountingFlatRow(row: Record<string, unknown>) {
  const accountCode = pickAccountingValue(row, ["account_code", "cuenta_codigo", "codigo_cuenta"]);
  const accountName = pickAccountingValue(row, ["account_name", "cuenta_nombre", "nombre_cuenta"]);
  const account = pickAccountingValue(row, ["account", "cuenta_contable"]);
  const accountLabel = [accountCode, accountName].map(formatValue).filter((value) => value !== "-").join(" ");
  const lineDescription = pickAccountingValue(row, [
    "line_description",
    "detalle",
    "detail",
    "description",
    "entry_description"
  ]);

  return {
    ...row,
    entry_date: pickAccountingValue(row, ["entry_date", "fecha", "date", "created_at"]),
    entry_id: pickAccountingValue(row, ["entry_id", "asiento", "id"]),
    period: pickAccountingValue(row, ["period", "periodo"]),
    origin: pickAccountingValue(row, ["origin", "origen"]),
    origin_id: pickAccountingValue(row, ["origin_id", "origen_id"]),
    workflow_status: pickAccountingValue(row, ["workflow_status", "estado"]),
    line_id: pickAccountingValue(row, ["line_id", "linea_id"]),
    account_code: accountCode,
    account_name: accountName,
    account: account || accountLabel,
    line_description: lineDescription,
    debit: pickAccountingValue(row, ["debit", "debe"]),
    credit: pickAccountingValue(row, ["credit", "haber"])
  };
}

function flattenAccountingLedger(payload: unknown): Record<string, unknown>[] {
  return extractRows(payload).flatMap((entry) => {
    const lines = Array.isArray(entry.lines) ? entry.lines : [];
    if (!lines.length) return [normalizeAccountingFlatRow(entry)];

    return lines
      .map((line) => asRecord(line))
      .filter(Boolean)
      .map((line) => ({
        ...normalizeAccountingFlatRow({
          ...entry,
          ...line,
          entry_id: pickAccountingValue(entry, ["entry_id", "asiento", "id"]),
          entry_date: pickAccountingValue(entry, ["entry_date", "fecha", "date", "created_at"]),
          period: pickAccountingValue(entry, ["period", "periodo"]),
          origin: pickAccountingValue(entry, ["origin", "origen"]),
          origin_id: pickAccountingValue(entry, ["origin_id", "origen_id"]),
          entry_description: pickAccountingValue(entry, ["description", "entry_description"]),
          line_description: pickAccountingValue(line || {}, ["line_description", "detalle", "detail", "description"])
        })
      }));
  });
}

function rowsForSection(sectionKey: string | undefined, payload: unknown) {
  if (sectionKey === "accounting") return flattenAccountingLedger(payload);
  return extractRows(payload);
}

function normalizeOngReviewRows(payload: unknown) {
  return extractRows(payload)
    .filter((row) => formatValue(row.title).trim().toLowerCase() !== "ong - agenda")
    .sort((a, b) => {
      const aTime = Date.parse(formatValue(a.updated_at));
      const bTime = Date.parse(formatValue(b.updated_at));
      if (Number.isFinite(aTime) && Number.isFinite(bTime) && aTime !== bTime) return bTime - aTime;
      return Number(formatValue(b.id)) - Number(formatValue(a.id));
    });
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

function companyByCode(code?: string) {
  return COMPANIES.find((company) => company.code === code) || DEFAULT_COMPANY;
}

function companyPrefix(code?: string) {
  return companyByCode(code).code.split("-")[0] || "MSL";
}

function withCompanySession(session: Session, companyCode?: string): Session {
  const company = companyByCode(companyCode);
  return { ...session, company_code: company.code, company_name: company.name };
}

function LoginScreen() {
  const { setSession } = useAuth();
  const [usuario, setUsuario] = useState("");
  const [password, setPassword] = useState("");
  const [companyCode, setCompanyCode] = useState(DEFAULT_COMPANY.code);
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
    await SecureStore.setItemAsync(CREDS_KEY, JSON.stringify({ usuario, password, company_code: companyCode }), {
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
      setCompanyCode(companyByCode(saved.company_code).code);

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
      await setSession(withCompanySession(response, companyCode));
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
            <SelectField
              label="Empresa"
              value={companyByCode(companyCode).label}
              options={COMPANIES.map((company) => company.label)}
              onChange={(label) => setCompanyCode(COMPANIES.find((company) => company.label === label)?.code || DEFAULT_COMPANY.code)}
            />

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
  const offlineSync = useOfflineSync(session);

  const modules = useMemo(
    () => getAllowedModules(session?.modules.map((module) => module.code) ?? [], session?.rol ?? ""),
    [session?.modules, session?.rol]
  );

  useEffect(() => {
    if (!activeModule && modules.length > 0) setActiveModule(modules[0]);
  }, [activeModule, modules]);

  useEffect(() => {
    if (!session) return;
    // Disabled while mobile stability is reviewed. Business alerts must never close the ERP app.
  }, [session]);

  useEffect(() => {
    if (activeModule?.code !== "informes" || activeSection || !session) return;
    const defaultSection = activeModule.sections.find((section) => section.key === "status-informes")
      || activeModule.sections.find((section) => section.key === "logra")
      || activeModule.sections[0];
    if (defaultSection) {
      setActiveSection(defaultSection);
      setPayload({ data: [] });
      setError("");
    }
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
            <Text style={styles.headerSub}>App {MOBILE_APP_VERSION}</Text>
            <Text style={styles.headerSub}>
              {session.usuario} · {session.rol}
            </Text>
          </View>
          <Pressable style={styles.headerButton} onPress={logout}>
            <Text style={styles.headerButtonText}>Salir</Text>
          </Pressable>
        </View>
        <View style={styles.syncRow}>
          <Pressable style={styles.syncButton} onPress={() => offlineSync.syncNow(true)} disabled={offlineSync.syncing}>
            <Text style={styles.syncButtonText}>
              {offlineSync.syncing ? "Sincronizando..." : `Sync${offlineSync.pendingCount ? ` (${offlineSync.pendingCount})` : ""}`}
            </Text>
          </Pressable>
          {offlineSync.message ? <Text style={styles.syncMessage}>{offlineSync.message}</Text> : null}
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
            {activeModule.code === "master_data" && session ? (
              <MasterDataHomeActions module={activeModule} session={session} onReload={() => activeSection && openSection(activeSection)} />
            ) : null}
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

  if ((moduleCode === "portia" || moduleCode === "qa_som") && section) {
    return <PortiaSectionMobile section={section} initialPayload={payload} session={session} />;
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

function PortiaSectionMobile({
  section,
  initialPayload,
  session
}: {
  section: AppSection;
  initialPayload: unknown;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
}) {
  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState("erp");
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [qaRows, setQaRows] = useState<Record<string, unknown>[]>([]);
  const [searchText, setSearchText] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");

  const suggestions = useMemo(() => {
    const rows = extractRows(initialPayload);
    if (rows.length) return rows.map((row) => formatValue(row.question || row.value || row.text)).filter((item) => item !== "-");
    const obj = asRecord(initialPayload);
    const data = obj?.data;
    return Array.isArray(data) ? data.map((item) => formatValue(item)).filter((item) => item !== "-") : [];
  }, [initialPayload]);

  useEffect(() => {
    setMessage("");
    setAnswer("");
    setAppliedSearch("");
    if (section.key !== "portia-qa") return;
    const rows = extractRows(initialPayload);
    if (rows.length) {
      setQaRows(rows);
      return;
    }
    apiRequest<Record<string, unknown>>("/portia/qa", { session })
      .then((payload) => setQaRows(extractRows(payload)))
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo cargar Q&A SOM."));
  }, [section.key, initialPayload, session.usuario]);

  async function askPortia(nextQuestion?: string, nextScope = scope) {
    const cleanQuestion = (nextQuestion ?? question).trim();
    if (!cleanQuestion) {
      setMessage("Escriba una pregunta para PORTIA.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>("/portia/ask", {
        method: "POST",
        session,
        body: { question: cleanQuestion, scope: nextScope }
      });
      setQuestion(cleanQuestion);
      setAnswer(formatValue(payload.answer));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo responder.");
    } finally {
      setBusy(false);
    }
  }

  const filteredQa = useMemo(() => {
    const term = appliedSearch.trim().toLowerCase();
    if (!term) return qaRows;
    return qaRows.filter((row) => {
      const text = `${formatValue(row.category)} ${formatValue(row.question)} ${formatValue(row.answer)}`.toLowerCase();
      return text.includes(term);
    });
  }, [qaRows, appliedSearch]);

  if (section.key === "portia-qa") {
    return (
      <View style={styles.tableShell}>
        <Text style={styles.cardTitle}>Q&A SOM</Text>
        <Text style={styles.helperText}>Manual funcional por modulo. Escriba un termino y presione Buscar.</Text>
        <View style={styles.financeFilterBox}>
          <Text style={styles.label}>Buscar en la base Q&A</Text>
          <TextInput
            style={styles.input}
            value={searchText}
            onChangeText={setSearchText}
            placeholder="Ej. draft ballast, collections pagos, agregar servicio"
            returnKeyType="search"
            onSubmitEditing={() => setAppliedSearch(searchText)}
          />
          <View style={styles.financeFilterActions}>
            <Pressable style={styles.actionButton} onPress={() => setAppliedSearch(searchText)}>
              <Text style={styles.actionButtonText}>Buscar</Text>
            </Pressable>
            <Pressable
              style={styles.modalClose}
              onPress={() => {
                setSearchText("");
                setAppliedSearch("");
              }}
            >
              <Text style={styles.modalCloseText}>Limpiar</Text>
            </Pressable>
          </View>
        </View>
        <Text style={styles.tableCount}>{filteredQa.length} resultado(s)</Text>
        {message ? <Text style={styles.error}>{message}</Text> : null}
        <View style={styles.list}>
          {filteredQa.slice(0, 80).map((row, index) => (
            <Pressable
              key={`${formatValue(row.category)}-${index}`}
              style={styles.rowCard}
              onPress={() => setAnswer(formatValue(row.answer))}
            >
              <Text style={styles.kpiLabel}>{formatValue(row.category)}</Text>
              <Text style={styles.rowTitle}>{formatValue(row.question)}</Text>
              <Text style={styles.helperText} numberOfLines={3}>{formatValue(row.answer)}</Text>
            </Pressable>
          ))}
        </View>
        {answer ? (
          <View style={styles.summaryBox}>
            <Text style={styles.cardTitle}>Respuesta seleccionada</Text>
            <Text style={styles.helperText}>{answer}</Text>
          </View>
        ) : null}
      </View>
    );
  }

  return (
    <View style={styles.tableShell}>
      <Text style={styles.cardTitle}>PORTIA SOM</Text>
      <Text style={styles.helperText}>Consulta datos del ERP, el manual Q&A o preguntas generales si el backend tiene IA configurada.</Text>
      <View style={styles.financeFilterBox}>
        <SelectField
          label="Alcance"
          value={scope}
          options={["erp", "qa", "general_chat"]}
          onChange={setScope}
        />
        <Text style={styles.label}>Pregunta</Text>
        <TextInput
          multiline
          style={[styles.input, styles.multilineInput]}
          value={question}
          onChangeText={setQuestion}
          placeholder="Ej. Resume el estado financiero actual"
        />
        <PrimaryButton label="Preguntar a PORTIA" loading={busy} onPress={() => askPortia()} />
      </View>
      {suggestions.length ? (
        <View style={styles.list}>
          <Text style={styles.cardTitle}>Consultas sugeridas</Text>
          {suggestions.slice(0, 20).map((item, index) => (
            <Pressable key={`${item}-${index}`} style={styles.rowCard} onPress={() => askPortia(item, "erp")}>
              <Text style={styles.rowTitle}>{item}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      {answer ? (
        <View style={styles.summaryBox}>
          <Text style={styles.cardTitle}>Respuesta de PORTIA</Text>
          <Text style={styles.helperText}>{answer}</Text>
        </View>
      ) : null}
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
  group: "Informe contenedor" | "Informe buque" | "Certificados" | "ONG";
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
    idField: "draft_report_number",
    detailEndpoint: "/draft-survey/unified/{id}",
    updateEndpoint: "/draft-survey/unified/{id}",
    createEndpoint: "/draft-survey-headers/",
    statusField: "status",
    columns: ["draft_report_number", "client", "port", "country", "continent", "year", "month", "status"],
    filters: ["status", "client", "port", "country", "continent", "draft_report_number"],
    actions: [
      { key: "excel", label: "Excel PDF", endpoint: "/draft-survey-excel/generate-pdf/{id}", file: true },
      { key: "word", label: "Word PDF", endpoint: "/draft-survey-word/generate/{id}", file: true },
      { key: "final", label: "Final PDF", endpoint: "/draft-survey-final/generate/{id}", file: true },
      { key: "presentation", label: "Presentacion PDF", endpoint: "/draft-survey-word/presentation/{id}", file: true },
      { key: "unified", label: "Unified PDF", endpoint: "/draft-survey-final/unified/{id}", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/draft-survey/{id}/approve", method: "PUT" },
      { key: "reject", label: "Rechazar", endpoint: "/draft-survey/{id}/reject", method: "PUT" }
    ]
  },
  bunker: {
    title: "Vessel Bunker",
    idField: "id",
    detailEndpoint: "/vessel-bunker-reports/{id}",
    updateEndpoint: "/vessel-bunker-reports/{id}",
    createEndpoint: "/vessel-bunker-reports/",
    statusField: "status",
    columns: ["id", "bunker_cert_no", "ship_name", "client", "port", "country", "report_date", "status"],
    filters: ["status", "client", "ship_name", "port", "country", "bunker_cert_no"],
    actions: [
      { key: "excel", label: "Excel", endpoint: "/vessel-bunker-excel/generate/{id}", file: true },
      { key: "pdf", label: "Final PDF", endpoint: "/vessel-bunker-excel/generate-pdf/{id}", file: true },
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
    columns: ["id", "report_number", "vessel", "requested_by", "port", "country", "service_start_date", "status"],
    filters: ["status", "requested_by", "vessel", "port", "country", "report_number"],
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
    columns: ["id", "report_number", "vessel", "client", "port", "country", "report_date", "status"],
    filters: ["status", "customer", "vessel", "port", "country"],
    actions: [
      { key: "word", label: "Word", endpoint: "/vessel-crane-inspection-reports/{id}/generate-word", file: true },
      { key: "presentation", label: "Presentacion PDF", endpoint: "/vessel-crane-inspection-reports/{id}/presentation", file: true },
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
      { key: "approve", label: "Aprobar", endpoint: "/port-captancy-reports/{report_number}", method: "PUT", body: { action: "approve" } },
      { key: "reject", label: "Rechazar", endpoint: "/port-captancy-reports/{report_number}", method: "PUT", body: { action: "reject" } }
    ]
  },
  "weight-certificate": {
    title: "Weight Certificate",
    idField: "id",
    detailEndpoint: "/weight-certificates/{id}",
    updateEndpoint: "/weight-certificates/{id}",
    createEndpoint: "/weight-certificates",
    statusField: "status",
    columns: ["id", "report_number", "vessel", "port", "country", "date", "status"],
    filters: ["status", "client", "vessel", "port", "country"],
    actions: [
      { key: "word", label: "Word", endpoint: "/weight-certificates/{id}/word", file: true },
      { key: "pdf", label: "PDF", endpoint: "/weight-certificates/{id}/pdf", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/weight-certificates/{id}", method: "PUT", body: { action: "approve" } },
      { key: "reject", label: "Rechazar", endpoint: "/weight-certificates/{id}", method: "PUT", body: { action: "reject" } }
    ]
  },
  "holds-certificate": {
    title: "Vessel Holds Inspection Certificate",
    idField: "id",
    detailEndpoint: "/vessel-holds-inspection-certificates/{id}",
    updateEndpoint: "/vessel-holds-inspection-certificates/{id}",
    createEndpoint: "/vessel-holds-inspection-certificates",
    statusField: "status",
    columns: ["id", "report_number", "vessel", "port", "country", "date", "status"],
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
    columns: ["id", "report_no", "vessel", "port", "country", "date", "status"],
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
    columns: ["id", "report_no", "vessel", "customer", "port", "country", "date", "status"],
    filters: ["status", "customer", "vessel", "port", "country"],
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
    createEndpoint: "/lashing-certificates/",
    statusField: "status",
    columns: ["id", "report_no", "customer", "flat_rack_container", "cargo_type", "port", "country", "date", "status"],
    filters: ["status", "customer", "flat_rack_container", "cargo_type", "port", "country"],
    actions: [
      { key: "word", label: "Word", endpoint: "/lashing-certificates/{id}/word", file: true },
      { key: "pdf", label: "PDF", endpoint: "/lashing-certificates/{id}/pdf", file: true },
      { key: "approve", label: "Aprobar", endpoint: "/lashing-certificates/{id}", method: "PUT", body: { status: "Approve" } },
      { key: "reject", label: "Rechazar", endpoint: "/lashing-certificates/{id}", method: "PUT", body: { status: "Reject" } }
    ]
  },
  logra: {
    title: "Informe ONG",
    idField: "id",
    detailEndpoint: "/logra-reports/{id}",
    updateEndpoint: "/logra-reports",
    createEndpoint: "/logra-reports",
    statusField: "status",
    columns: ["id", "title", "category", "status", "attachment_count", "updated_at"],
    filters: ["title", "category", "status", "created_by"],
    actions: [
      { key: "logra-word", label: "Exportar Word", endpoint: "" },
      { key: "logra-pdf", label: "Exportar PDF", endpoint: "" }
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

function mimeFromFilename(filename: string, fallback = "application/octet-stream") {
  const lower = filename.toLowerCase();
  if (lower.endsWith(".pdf")) return "application/pdf";
  if (lower.endsWith(".html") || lower.endsWith(".htm")) return "text/html";
  if (lower.endsWith(".xlsx")) return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
  if (lower.endsWith(".xls")) return "application/vnd.ms-excel";
  if (lower.endsWith(".docx")) return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (lower.endsWith(".doc")) return "application/msword";
  if (lower.endsWith(".png")) return "image/png";
  if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
  if (lower.endsWith(".webp")) return "image/webp";
  if (lower.endsWith(".txt")) return "text/plain";
  return fallback;
}

function escapeHtml(value: unknown) {
  return formatValue(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function lograSectionLabel(section: string) {
  return section === "critical_questions" ? "Preguntas de apertura" : section === "detailed_questions" ? "Preguntas por tema" : section;
}

function orderedLograAnswers(payload: Record<string, unknown>) {
  const rawAnswers = Array.isArray(payload.answers) ? payload.answers : [];
  const answers = new Map<string, Record<string, unknown>>();
  rawAnswers.forEach((item) => {
    const record = asRecord(item);
    if (!record) return;
    const key = `${formatValue(record.form_slug)}|${formatValue(record.section)}|${formatValue(record.item_key)}`;
    answers.set(key, record);
  });
  const ordered: Array<{ form: LograQuestionnaire; section: "critical_questions" | "detailed_questions"; question: LograQuestion; answer: Record<string, unknown> }> = [];
  ONG_QUESTIONNAIRES.forEach((form) => {
    (["critical_questions", "detailed_questions"] as Array<"critical_questions" | "detailed_questions">).forEach((section) => {
      const questions = Array.isArray(form[section]) ? form[section] as LograQuestion[] : [];
      questions.forEach((question) => {
        const itemKey = formatValue(question.id || question.number);
        const answer = answers.get(`${form.slug}|${section}|${itemKey}`);
        if (answer) ordered.push({ form, section, question, answer });
      });
    });
  });
  return ordered;
}

function buildLograReportHtml(payload: Record<string, unknown>) {
  const report = asRecord(payload.report) || {};
  const rawAttachments = Array.isArray(payload.attachments) ? payload.attachments : [];
  const attachments = new Map<string, string[]>();
  rawAttachments.forEach((item) => {
    const record = asRecord(item);
    if (!record) return;
    const key = `${formatValue(record.form_slug)}|${formatValue(record.section)}|${formatValue(record.item_key)}`;
    const filename = formatValue(record.original_filename || record.id);
    attachments.set(key, [...(attachments.get(key) || []), filename]);
  });
  const agenda = Array.isArray(report.agenda_items) ? report.agenda_items.map((item) => asRecord(item)).filter(Boolean) as Record<string, unknown>[] : [];
  const rows = orderedLograAnswers(payload);
  let currentForm = "";
  let currentSection = "";
  const body: string[] = [];
  rows.forEach(({ form, section, question, answer }) => {
    if (currentForm !== form.slug) {
      body.push(`<h2>${escapeHtml(form.title)}</h2>`);
      currentForm = form.slug;
      currentSection = "";
    }
    if (currentSection !== section) {
      body.push(`<h3>${escapeHtml(lograSectionLabel(section))}</h3>`);
      currentSection = section;
    }
    const itemKey = formatValue(question.id || question.number || answer.item_key);
    const questionText = formatValue(answer.question_text || question.question);
    const bullets = Array.isArray(answer.bullets) ? answer.bullets : [];
    const attachmentNames = attachments.get(`${form.slug}|${section}|${itemKey}`) || [];
    body.push(`<section class="question"><p class="question-title">${escapeHtml(itemKey)}. ${escapeHtml(questionText)}</p>`);
    if (bullets.length) {
      body.push("<ul>");
      bullets.forEach((bullet) => body.push(`<li>${escapeHtml(bullet)}</li>`));
      body.push("</ul>");
    } else {
      body.push('<p class="empty">Sin respuesta registrada.</p>');
    }
    if (attachmentNames.length) {
      body.push(`<p class="attachments"><strong>Adjuntos:</strong> ${attachmentNames.map(escapeHtml).join(", ")}</p>`);
    }
    body.push("</section>");
  });
  const agendaRows = agenda.map((item) => `
    <tr>
      <td>${escapeHtml(item.date || item.date_long || item.date_iso)}</td>
      <td>${escapeHtml(item.start_time)}</td>
      <td>${escapeHtml(item.end_time)}</td>
      <td>${escapeHtml(item.place)}</td>
      <td>${escapeHtml(item.person)}</td>
      <td>${escapeHtml(item.company_role || item.company)}</td>
      <td>${escapeHtml(item.topic)}</td>
    </tr>
  `).join("");
  return `<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<title>${escapeHtml(report.title || "ONG Report")}</title>
<style>
  body { font-family: Arial, sans-serif; color: #172033; margin: 28px; }
  h1 { color: #003A75; text-align: center; margin-bottom: 4px; }
  h2 { color: #003A75; border-bottom: 2px solid #003A75; padding-bottom: 4px; margin-top: 26px; }
  h3 { color: #4B6478; margin-top: 18px; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  td, th { border: 1px solid #B8C1CA; padding: 6px; font-size: 11px; vertical-align: top; }
  th, .meta-label { background: #E9EEF3; font-weight: bold; }
  .subtitle { text-align: center; color: #667085; margin-bottom: 18px; }
  .question { break-inside: avoid; margin-bottom: 10px; }
  .question-title { font-weight: bold; margin-bottom: 4px; }
  li { margin-bottom: 3px; }
  .attachments, .empty { color: #667085; font-size: 11px; }
</style>
</head>
<body>
<h1>${escapeHtml(report.title || "ONG Report")}</h1>
<p class="subtitle">Professional ONG Questionnaire Report</p>
<table>
  <tr><td class="meta-label">ID</td><td>${escapeHtml(report.id)}</td></tr>
  <tr><td class="meta-label">Categoria</td><td>${escapeHtml(report.category || "ONG")}</td></tr>
  <tr><td class="meta-label">Status</td><td>${escapeHtml(report.status)}</td></tr>
  <tr><td class="meta-label">Agenda</td><td>${agenda.length} reuniones</td></tr>
  <tr><td class="meta-label">Actualizado</td><td>${escapeHtml(report.updated_at)}</td></tr>
</table>
${agendaRows ? `<h2>Meeting Agenda</h2><table><tr><th>Date</th><th>Start</th><th>End</th><th>Place</th><th>Person</th><th>Company/Role</th><th>Topic</th></tr>${agendaRows}</table>` : ""}
${body.join("\n")}
</body>
</html>`;
}

async function openDownloadedFile(uri: string, filename: string, mimeType?: string | null) {
  const type = mimeType || mimeFromFilename(filename);
  if (Platform.OS === "android") {
    try {
      const contentUri = await FileSystem.getContentUriAsync(uri);
      await IntentLauncher.startActivityAsync("android.intent.action.VIEW", {
        data: contentUri,
        type,
        flags: 1
      });
      return;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err || "");
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(uri, { dialogTitle: filename, mimeType: type });
        return;
      }
      throw new Error(message.includes("No Activity found") ? `No hay una aplicacion instalada para abrir ${filename}.` : `No se pudo abrir ${filename}: ${message}`);
    }
  }
  if (await Sharing.isAvailableAsync()) {
    await Sharing.shareAsync(uri, { dialogTitle: filename, mimeType: type, UTI: type });
    return;
  }
  await Linking.openURL(uri);
}

async function downloadSessionFile(
  endpoint: string,
  session: LoginResponse | null | { usuario: string; rol: string },
  filename: string,
  method: "GET" | "POST" | "PUT" = "GET",
  body?: Record<string, unknown>
) {
  const fileUri = `${FileSystem.cacheDirectory || ""}${cleanFilePart(filename)}`;
  const companySession = session as (Session | null);
  const headers: Record<string, string> = session
    ? {
        Accept: "application/octet-stream, application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*",
        "X-User": session.usuario,
        "X-Role": session.rol,
        "X-User-Role": session.rol,
        "X-Company-Code": companySession?.company_code || DEFAULT_COMPANY.code,
        "X-Company-Name": companySession?.company_name || DEFAULT_COMPANY.name
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

  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }
  await FileSystem.writeAsStringAsync(fileUri, btoa(binary), {
    encoding: FileSystem.EncodingType.Base64
  });

  await openDownloadedFile(fileUri, filename);
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
  { key: "lashing-certificate", label: "Informe Lashing Certificate" },
  { key: "logra", label: "Informe ONG" }
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

const ONG_FIELDS: InformeCreateField[] = [
  { key: "section_header", label: "ONG", type: "section" },
  { key: "title", label: "Titulo" },
  { key: "category", label: "Categoria" },
  { key: "status", label: "Status" },
  { key: "section_agenda", label: "Agenda", type: "section" },
  { key: "meeting_date", label: "Fecha", type: "date" },
  { key: "meeting_start_time", label: "Inicio HH:MM" },
  { key: "meeting_end_time", label: "Fin HH:MM" },
  { key: "meeting_location", label: "Lugar" },
  { key: "meeting_person", label: "Persona" },
  { key: "meeting_phone", label: "Telefono" },
  { key: "company_role", label: "Empresa/Rol" },
  { key: "topic", label: "Tema" },
  { key: "priority", label: "Prioridad" },
  { key: "reminder_minutes", label: "Recordar min" },
  { key: "agenda_notes", label: "Anotaciones generales", type: "multiline" },
  { key: "section_questionnaire", label: "Cuestionario", type: "section" },
  { key: "form_title", label: "Formulario" },
  { key: "question_text", label: "Pregunta" },
  { key: "bullet_1", label: "Bullet 1", type: "multiline" },
  { key: "bullet_2", label: "Bullet 2", type: "multiline" },
  { key: "bullet_3", label: "Bullet 3", type: "multiline" }
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
  { key: "lashing-certificate", group: "Certificados", title: "Lashing Certificate", endpoint: "/lashing-certificates", fields: COMMON_REPORT_FIELDS },
  { key: "logra", group: "ONG", title: "ONG", endpoint: "/logra-reports", fields: ONG_FIELDS }
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
  const [draftSurveyOpen, setDraftSurveyOpen] = useState(false);
  const [bunkerOpen, setBunkerOpen] = useState(false);
  const [bunkerReviewId, setBunkerReviewId] = useState<string | null>(null);
  const [cargoConditionOpen, setCargoConditionOpen] = useState(false);
  const [cargoConditionReviewId, setCargoConditionReviewId] = useState<string | null>(null);
  const [vesselConditionOpen, setVesselConditionOpen] = useState(false);
  const [vesselConditionReviewId, setVesselConditionReviewId] = useState<string | null>(null);
  const [portCaptancyOpen, setPortCaptancyOpen] = useState(false);
  const [portCaptancyReviewId, setPortCaptancyReviewId] = useState<string | null>(null);
  const [craneInspectionOpen, setCraneInspectionOpen] = useState(false);
  const [craneInspectionReviewId, setCraneInspectionReviewId] = useState<string | null>(null);
  const [weightCertificateOpen, setWeightCertificateOpen] = useState(false);
  const [weightCertificateReviewId, setWeightCertificateReviewId] = useState<string | null>(null);
  const [holdsCertificateOpen, setHoldsCertificateOpen] = useState(false);
  const [holdsCertificateReviewId, setHoldsCertificateReviewId] = useState<string | null>(null);
  const [samplingCertificateOpen, setSamplingCertificateOpen] = useState(false);
  const [samplingCertificateReviewId, setSamplingCertificateReviewId] = useState<string | null>(null);
  const [sealingCertificateOpen, setSealingCertificateOpen] = useState(false);
  const [sealingCertificateReviewId, setSealingCertificateReviewId] = useState<string | null>(null);
  const [lashingCertificateOpen, setLashingCertificateOpen] = useState(false);
  const [lashingCertificateReviewId, setLashingCertificateReviewId] = useState<string | null>(null);
  const [lograOpen, setLograOpen] = useState(false);
  const [lograReviewId, setLograReviewId] = useState<string | null>(null);
  const [reviewActionKey, setReviewActionKey] = useState("Review");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const statusOptions = ["", "Draft", "Pendiente", "En curso", "Completado", "Pending", "Pending for review", "Approved", "Rejected", "Approve", "Reject"];

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
  const reviewActionOptions = ["Review", ...config.actions.map((action) => action.label)];

  useEffect(() => {
    setReviewActionKey("Review");
  }, [activeKey]);

  function selectedReviewAction() {
    if (reviewActionKey === "Review") return null;
    return config.actions.find((action) => action.key === reviewActionKey || action.label === reviewActionKey) || null;
  }

  async function runSelectedReviewAction() {
    const action = selectedReviewAction();
    if (action) await runInformeAction(action);
    else await openDetail();
  }

  async function load() {
    const endpoint = activeKey === "logra" ? "/logra-reports" : getInformeEndpoint(activeKey, section, activeSection);
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
      const nextRows = activeKey === "logra" ? normalizeOngReviewRows(payload) : rowsFromAny(payload);
      setRows(nextRows);
      if (activeKey === "logra" && !nextRows.length) {
        setMessage("No hay cuestionarios ONG cargados para revisar.");
      }
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

  useEffect(() => {
    if (reviewOpen && activeKey === "logra") {
      load();
    }
  }, [reviewOpen, activeKey]);

  async function openDetail() {
    if (!selectedRow) {
      setMessage("Seleccione una fila.");
      return;
    }
    if (activeKey === "bunker") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Vessel Bunker valido.");
        return;
      }
      setBunkerReviewId(id);
      setBunkerOpen(true);
      return;
    }
    if (activeKey === "cargo-condition") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Cargo Condition valido.");
        return;
      }
      setCargoConditionReviewId(id);
      setCargoConditionOpen(true);
      return;
    }
    if (activeKey === "vessel-condition") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Vessel Condition valido.");
        return;
      }
      setVesselConditionReviewId(id);
      setVesselConditionOpen(true);
      return;
    }
    if (activeKey === "port-captancy") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Port Captancy valido.");
        return;
      }
      setPortCaptancyReviewId(id);
      setPortCaptancyOpen(true);
      return;
    }
    if (activeKey === "crane-inspection") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Crane Inspection valido.");
        return;
      }
      setCraneInspectionReviewId(id);
      setCraneInspectionOpen(true);
      return;
    }
    if (activeKey === "weight-certificate") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Weight Certificate valido.");
        return;
      }
      setWeightCertificateReviewId(id);
      setWeightCertificateOpen(true);
      return;
    }
    if (activeKey === "holds-certificate") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Holds Inspection Certificate valido.");
        return;
      }
      setHoldsCertificateReviewId(id);
      setHoldsCertificateOpen(true);
      return;
    }
    if (activeKey === "sampling-certificate") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Sampling Certificate valido.");
        return;
      }
      setSamplingCertificateReviewId(id);
      setSamplingCertificateOpen(true);
      return;
    }
    if (activeKey === "sealing-certificate") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Sealing Certificate valido.");
        return;
      }
      setSealingCertificateReviewId(id);
      setSealingCertificateOpen(true);
      return;
    }
    if (activeKey === "lashing-certificate") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un Lashing Certificate valido.");
        return;
      }
      setLashingCertificateReviewId(id);
      setLashingCertificateOpen(true);
      return;
    }
    if (activeKey === "logra") {
      const id = formatValue(selectedRow.id);
      if (id === "-") {
        setMessage("Seleccione un ONG valido.");
        return;
      }
      setLograReviewId(id);
      setLograOpen(true);
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
    if (activeKey === "logra") {
      setMessage("ONG se puede revisar desde mobile. Para editar cuestionario, agenda y adjuntos use la pantalla ONG completa del ERP.");
      return;
    }
    const updateEndpoint = config.updateEndpoint || config.detailEndpoint;
    if (!updateEndpoint) {
      setMessage("Este informe no tiene endpoint de actualizacion.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const row = { ...detail, ...detailForm };
      const result = await offlineApiRequest(endpointForRow(updateEndpoint, row, config.idField), {
        method: "PUT",
        body: detailForm,
        session,
        offlineLabel: `Actualizar ${config.title}`
      });
      setMessage(isQueuedOffline(result) ? "Sin internet: cambios guardados en cache local para sincronizar." : "Informe actualizado correctamente.");
      setDetail(null);
      setDetailForm({});
      if (!isQueuedOffline(result)) await load();
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
    if (activeKey === "logra" && (action.key === "logra-word" || action.key === "logra-pdf")) {
      await exportLograMobile(action.key === "logra-word" ? "word" : "pdf");
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
        const result = await offlineApiRequest(endpoint, {
          method: action.method,
          body: action.body,
          session,
          offlineLabel: `${action.label} ${config.title}`
        });
        setMessage(isQueuedOffline(result) ? "Sin internet: accion guardada en cache local para sincronizar." : "Accion ejecutada correctamente.");
        if (!isQueuedOffline(result)) await load();
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `No se pudo ejecutar ${action.label}.`);
    } finally {
      setBusy(false);
    }
  }

  async function exportLograMobile(kind: "word" | "pdf") {
    if (!selectedRow) {
      setMessage("Seleccione un ONG.");
      return;
    }
    const id = formatValue(selectedRow.id);
    if (id === "-") {
      setMessage("Seleccione un ONG valido.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/logra-reports/${encodeURIComponent(id)}`, { session });
      const html = buildLograReportHtml(payload);
      const report = asRecord(payload.report) || selectedRow;
      const title = cleanFilePart(formatValue(report.title || `ONG_${id}`));
      const extension = kind === "word" ? "doc" : "html";
      const filename = `${title}_${kind === "word" ? "WORD" : "PDF"}.${extension}`;
      const uri = `${FileSystem.cacheDirectory || ""}${filename}`;
      await FileSystem.writeAsStringAsync(uri, html);
      await openDownloadedFile(uri, filename, kind === "word" ? "application/msword" : "text/html");
      setMessage(kind === "word" ? "Word ONG generado correctamente." : "Reporte ONG abierto. Use imprimir/guardar como PDF desde el telefono.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo exportar ONG.");
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
    if (configToCreate.key === "logra") {
      initial.title = "ONG";
      initial.category = "ONG";
      initial.status = "Pendiente";
      initial.meeting_date = formatYmd(new Date());
      initial.meeting_start_time = "09:00";
      initial.meeting_end_time = "10:00";
      initial.priority = "Media";
      initial.reminder_minutes = "30";
      initial.form_title = "ONG Mobile";
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
      if (createConfig.key === "logra") {
        const bullets = [createForm.bullet_1, createForm.bullet_2, createForm.bullet_3].map((value) => (value || "").trim()).filter(Boolean);
        const lograPayload = {
          title: createForm.title || "ONG",
          category: createForm.category || "ONG",
          status: createForm.status || "Pendiente",
          created_by: session.usuario,
          agenda_notes: createForm.agenda_notes || "",
          agenda_items: [
            {
              date_iso: createForm.meeting_date || formatYmd(new Date()),
              start_time: createForm.meeting_start_time || "09:00",
              end_time: createForm.meeting_end_time || "10:00",
              place: createForm.meeting_location || "",
              person: createForm.meeting_person || "",
              phone: createForm.meeting_phone || "",
              company_role: createForm.company_role || "",
              topic: createForm.topic || "",
              priority: createForm.priority || "Media",
              status: createForm.status || "Pendiente",
              reminder_minutes: Number(createForm.reminder_minutes || 30)
            }
          ],
          answers: createForm.question_text
            ? [
                {
                  form_slug: "mobile-logra",
                  form_title: createForm.form_title || "ONG Mobile",
                  section: "Mobile",
                  item_key: "mobile-1",
                  question_text: createForm.question_text,
                  bullets
                }
              ]
            : []
        };
        const result = await offlineApiRequest(createConfig.endpoint, {
          method: "POST",
          body: lograPayload,
          session,
          offlineLabel: "Crear ONG"
        });
        setCreateConfig(null);
        setCreateForm({});
        setMessage(isQueuedOffline(result) ? "Sin internet: ONG guardado en cache local para sincronizar." : "ONG creado correctamente.");
        if (activeKey === "logra" && !isQueuedOffline(result)) await load();
        return;
      }
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
      const result = await offlineApiRequest(createConfig.endpoint, {
        method: "POST",
        body: payload,
        session,
        offlineLabel: `Crear ${createConfig.title}`
      });
      setCreateConfig(null);
      setCreateForm({});
      setMessage(isQueuedOffline(result) ? "Sin internet: informe guardado en cache local para sincronizar." : "Informe creado y enviado a revision.");
      if (activeKey === createConfig.key && !isQueuedOffline(result)) await load();
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
      <View style={styles.financeFilterBox}>
        <SelectField label="Acciones" value={reviewActionKey} options={reviewActionOptions} onChange={setReviewActionKey} />
        <View style={styles.financeFilterActions}>
          <Pressable style={selectedReviewAction()?.key === "reject" ? styles.modalClose : styles.actionButton} onPress={runSelectedReviewAction}>
            <Text style={selectedReviewAction()?.key === "reject" ? styles.modalCloseText : styles.actionButtonText}>Ejecutar</Text>
          </Pressable>
        </View>
      </View>
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
                <Pressable
                  style={styles.secondaryButton}
                  onPress={() => {
                    setGenerateOpen(false);
                    setGenerateGroup(null);
                    setLograReviewId(null);
                    setLograOpen(true);
                  }}
                >
                  <Text style={styles.secondaryButtonText}>ONG</Text>
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
                    <Pressable
                      key={item.key}
                      style={styles.secondaryButton}
                      onPress={() => {
                        if (item.key === "draft-survey") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setDraftSurveyOpen(true);
                        } else if (item.key === "bunker") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setBunkerReviewId(null);
                          setBunkerOpen(true);
                        } else if (item.key === "cargo-condition") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setCargoConditionReviewId(null);
                          setCargoConditionOpen(true);
                        } else if (item.key === "vessel-condition") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setVesselConditionReviewId(null);
                          setVesselConditionOpen(true);
                        } else if (item.key === "port-captancy") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setPortCaptancyReviewId(null);
                          setPortCaptancyOpen(true);
                        } else if (item.key === "crane-inspection") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setCraneInspectionReviewId(null);
                          setCraneInspectionOpen(true);
                        } else if (item.key === "weight-certificate") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setWeightCertificateReviewId(null);
                          setWeightCertificateOpen(true);
                        } else if (item.key === "holds-certificate") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setHoldsCertificateReviewId(null);
                          setHoldsCertificateOpen(true);
                        } else if (item.key === "sampling-certificate") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setSamplingCertificateReviewId(null);
                          setSamplingCertificateOpen(true);
                        } else if (item.key === "sealing-certificate") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setSealingCertificateReviewId(null);
                          setSealingCertificateOpen(true);
                        } else if (item.key === "lashing-certificate") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setLashingCertificateReviewId(null);
                          setLashingCertificateOpen(true);
                        } else if (item.key === "logra") {
                          setGenerateOpen(false);
                          setGenerateGroup(null);
                          setLograReviewId(null);
                          setLograOpen(true);
                        } else {
                          openCreate(item);
                        }
                      }}
                    >
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
      <DraftSurveyMobileModal
        visible={draftSurveyOpen}
        session={session}
        onClose={() => setDraftSurveyOpen(false)}
        onSaved={async () => {
          setDraftSurveyOpen(false);
          if (activeKey === "draft-survey") await load();
        }}
      />
      <VesselBunkerMobileModal
        visible={bunkerOpen}
        session={session}
        initialReportId={bunkerReviewId}
        onClose={() => {
          setBunkerOpen(false);
          setBunkerReviewId(null);
        }}
        onSaved={async () => {
          setBunkerOpen(false);
          setBunkerReviewId(null);
          if (activeKey === "bunker") await load();
        }}
      />
      <CargoConditionMobileModal
        visible={cargoConditionOpen}
        session={session}
        initialReportId={cargoConditionReviewId}
        onClose={() => {
          setCargoConditionOpen(false);
          setCargoConditionReviewId(null);
        }}
        onSaved={async () => {
          setCargoConditionOpen(false);
          setCargoConditionReviewId(null);
          if (activeKey === "cargo-condition") await load();
        }}
      />
      <CraneInspectionMobileModal
        visible={craneInspectionOpen}
        session={session}
        initialReportId={craneInspectionReviewId}
        onClose={() => {
          setCraneInspectionOpen(false);
          setCraneInspectionReviewId(null);
        }}
        onSaved={async () => {
          setCraneInspectionOpen(false);
          setCraneInspectionReviewId(null);
          if (activeKey === "crane-inspection") await load();
        }}
      />
      <WeightCertificateMobileModal
        visible={weightCertificateOpen}
        session={session}
        initialReportId={weightCertificateReviewId}
        onClose={() => {
          setWeightCertificateOpen(false);
          setWeightCertificateReviewId(null);
        }}
        onSaved={async () => {
          setWeightCertificateOpen(false);
          setWeightCertificateReviewId(null);
          if (activeKey === "weight-certificate") await load();
        }}
      />
      <HoldsInspectionCertificateMobileModal
        visible={holdsCertificateOpen}
        session={session}
        initialReportId={holdsCertificateReviewId}
        onClose={() => {
          setHoldsCertificateOpen(false);
          setHoldsCertificateReviewId(null);
        }}
        onSaved={async () => {
          setHoldsCertificateOpen(false);
          setHoldsCertificateReviewId(null);
          if (activeKey === "holds-certificate") await load();
        }}
      />
      <SamplingCertificateMobileModal
        visible={samplingCertificateOpen}
        session={session}
        initialReportId={samplingCertificateReviewId}
        onClose={() => {
          setSamplingCertificateOpen(false);
          setSamplingCertificateReviewId(null);
        }}
        onSaved={async () => {
          setSamplingCertificateOpen(false);
          setSamplingCertificateReviewId(null);
          if (activeKey === "sampling-certificate") await load();
        }}
      />
      <SealingCertificateMobileModal
        visible={sealingCertificateOpen}
        session={session}
        initialReportId={sealingCertificateReviewId}
        onClose={() => {
          setSealingCertificateOpen(false);
          setSealingCertificateReviewId(null);
        }}
        onSaved={async () => {
          setSealingCertificateOpen(false);
          setSealingCertificateReviewId(null);
          if (activeKey === "sealing-certificate") await load();
        }}
      />
      <LashingCertificateMobileModal
        visible={lashingCertificateOpen}
        session={session}
        initialReportId={lashingCertificateReviewId}
        onClose={() => {
          setLashingCertificateOpen(false);
          setLashingCertificateReviewId(null);
        }}
        onSaved={async () => {
          setLashingCertificateOpen(false);
          setLashingCertificateReviewId(null);
          if (activeKey === "lashing-certificate") await load();
        }}
      />
      <VesselConditionMobileModal
        visible={vesselConditionOpen}
        session={session}
        initialReportId={vesselConditionReviewId}
        onClose={() => {
          setVesselConditionOpen(false);
          setVesselConditionReviewId(null);
        }}
        onSaved={async () => {
          setVesselConditionOpen(false);
          setVesselConditionReviewId(null);
          if (activeKey === "vessel-condition") await load();
        }}
      />
      <PortCaptancyMobileModal
        visible={portCaptancyOpen}
        session={session}
        initialReportId={portCaptancyReviewId}
        onClose={() => {
          setPortCaptancyOpen(false);
          setPortCaptancyReviewId(null);
        }}
        onSaved={async () => {
          setPortCaptancyOpen(false);
          setPortCaptancyReviewId(null);
          if (activeKey === "port-captancy") await load();
        }}
      />
      <LograMobileModal
        visible={lograOpen}
        session={session}
        initialReportId={lograReviewId}
        onClose={() => {
          setLograOpen(false);
          setLograReviewId(null);
        }}
        onSaved={async () => {
          setLograOpen(false);
          setLograReviewId(null);
          if (activeKey === "logra") await load();
        }}
      />
    </View>
  );
}

type LograAgendaItem = {
  report_id?: number | string;
  agenda_index?: number | string;
  report_title?: string;
  date?: string;
  date_iso?: string;
  start_time?: string;
  end_time?: string;
  place?: string;
  person?: string;
  phone?: string;
  telefono?: string;
  company?: string;
  company_role?: string;
  topic?: string;
  priority?: string;
  status?: string;
  notes?: string;
  reminder_minutes?: number | string;
};

type LograAttachment = {
  id: number;
  form_slug: string;
  section: string;
  item_key: string;
  bullet_index?: number | null;
  original_filename: string;
  content_type?: string | null;
  created_at?: string;
};

const ONG_SECTION_LABELS: Record<"critical_questions" | "detailed_questions", string> = {
  critical_questions: "Preguntas de apertura",
  detailed_questions: "Preguntas por tema"
};

const ONG_ITEMS_PER_PAGE = 5;
const ONG_MAX_BULLETS = 20;

function lograQuestionKey(form: LograQuestionnaire, section: keyof typeof ONG_SECTION_LABELS, item: LograQuestion) {
  return `${form.slug}|${section}|${String(item.id || item.number || "").trim()}`;
}

function lograItemKey(item: LograQuestion) {
  return String(item.id || item.number || "").trim();
}

function lograTint(value?: string) {
  const normalized = (value || "").toLowerCase();
  if (normalized.includes("alta") || normalized.includes("pendiente") || normalized.includes("late")) return "#F8D7DA";
  if (normalized.includes("media") || normalized.includes("proceso") || normalized.includes("curso")) return "#FFF3CD";
  if (normalized.includes("baja") || normalized.includes("complet")) return "#D1E7DD";
  return "#FFFFFF";
}

function blankAgendaItem(): LograAgendaItem {
  return {
    date_iso: formatYmd(new Date()),
    start_time: "09:00",
    end_time: "10:00",
    place: "",
    person: "",
    phone: "",
    company: "",
    topic: "",
    priority: "Media",
    status: "Pendiente",
    reminder_minutes: 30
  };
}

function lograAgendaKey(item: LograAgendaItem, reportTitle = "") {
  return [
    reportTitle,
    item.date_iso || item.date || "",
    item.start_time || "",
    item.end_time || "",
    item.place || "",
    item.person || "",
    item.phone || item.telefono || "",
    item.company || item.company_role || "",
    item.topic || ""
  ].map((value) => String(value || "").trim().toLowerCase()).join("|");
}

function lograAgendaStartDate(item: LograAgendaItem) {
  const date = String(item.date_iso || item.date || "").slice(0, 10);
  const time = String(item.start_time || "00:00").slice(0, 5);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(time)) return null;
  const parsed = new Date(`${date}T${time}:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function lograAgendaEndDate(item: LograAgendaItem) {
  const date = String(item.date_iso || item.date || "").slice(0, 10);
  const time = String(item.end_time || "").slice(0, 5);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(time)) return null;
  const parsed = new Date(`${date}T${time}:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function lograAgendaTint(item: LograAgendaItem) {
  const status = String(item.status || "").toLowerCase();
  if (status.includes("complet")) return "#D1E7DD";
  const now = Date.now();
  const start = lograAgendaStartDate(item);
  const end = lograAgendaEndDate(item);
  if (end && end.getTime() < now) return "#F4B8B8";
  if (start && start.getTime() <= now && (!end || end.getTime() >= now)) return "#FFF3CD";
  return lograTint(item.status || item.priority);
}

function monthName(date: Date) {
  return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

function calendarDaysForMonth(monthDate: Date) {
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();
  const first = new Date(year, month, 1);
  const start = new Date(year, month, 1 - first.getDay());
  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    return date;
  });
}

async function syncLograAgendaNotifications(items: LograAgendaItem[]) {
  try {
    const previous = await AsyncStorage.getItem(ONG_NOTIFICATION_IDS_KEY);
    const previousIds = previous ? JSON.parse(previous) as string[] : [];
    await Promise.all(previousIds.map((id) => Notifications.cancelScheduledNotificationAsync(id).catch(() => undefined)));

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("logra-agenda", {
        name: "ONG Agenda",
        importance: Notifications.AndroidImportance.HIGH,
        sound: "default",
        vibrationPattern: [0, 500, 250, 500]
      });
    }

    const permission = await Notifications.requestPermissionsAsync();
    if (!permission.granted) {
      await AsyncStorage.setItem(ONG_NOTIFICATION_IDS_KEY, JSON.stringify([]));
      return;
    }

    const now = Date.now();
    const nextIds: string[] = [];
    for (const item of items.slice(0, 150)) {
      if (String(item.status || "").toLowerCase().includes("complet")) continue;
      const start = lograAgendaStartDate(item);
      if (!start) continue;
      const reminderMinutes = Math.max(0, Number(item.reminder_minutes || 0) || 0);
      const title = item.topic || item.person || "Reunion ONG";
      const detail = [item.person, item.phone || item.telefono, item.place].filter(Boolean).join(" | ");
      const reminderAt = new Date(start.getTime() - reminderMinutes * 60 * 1000);
      const triggers = [
        reminderMinutes > 0 ? { date: reminderAt, body: `Inicia en ${reminderMinutes} min. ${detail}` } : null,
        { date: start, body: `La reunion esta en curso. ${detail}` }
      ].filter(Boolean) as Array<{ date: Date; body: string }>;
      for (const trigger of triggers) {
        if (trigger.date.getTime() <= now) continue;
        const id = await Notifications.scheduleNotificationAsync({
          content: {
            title: `Agenda ONG: ${title}`,
            body: trigger.body,
            sound: "default",
            data: { type: "logra-agenda" }
          },
          trigger: { type: "date", date: trigger.date, channelId: "logra-agenda" } as Notifications.NotificationTriggerInput
        });
        nextIds.push(id);
      }
    }
    await AsyncStorage.setItem(ONG_NOTIFICATION_IDS_KEY, JSON.stringify(nextIds));
  } catch {
    // Notifications should never block saving or loading the agenda.
  }
}

function parseDateValue(value: unknown) {
  const text = String(value ?? "").trim();
  if (!text) return null;
  const normalized = /^\d{4}-\d{2}-\d{2}/.test(text) ? text.slice(0, 10) : text;
  const parsed = new Date(`${normalized}T09:00:00`);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function nextBirthdayDate(value: unknown) {
  const birth = parseDateValue(value);
  if (!birth) return null;
  const today = new Date();
  const next = new Date(today.getFullYear(), birth.getMonth(), birth.getDate(), 9, 0, 0);
  const todayDateOnly = new Date(today.getFullYear(), today.getMonth(), today.getDate()).getTime();
  const nextDateOnly = new Date(next.getFullYear(), next.getMonth(), next.getDate()).getTime();
  if (nextDateOnly < todayDateOnly) next.setFullYear(today.getFullYear() + 1);
  return next;
}

function calendarDaysBetween(from: Date, to: Date) {
  const start = new Date(from.getFullYear(), from.getMonth(), from.getDate()).getTime();
  const end = new Date(to.getFullYear(), to.getMonth(), to.getDate()).getTime();
  return Math.round((end - start) / (24 * 60 * 60 * 1000));
}

async function syncBusinessNotifications(session: Session) {
  try {
    const previous = await AsyncStorage.getItem(ERP_NOTIFICATION_IDS_KEY);
    const previousIds = previous ? JSON.parse(previous) as string[] : [];
    await Promise.all(previousIds.map((id) => Notifications.cancelScheduledNotificationAsync(id).catch(() => undefined)));

    if (Platform.OS === "android") {
      await Notifications.setNotificationChannelAsync("erp-alerts", {
        name: "ERP SOM Alertas",
        importance: Notifications.AndroidImportance.HIGH,
        sound: "default",
        vibrationPattern: [0, 500, 250, 500]
      });
    }

    const permission = await Notifications.requestPermissionsAsync();
    if (!permission.granted) {
      await AsyncStorage.setItem(ERP_NOTIFICATION_IDS_KEY, JSON.stringify([]));
      return;
    }

    const now = new Date();
    const period = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    const ids: string[] = [];

    const tax = await apiRequest<Record<string, unknown>>(`/accounting/tax/obligations?year=${now.getFullYear()}&period=${period}&pending_only=true`, { session }).catch(() => null);
    for (const item of (Array.isArray(tax?.data) ? tax?.data : []).slice(0, 10) as Record<string, unknown>[]) {
      const calendar = Array.isArray(item.calendar) ? item.calendar as Record<string, unknown>[] : [];
      for (const due of calendar.slice(0, 3)) {
        const dueDate = parseDateValue(due.estimated_due_date);
        const status = String(due.alert_status || "").toUpperCase();
        const name = String(item.name || item.tax_code || "Declaracion pendiente");
        const dueText = String(due.estimated_due_date || "sin fecha");
        const alertDate = dueDate ? new Date(dueDate.getTime() - 24 * 60 * 60 * 1000) : null;
        const triggerDate = status === "DUE_TODAY" || status === "DUE_TOMORROW"
          ? new Date(Date.now() + 3000)
          : alertDate && alertDate.getTime() > Date.now()
            ? alertDate
            : null;
        if (!triggerDate) continue;
        const id = await Notifications.scheduleNotificationAsync({
          content: {
            title: "Declaracion pendiente",
            body: `${name} vence ${dueText}.`,
            sound: "default",
            data: { type: "tax-obligation" }
          },
          trigger: { type: "date", date: triggerDate, channelId: "erp-alerts" } as Notifications.NotificationTriggerInput
        });
        ids.push(id);
      }
    }

    const role = String(session.rol || "").trim().toLowerCase();
    if (role === "master" || role === "admin") {
      const employees = await apiRequest<Record<string, unknown>>("/hr/employees?page=1&page_size=500&estado=ACTIVO", { session }).catch(() => null);
      for (const emp of (Array.isArray(employees?.data) ? employees?.data : []) as Record<string, unknown>[]) {
        const date = nextBirthdayDate(emp.fecha_nacimiento);
        if (!date) continue;
        const days = calendarDaysBetween(new Date(), date);
        if (days !== 0 && days !== 3) continue;
        const name = String(emp.nombre_completo || emp.nombre || emp.usuario || "Empleado");
        const id = await Notifications.scheduleNotificationAsync({
          content: {
            title: "Cumpleanos de empleado",
            body: days === 0 ? `${name} cumple anos hoy.` : `${name} cumple anos en 3 dias.`,
            sound: "default",
            data: { type: "employee-birthday" }
          },
          trigger: { type: "date", date: days === 0 ? new Date(Date.now() + 5000) : date, channelId: "erp-alerts" } as Notifications.NotificationTriggerInput
        });
        ids.push(id);
      }
    }

    const statusReports = await apiRequest<Record<string, unknown>>("/status-informes?status=Pending", { session }).catch(() => null);
    const regularPending = Number(statusReports?.count || (Array.isArray(statusReports?.data) ? statusReports?.data.length : 0)) || 0;
    const ongReports = await apiRequest<Record<string, unknown>>("/logra-reports", { session }).catch(() => null);
    const ongPending = (Array.isArray(ongReports?.data) ? ongReports?.data : []).filter((row) => String((row as Record<string, unknown>).status || "").toLowerCase() === "pending").length;
    const pendingTotal = regularPending + ongPending;
    if (pendingTotal > 0) {
      const immediateId = await Notifications.scheduleNotificationAsync({
        content: {
          title: "Informes pendientes",
          body: `Hay ${pendingTotal} informe(s) Pending. Deben marcarse Approved o Rejected.`,
          sound: "default",
          data: { type: "pending-reports" }
        },
        trigger: { type: "date", date: new Date(Date.now() + 5000), channelId: "erp-alerts" } as Notifications.NotificationTriggerInput
      });
      ids.push(immediateId);
      const id = await Notifications.scheduleNotificationAsync({
        content: {
          title: "Informes pendientes",
          body: `Hay ${pendingTotal} informe(s) Pending. Se avisara cada 24 horas hasta aprobar o rechazar.`,
          sound: "default",
          data: { type: "pending-reports" }
        },
        trigger: { type: "timeInterval", seconds: 86400, repeats: true, channelId: "erp-alerts" } as Notifications.NotificationTriggerInput
      });
      ids.push(id);
    }

    await AsyncStorage.setItem(ERP_NOTIFICATION_IDS_KEY, JSON.stringify(ids));
  } catch {
    // Notifications are supportive; the ERP must continue even if permissions or fetches fail.
  }
}

function LograMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: Session;
  initialReportId: string | null;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const [reportId, setReportId] = useState<string | null>(initialReportId);
  const [reportIdsByForm, setReportIdsByForm] = useState<Record<string, string>>({});
  const [reportVersionsByForm, setReportVersionsByForm] = useState<Record<string, number>>({});
  const [formTitle, setFormTitle] = useState(ONG_QUESTIONNAIRES[0]?.title || "");
  const [section, setSection] = useState<keyof typeof ONG_SECTION_LABELS>("critical_questions");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string[]>>({});
  const [agendaItems, setAgendaItems] = useState<LograAgendaItem[]>([]);
  const [agendaDraft, setAgendaDraft] = useState<LograAgendaItem>(() => blankAgendaItem());
  const [agendaNotes, setAgendaNotes] = useState("");
  const [selectedAgenda, setSelectedAgenda] = useState<number | null>(null);
  const [attachments, setAttachments] = useState<LograAttachment[]>([]);
  const [agendaOpen, setAgendaOpen] = useState(false);
  const [agendaView, setAgendaView] = useState<"list" | "calendar">("list");
  const [calendarMonth, setCalendarMonth] = useState(() => new Date());
  const [agendaAction, setAgendaAction] = useState("Nueva");
  const [agendaStatusOpen, setAgendaStatusOpen] = useState(false);
  const [agendaStatusDraft, setAgendaStatusDraft] = useState("Pendiente");
  const [agendaNotesOpen, setAgendaNotesOpen] = useState(false);
  const [agendaLineNote, setAgendaLineNote] = useState("");
  const [portiaOpen, setPortiaOpen] = useState(false);
  const [portiaForm, setPortiaForm] = useState(ONG_QUESTIONNAIRES[0]?.title || "");
  const [portiaSection, setPortiaSection] = useState<keyof typeof ONG_SECTION_LABELS>("critical_questions");
  const [portiaQuestionKey, setPortiaQuestionKey] = useState("");
  const [portiaBullet, setPortiaBullet] = useState("0");
  const [portiaLanguage, setPortiaLanguage] = useState("ES");
  const [portiaResult, setPortiaResult] = useState<{ original: string; improved: string; answerKey: string; bulletIndex: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const realtimeDraftTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const selectedForm = ONG_QUESTIONNAIRES.find((item) => item.title === formTitle) || ONG_QUESTIONNAIRES[0];
  const allItems = selectedForm ? selectedForm[section] || [] : [];
  const filteredItems = allItems.filter((item) => {
    const needle = search.trim().toLowerCase();
    if (!needle) return true;
    return [item.id, item.number, item.block, item.question].map((value) => String(value || "").toLowerCase()).some((value) => value.includes(needle));
  });
  const totalPages = Math.max(1, Math.ceil(filteredItems.length / ONG_ITEMS_PER_PAGE));
  const pageItems = filteredItems.slice(page * ONG_ITEMS_PER_PAGE, page * ONG_ITEMS_PER_PAGE + ONG_ITEMS_PER_PAGE);
  const portiaSelectedForm = ONG_QUESTIONNAIRES.find((item) => item.title === portiaForm) || ONG_QUESTIONNAIRES[0];
  const portiaQuestions = portiaSelectedForm ? portiaSelectedForm[portiaSection] || [] : [];
  const portiaSelectedQuestion = portiaQuestions.find((item) => lograItemKey(item) === portiaQuestionKey) || portiaQuestions[0];
  const portiaAnswerKey = portiaSelectedForm && portiaSelectedQuestion ? lograQuestionKey(portiaSelectedForm, portiaSection, portiaSelectedQuestion) : "";
  const portiaBullets = answers[portiaAnswerKey] || [""];
  const calendarDays = calendarDaysForMonth(calendarMonth);
  const agendaByDate = agendaItems.reduce<Record<string, LograAgendaItem[]>>((acc, item) => {
    const key = String(item.date_iso || item.date || "").slice(0, 10);
    if (!key) return acc;
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  useEffect(() => {
    if (!visible) return;
    setReportId(initialReportId);
    setReportIdsByForm({});
    setReportVersionsByForm({});
    setFormTitle(ONG_QUESTIONNAIRES[0]?.title || "");
    setPortiaForm(ONG_QUESTIONNAIRES[0]?.title || "");
    setSection("critical_questions");
    setPortiaSection("critical_questions");
    setSearch("");
    setPage(0);
    setAnswers({});
    setAgendaItems([]);
    setAgendaDraft(blankAgendaItem());
    setAgendaNotes("");
    setAgendaView("list");
    setCalendarMonth(new Date());
    setAttachments([]);
    setMessage("");
    if (initialReportId) loadReport(initialReportId);
    else restoreLocalOngDraft();
  }, [visible, initialReportId]);

  useEffect(() => {
    setPage(0);
  }, [formTitle, section, search]);

  useEffect(() => {
    const first = portiaQuestions[0];
    setPortiaQuestionKey(first ? lograItemKey(first) : "");
    setPortiaBullet("0");
  }, [portiaForm, portiaSection]);

  useEffect(() => {
    if (!visible) return;
    const timer = setInterval(() => {
      autosaveLogra();
    }, 20000);
    return () => clearInterval(timer);
  }, [visible, reportId, formTitle, section, answers, agendaItems, agendaNotes]);

  useEffect(() => {
    if (!visible) return;
    if (realtimeDraftTimer.current) clearTimeout(realtimeDraftTimer.current);
    realtimeDraftTimer.current = setTimeout(() => {
      saveLocalOngDraft();
    }, 700);
    return () => {
      if (realtimeDraftTimer.current) clearTimeout(realtimeDraftTimer.current);
    };
  }, [visible, reportId, formTitle, section, answers, agendaItems, agendaNotes]);

  async function loadReport(id: string) {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/logra-reports/${encodeURIComponent(id)}`, { session });
      const report = asRecord(payload.report) || {};
      const nextAnswers: Record<string, string[]> = {};
      const rawAnswers = Array.isArray(payload.answers) ? payload.answers : [];
      rawAnswers.forEach((entry) => {
        const record = asRecord(entry);
        if (!record) return;
        const key = `${formatValue(record.form_slug)}|${formatValue(record.section)}|${formatValue(record.item_key)}`;
        const bullets = Array.isArray(record.bullets) ? record.bullets.map((value) => String(value || "")) : [""];
        nextAnswers[key] = bullets.length ? bullets : [""];
      });
      setReportId(id);
      setAnswers(nextAnswers);
      const loadedAgenda = Array.isArray(report.agenda_items) ? report.agenda_items as LograAgendaItem[] : [];
      setAgendaItems(loadedAgenda);
      await syncLograAgendaNotifications(loadedAgenda);
      setAgendaNotes(formatValue(report.agenda_notes) === "-" ? "" : formatValue(report.agenda_notes));
      setAttachments((Array.isArray(payload.attachments) ? payload.attachments : []).filter((item) => asRecord(item)) as LograAttachment[]);
      const title = formatValue(report.title);
      const answerSlug = rawAnswers.map((entry) => formatValue(asRecord(entry)?.form_slug)).find((value) => value !== "-");
      const reportSlug = formatValue(report.form_slug);
      const matched = ONG_QUESTIONNAIRES.find((form) => form.slug === reportSlug || form.slug === answerSlug)
        || ONG_QUESTIONNAIRES.find((form) => title.includes(form.title));
      if (matched) {
        setFormTitle(matched.title);
        setPortiaForm(matched.title);
        setReportIdsByForm((current) => ({ ...current, [matched.slug]: id }));
        const loadedVersion = Number(report.version || 1);
        setReportVersionsByForm((current) => ({ ...current, [matched.slug]: loadedVersion }));
      }
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar ONG.");
    } finally {
      setBusy(false);
    }
  }

  async function restoreLocalOngDraft() {
    try {
      const raw = await AsyncStorage.getItem(ONG_AUTOSAVE_DRAFT_KEY);
      if (!raw) return;
      const draft = asRecord(JSON.parse(raw));
      if (!draft || formatValue(draft.usuario) !== session.usuario) return;
      if (draft.formTitle && formatValue(draft.formTitle) !== "-") {
        setFormTitle(formatValue(draft.formTitle));
        setPortiaForm(formatValue(draft.formTitle));
      }
      if (draft.section && Object.keys(ONG_SECTION_LABELS).includes(formatValue(draft.section))) {
        setSection(formatValue(draft.section) as keyof typeof ONG_SECTION_LABELS);
      }
      if (asRecord(draft.answers)) setAnswers(draft.answers as Record<string, string[]>);
      if (asRecord(draft.reportIdsByForm)) setReportIdsByForm(draft.reportIdsByForm as Record<string, string>);
      if (asRecord(draft.reportVersionsByForm)) setReportVersionsByForm(draft.reportVersionsByForm as Record<string, number>);
      if (Array.isArray(draft.agendaItems)) setAgendaItems(draft.agendaItems as LograAgendaItem[]);
      setAgendaNotes(formatValue(draft.agendaNotes) === "-" ? "" : formatValue(draft.agendaNotes));
      setMessage("Borrador local ONG recuperado.");
    } catch {
      // Draft recovery should never block the form.
    }
  }

  function getBullets(form: LograQuestionnaire, selectedSection: keyof typeof ONG_SECTION_LABELS, item: LograQuestion) {
    const key = lograQuestionKey(form, selectedSection, item);
    return answers[key] || [""];
  }

  function changeLograForm(nextTitle: string) {
    const nextForm = ONG_QUESTIONNAIRES.find((item) => item.title === nextTitle);
    setFormTitle(nextTitle);
    setPortiaForm(nextTitle);
    setReportId(nextForm ? reportIdsByForm[nextForm.slug] || null : null);
  }

  function setBullet(form: LograQuestionnaire, selectedSection: keyof typeof ONG_SECTION_LABELS, item: LograQuestion, index: number, value: string) {
    const key = lograQuestionKey(form, selectedSection, item);
    setAnswers((current) => {
      const next = [...(current[key] || [""])];
      next[index] = value;
      return { ...current, [key]: next };
    });
  }

  function addBullet(form: LograQuestionnaire, selectedSection: keyof typeof ONG_SECTION_LABELS, item: LograQuestion) {
    const key = lograQuestionKey(form, selectedSection, item);
    setAnswers((current) => {
      const next = [...(current[key] || [""])];
      if (next.length >= ONG_MAX_BULLETS) {
        Alert.alert("ONG", "Cada pregunta permite maximo 20 bullet points.");
        return current;
      }
      next.push("");
      return { ...current, [key]: next };
    });
  }

  function removeBullet(form: LograQuestionnaire, selectedSection: keyof typeof ONG_SECTION_LABELS, item: LograQuestion) {
    const key = lograQuestionKey(form, selectedSection, item);
    setAnswers((current) => {
      const next = [...(current[key] || [""])];
      if (next.length <= 1) next[0] = "";
      else next.pop();
      return { ...current, [key]: next };
    });
  }

  function addAgendaLine() {
    const hasValue = [agendaDraft.place, agendaDraft.person, agendaDraft.topic].some((value) => String(value || "").trim());
    if (!hasValue) {
      Alert.alert("Agenda ONG", "Agrega al menos persona, tema o lugar.");
      return;
    }
    if (agendaItems.length >= 150) {
      Alert.alert("Agenda ONG", "La agenda soporta hasta 150 lineas.");
      return;
    }
    const dateIso = agendaDraft.date_iso || formatYmd(new Date());
    setAgendaItems((current) => [...current, { ...agendaDraft, date: longEnglishDate(dateIso), date_iso: dateIso }]);
    setAgendaDraft(blankAgendaItem());
  }

  function removeAgendaLine() {
    if (selectedAgenda === null || !agendaItems[selectedAgenda]) {
      Alert.alert("Agenda ONG", "Selecciona una linea de agenda.");
      return;
    }
    Alert.alert("Agenda ONG", "Desea eliminar la linea seleccionada?", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Eliminar",
        style: "destructive",
        onPress: () => {
          setAgendaItems((current) => current.filter((_, index) => index !== selectedAgenda));
          setSelectedAgenda(null);
        }
      }
    ]);
  }

  function changeAgendaStatus() {
    if (selectedAgenda === null || !agendaItems[selectedAgenda]) {
      Alert.alert("Agenda ONG", "Selecciona una linea de agenda.");
      return;
    }
    setAgendaStatusDraft(String(agendaItems[selectedAgenda].status || "Pendiente"));
    setAgendaStatusOpen(true);
  }

  function openAgendaNotes() {
    if (selectedAgenda === null || !agendaItems[selectedAgenda]) {
      Alert.alert("Agenda ONG", "Selecciona una linea de agenda.");
      return;
    }
    setAgendaLineNote(String(agendaItems[selectedAgenda].notes || ""));
    setAgendaNotesOpen(true);
  }

  function saveAgendaLineNote() {
    if (selectedAgenda === null) return;
    updateSelectedAgendaLine({ notes: agendaLineNote }, false).then((updated) => {
      if (updated) setAgendaNotesOpen(false);
    });
  }

  async function searchAgenda() {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>("/logra-reports", { session });
      const reports = rowsFromAny(payload);
      const agendaReports = reports.filter((report) => formatValue(report.title).trim().toLowerCase() === "ong - agenda");
      const sourceReports = agendaReports.length ? agendaReports : reports;
      const nextItems: LograAgendaItem[] = [];
      const seen = new Set<string>();
      sourceReports.forEach((report) => {
        const reportTitle = formatValue(report.title);
        const items = Array.isArray(report.agenda_items) ? report.agenda_items : [];
        items.forEach((item, agendaIndex) => {
          const record = asRecord(item);
          if (!record || nextItems.length >= 150) return;
          const dateIso = formatValue(record.date_iso || record.date).slice(0, 10);
          const nextItem = {
            ...(record as LograAgendaItem),
            report_id: formatValue(report.id),
            agenda_index: agendaIndex,
            report_title: reportTitle,
            date_iso: dateIso === "-" ? formatYmd(new Date()) : dateIso,
            date: longEnglishDate(dateIso === "-" ? formatYmd(new Date()) : dateIso),
            phone: formatValue(record.phone || record.telefono),
            company: formatValue(record.company || record.company_role),
            topic: formatValue(record.topic) === "-" ? reportTitle : formatValue(record.topic)
          };
          const key = lograAgendaKey(nextItem);
          if (seen.has(key)) return;
          seen.add(key);
          nextItems.push(nextItem);
        });
      });
      setAgendaItems(nextItems);
      setSelectedAgenda(null);
      await syncLograAgendaNotifications(nextItems);
      setMessage(nextItems.length ? `Agenda cargada: ${nextItems.length} linea(s).` : "No hay agendas ONG guardadas en backend.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo buscar agenda ONG.");
    } finally {
      setBusy(false);
    }
  }

  function buildAnswersPayload() {
    const payload: Array<Record<string, unknown>> = [];
    if (!selectedForm) return payload;
    (Object.keys(ONG_SECTION_LABELS) as Array<keyof typeof ONG_SECTION_LABELS>).forEach((selectedSection) => {
      selectedForm[selectedSection].forEach((item) => {
        const key = lograQuestionKey(selectedForm, selectedSection, item);
        const bullets = (answers[key] || []).map((value) => value.trim()).filter(Boolean).slice(0, ONG_MAX_BULLETS);
        if (!bullets.length) return;
        payload.push({
          form_slug: selectedForm.slug,
          form_title: selectedForm.title,
          section: selectedSection,
          item_key: lograItemKey(item),
          question_text: item.question,
          bullets
        });
      });
    });
    return payload;
  }

  function buildLograPayload(targetReportId: string | null = reportId) {
    const formSlug = selectedForm?.slug || "";
    const payload: Record<string, unknown> = {
      id: targetReportId,
      title: `ONG - ${formTitle || "Cuestionarios"}`,
      form_slug: formSlug,
      category: "ONG",
      status: "Pending",
      created_by: session.usuario,
      agenda_items: [],
      agenda_notes: "",
      answers: buildAnswersPayload()
    };
    const expectedVersion = reportVersionsByForm[formSlug];
    if (expectedVersion !== undefined) payload.expected_version = expectedVersion;
    return payload;
  }

  async function saveLocalOngDraft() {
    const payload = {
      reportId,
      reportIdsByForm,
      reportVersionsByForm,
      formTitle,
      section,
      answers,
      agendaItems,
      agendaNotes,
      savedAt: new Date().toISOString(),
      usuario: session.usuario
    };
    await AsyncStorage.setItem(ONG_AUTOSAVE_DRAFT_KEY, JSON.stringify(payload));
  }

  function buildAgendaItemFromDraft(currentItem: LograAgendaItem) {
    const dateIso = String(agendaDraft.date_iso || currentItem.date_iso || formatYmd(new Date())).slice(0, 10);
    const nextItem: LograAgendaItem = {
      ...currentItem,
      ...agendaDraft,
      date_iso: dateIso,
      date: longEnglishDate(dateIso),
      reminder_minutes: Number(agendaDraft.reminder_minutes || currentItem.reminder_minutes || 30)
    };
    const hasValue = [nextItem.place, nextItem.person, nextItem.topic].some((value) => String(value || "").trim());
    if (!hasValue) {
      Alert.alert("Agenda ONG", "Agrega al menos persona, tema o lugar.");
      return null;
    }
    return nextItem;
  }

  async function saveAgendaOnly() {
    let itemsToSave = agendaItems;
    if (selectedAgenda !== null && agendaItems[selectedAgenda]) {
      const nextItem = buildAgendaItemFromDraft(agendaItems[selectedAgenda]);
      if (!nextItem) return;
      itemsToSave = agendaItems.map((item, index) => index === selectedAgenda ? nextItem : item);
    }

    if (!itemsToSave.length) {
      setMessage("No hay lineas de agenda para guardar.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const result = await offlineApiRequest("/logra-reports/agenda-only", {
        method: "POST",
        body: {
          created_by: session.usuario,
          agenda_items: itemsToSave,
          agenda_notes: agendaNotes
        },
        session,
        offlineLabel: "Guardar agenda ONG"
      });
      if (!isQueuedOffline(result)) {
        const record = asRecord(result);
        const report = asRecord(record?.report);
        const savedItems = Array.isArray(report?.agenda_items) ? report.agenda_items : itemsToSave;
        const agendaReportId = formatValue(report?.id);
        const normalizedItems = savedItems.map((item, index) => ({
          ...(asRecord(item) as LograAgendaItem),
          report_id: agendaReportId,
          agenda_index: index,
          report_title: "ONG - Agenda"
        }));
        setAgendaItems(normalizedItems);
        setSelectedAgenda(null);
        setAgendaDraft(blankAgendaItem());
        await syncLograAgendaNotifications(normalizedItems);
      }
      setMessage(isQueuedOffline(result) ? "Sin internet: agenda ONG guardada en cache local." : "Agenda ONG guardada correctamente.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar agenda ONG.");
    } finally {
      setBusy(false);
    }
  }

  function loadSelectedAgendaLine() {
    if (selectedAgenda === null || !agendaItems[selectedAgenda]) {
      Alert.alert("Agenda ONG", "Selecciona una linea de agenda.");
      return;
    }
    setAgendaDraft({ ...blankAgendaItem(), ...agendaItems[selectedAgenda] });
  }

  function selectAgendaLine(index: number) {
    setSelectedAgenda(index);
    setAgendaDraft({ ...blankAgendaItem(), ...agendaItems[index] });
  }

  function runAgendaAction() {
    if (agendaAction === "Nueva") {
      addAgendaLine();
      return;
    }
    if (agendaAction === "Cargar seleccion") {
      loadSelectedAgendaLine();
      return;
    }
    if (agendaAction === "Editar agenda") {
      updateSelectedAgendaLine();
      return;
    }
    if (agendaAction === "Cambiar status") {
      changeAgendaStatus();
      return;
    }
    if (agendaAction === "Notas") {
      openAgendaNotes();
      return;
    }
    if (agendaAction === "Eliminar") {
      removeAgendaLine();
    }
  }

  function resetAgendaDraftForNewLine() {
    setAgendaDraft(blankAgendaItem());
    setSelectedAgenda(null);
  }

  async function updateSelectedAgendaLine(extraValues: Partial<LograAgendaItem> = {}, useDraft = true) {
    if (selectedAgenda === null || !agendaItems[selectedAgenda]) {
      Alert.alert("Agenda ONG", "Selecciona una linea de agenda.");
      return false;
    }
    const currentItem = agendaItems[selectedAgenda];
    const nextItem = useDraft
      ? buildAgendaItemFromDraft({ ...currentItem, ...extraValues })
      : { ...currentItem, ...extraValues };
    if (!nextItem) return false;

    setBusy(true);
    setMessage("");
    try {
      const itemReportId = formatValue(nextItem.report_id || reportId);
      const itemAgendaIndex = Number(nextItem.agenda_index ?? selectedAgenda);
      if (itemReportId !== "-" && Number.isFinite(itemAgendaIndex)) {
        await apiRequest(`/logra-reports/${encodeURIComponent(itemReportId)}/agenda-items/${itemAgendaIndex}`, {
          method: "PUT",
          session,
          body: nextItem
        });
      }
      const nextItems = agendaItems.map((item, index) => index === selectedAgenda ? nextItem : item);
      setAgendaItems(nextItems);
      await syncLograAgendaNotifications(nextItems);
      setAgendaDraft(blankAgendaItem());
      setSelectedAgenda(null);
      setMessage(itemReportId === "-" ? "Linea actualizada localmente. Guarda ONG para persistirla." : "Linea de agenda actualizada.");
      return true;
    } catch (err) {
      Alert.alert("Agenda ONG", err instanceof Error ? err.message : "No se pudo actualizar la linea.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function saveLogra(closeAfterSave = true) {
    setBusy(true);
    setMessage("");
    try {
      await saveLocalOngDraft();
      const payload = buildLograPayload();
      const endpoint = reportId ? `/logra-reports/${encodeURIComponent(reportId)}` : "/logra-reports";
      const result = await offlineApiRequest(endpoint, {
        method: reportId ? "PUT" : "POST",
        body: payload,
        session,
        offlineLabel: "Guardar ONG"
      });
      if (!isQueuedOffline(result)) {
        const record = asRecord(result);
        const report = asRecord(record?.report);
        const nextId = formatValue(report?.id);
        if (nextId !== "-") {
          setReportId(nextId);
          const formSlug = selectedForm?.slug || formatValue(report?.form_slug);
          if (formSlug && formSlug !== "-") {
            setReportIdsByForm((current) => ({ ...current, [formSlug]: nextId }));
            setReportVersionsByForm((current) => ({ ...current, [formSlug]: Number(report?.version || 1) }));
          }
          const expectedAnswerCount = buildAnswersPayload().length;
          if (Number(record?.saved_answer_count || 0) < expectedAnswerCount) {
            throw new Error("El backend no confirmo todas las respuestas enviadas.");
          }
          await syncLograAgendaNotifications(agendaItems);
          setMessage("ONG guardado correctamente.");
          if (closeAfterSave) await onSaved();
          return nextId;
        }
      }
      setMessage(isQueuedOffline(result) ? "Sin internet: ONG guardado en cache local para sincronizar." : "ONG guardado correctamente.");
      if (closeAfterSave) await onSaved();
      return reportId;
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar ONG.");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function autosaveLogra() {
    try {
      await saveLocalOngDraft();
      const payload = buildLograPayload();
      const hasAnswers = Array.isArray(payload.answers) && payload.answers.length > 0;
      if (!reportId && !hasAnswers) {
        setMessage("Autosave ONG local.");
        return;
      }
      const endpoint = reportId ? `/logra-reports/${encodeURIComponent(reportId)}` : "/logra-reports";
      const result = await offlineApiRequest(endpoint, {
        method: reportId ? "PUT" : "POST",
        body: payload,
        session,
        offlineLabel: `Autosave ONG ${formTitle || "Cuestionarios"}`
      });
      if (!isQueuedOffline(result)) {
        const record = asRecord(result);
        const report = asRecord(record?.report);
        const expectedAnswerCount = buildAnswersPayload().length;
        if (Number(record?.saved_answer_count || 0) < expectedAnswerCount) {
          throw new Error("El backend no confirmo todas las respuestas del autosave.");
        }
        const nextId = formatValue(report?.id);
        if (nextId !== "-") {
          setReportId(nextId);
          const formSlug = selectedForm?.slug || formatValue(report?.form_slug);
          if (formSlug && formSlug !== "-") {
            setReportIdsByForm((current) => ({ ...current, [formSlug]: nextId }));
            setReportVersionsByForm((current) => ({ ...current, [formSlug]: Number(report?.version || 1) }));
          }
        }
        setMessage(`Autosave ONG ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
      } else {
        setMessage("Sin internet: autosave ONG guardado en cache local.");
      }
    } catch {
      // Autosave must not interrupt editing.
    }
  }

  async function runPortia() {
    if (!portiaSelectedForm || !portiaSelectedQuestion) return;
    const bulletIndex = Number(portiaBullet || 0);
    const currentText = (portiaBullets[bulletIndex] || "").trim();
    if (!currentText) {
      Alert.alert("PORTIA", "El bullet seleccionado esta vacio.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await apiRequest<Record<string, unknown>>("/reports/ai/improve/logra", {
        method: "POST",
        session,
        body: {
          text: currentText,
          language: portiaLanguage,
          report_type: ONG_SECTION_LABELS[portiaSection],
          form_title: portiaSelectedForm.title,
          question: portiaSelectedQuestion.question
        }
      });
      const improved = formatValue(response.text || response.improved_text || response.result);
      if (improved === "-") {
        setMessage("PORTIA no devolvio texto valido.");
        return;
      }
      setPortiaResult({ original: currentText, improved, answerKey: portiaAnswerKey, bulletIndex });
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo mejorar el texto.");
    } finally {
      setBusy(false);
    }
  }

  async function updateQuestionAnswer(form: LograQuestionnaire, selectedSection: keyof typeof ONG_SECTION_LABELS, item: LograQuestion) {
    setBusy(true);
    setMessage("");
    try {
      let targetReportId = reportId;
      if (!targetReportId) {
        targetReportId = await saveLogra(false);
      }
      if (!targetReportId) throw new Error("Primero se debe guardar ONG para actualizar la pregunta.");
      const key = lograQuestionKey(form, selectedSection, item);
      const bullets = (answers[key] || []).map((value) => value.trim()).filter(Boolean).slice(0, ONG_MAX_BULLETS);
      await apiRequest(`/logra-reports/${encodeURIComponent(targetReportId)}/answers`, {
        method: "PUT",
        session,
        body: {
          form_slug: form.slug,
          form_title: form.title,
          section: selectedSection,
          item_key: lograItemKey(item),
          question_text: item.question,
          bullets
        }
      });
      setMessage("Pregunta actualizada correctamente.");
    } catch (err) {
      Alert.alert("ONG", err instanceof Error ? err.message : "No se pudo actualizar la pregunta.");
    } finally {
      setBusy(false);
    }
  }

  async function openAttachment(attachment: LograAttachment) {
    try {
      const filename = cleanFilePart(attachment.original_filename || `logra_${attachment.id}.bin`);
      const downloadUrl = `${API_BASE_URL}/logra-reports/attachments/${attachment.id}/download`;
      if (Platform.OS === "android") {
        await Linking.openURL(downloadUrl);
        return;
      }
      const fileUri = `${FileSystem.cacheDirectory || ""}${Date.now()}_${filename}`;
      const headers = {
        Accept: "application/octet-stream, application/pdf, application/vnd.openxmlformats-officedocument.spreadsheetml.sheet, */*",
        "X-User": session.usuario,
        "X-Role": session.rol,
        "X-User-Role": session.rol
      };
      const result = await FileSystem.downloadAsync(
        downloadUrl,
        fileUri,
        { headers }
      );
      if (result.status < 200 || result.status >= 300) {
        throw new Error(`No se pudo descargar el adjunto (${result.status}).`);
      }
      await openDownloadedFile(result.uri, filename, attachment.content_type);
    } catch (err) {
      Alert.alert("ONG", err instanceof Error ? err.message : "No se pudo abrir el adjunto.");
    }
  }

  async function attachLograFile(form: LograQuestionnaire, selectedSection: keyof typeof ONG_SECTION_LABELS, item: LograQuestion) {
    const itemKey = lograItemKey(item);
    const existing = attachments.filter((att) => att.form_slug === form.slug && att.section === selectedSection && att.item_key === itemKey);
    if (existing.length >= 10) {
      Alert.alert("ONG", "Cada pregunta permite maximo 10 adjuntos.");
      return;
    }

    const picked = await DocumentPicker.getDocumentAsync({
      copyToCacheDirectory: true,
      multiple: false,
      type: "*/*"
    });
    if (picked.canceled) return;

    const asset = picked.assets?.[0];
    if (!asset?.uri) {
      Alert.alert("ONG", "No se selecciono un archivo valido.");
      return;
    }

    setBusy(true);
    setMessage("");
    try {
      const savedId = await saveLogra(false);
      if (!savedId) throw new Error("Primero se debe guardar ONG para adjuntar archivos.");

      const formData = new FormData();
      formData.append("form_slug", form.slug);
      formData.append("section", selectedSection);
      formData.append("item_key", itemKey);
      formData.append("file", {
        uri: asset.uri,
        name: asset.name || "logra_attachment",
        type: asset.mimeType || "application/octet-stream"
      } as unknown as Blob);

      const response = await fetch(`${API_BASE_URL}/logra-reports/${encodeURIComponent(savedId)}/attachments`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "X-User": session.usuario,
          "X-Role": session.rol,
          "X-User-Role": session.rol
        },
        body: formData
      });
      const text = await response.text();
      const payload = text ? JSON.parse(text) as Record<string, unknown> : {};
      if (!response.ok) {
        throw new Error(formatValue(payload.detail || payload.error || payload.message || `Error ${response.status}`));
      }

      await loadReport(savedId);
      setMessage("Adjunto guardado correctamente.");
    } catch (err) {
      Alert.alert("ONG", err instanceof Error ? err.message : "No se pudo adjuntar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  function deleteAttachment(attachment: LograAttachment) {
    Alert.alert("ONG", `Eliminar adjunto?\n\n${attachment.original_filename}`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Eliminar",
        style: "destructive",
        onPress: async () => {
          try {
            await apiRequest(`/logra-reports/attachments/${attachment.id}`, { method: "DELETE", session });
            setAttachments((current) => current.filter((item) => item.id !== attachment.id));
          } catch (err) {
            Alert.alert("ONG", err instanceof Error ? err.message : "No se pudo eliminar el adjunto.");
          }
        }
      }
    ]);
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>ONG - Cuestionarios</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          <View style={styles.actionBar}>
            <Pressable style={styles.secondaryButton} onPress={() => setAgendaOpen(true)}><Text style={styles.secondaryButtonText}>Agenda ONG</Text></Pressable>
            <Pressable style={styles.secondaryButton} onPress={() => setPortiaOpen(true)}><Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text></Pressable>
            <Pressable style={styles.actionButton} onPress={() => saveLogra()}><Text style={styles.actionButtonText}>Guardar</Text></Pressable>
          </View>
          <SelectField label="Formulario" value={formTitle} options={ONG_QUESTIONNAIRES.map((item) => item.title)} onChange={changeLograForm} />
          <SelectField label="Seccion" value={section} options={Object.keys(ONG_SECTION_LABELS)} onChange={(value) => setSection(value as keyof typeof ONG_SECTION_LABELS)} />
          <Text style={styles.helperText}>{ONG_SECTION_LABELS[section]} | Apertura: {selectedForm?.critical_questions.length || 0} | Por tema: {selectedForm?.detailed_questions.length || 0} | Total: {(selectedForm?.critical_questions.length || 0) + (selectedForm?.detailed_questions.length || 0)}</Text>
          <Text style={styles.label}>Buscar</Text>
          <TextInput style={styles.input} value={search} onChangeText={setSearch} placeholder="Palabra clave" />
          <Text style={styles.helperText}>Agenda ONG: {agendaItems.length} linea(s) cargadas.</Text>

          <View style={styles.actionBar}>
            <Pressable style={styles.modalClose} onPress={() => setPage((current) => Math.max(0, current - 1))}><Text style={styles.modalCloseText}>Anterior</Text></Pressable>
            <Text style={styles.helperText}>Pagina {page + 1} de {totalPages} - {filteredItems.length} preguntas</Text>
            <Pressable style={styles.modalClose} onPress={() => setPage((current) => Math.min(totalPages - 1, current + 1))}><Text style={styles.modalCloseText}>Siguiente</Text></Pressable>
          </View>

          {pageItems.map((item) => {
            const bullets = selectedForm ? getBullets(selectedForm, section, item) : [""];
            const itemKey = lograItemKey(item);
            const questionAttachments = attachments.filter((att) => att.form_slug === selectedForm.slug && att.section === section && att.item_key === itemKey);
            return (
              <View key={`${selectedForm.slug}-${section}-${itemKey}`} style={styles.summaryBox}>
                <Text style={styles.cardTitle}>{itemKey}</Text>
                {item.block ? <Text style={styles.helperText}>{item.block}</Text> : null}
                <Text style={styles.fieldValue}>{item.question}</Text>
                {bullets.map((bullet, index) => (
                  <View key={index} style={styles.formField}>
                    <Text style={styles.label}>{index + 1}.</Text>
                    <TextInput style={[styles.input, styles.multilineInput]} multiline value={bullet} onChangeText={(value) => setBullet(selectedForm, section, item, index, value)} />
                  </View>
                ))}
                <View style={styles.actionBar}>
                  <Pressable style={styles.secondaryButton} onPress={() => addBullet(selectedForm, section, item)}><Text style={styles.secondaryButtonText}>+ Bullet</Text></Pressable>
                  <Pressable style={styles.modalClose} onPress={() => removeBullet(selectedForm, section, item)}><Text style={styles.modalCloseText}>- Bullet</Text></Pressable>
                  <Pressable
                    style={styles.secondaryButton}
                    onPress={() => attachLograFile(selectedForm, section, item)}
                  >
                    <Text style={styles.secondaryButtonText}>Adjuntar</Text>
                  </Pressable>
                  <Pressable style={styles.secondaryButton} onPress={() => updateQuestionAnswer(selectedForm, section, item)}>
                    <Text style={styles.secondaryButtonText}>Actualizar pregunta</Text>
                  </Pressable>
                </View>
                {questionAttachments.length ? <Text style={styles.label}>Adjuntos</Text> : null}
                {questionAttachments.map((attachment) => (
                  <View key={attachment.id} style={styles.inlineFields}>
                    <Pressable style={styles.secondaryButton} onPress={() => openAttachment(attachment)}><Text style={styles.secondaryButtonText}>{attachment.original_filename}</Text></Pressable>
                    <Pressable style={styles.modalClose} onPress={() => deleteAttachment(attachment)}><Text style={styles.modalCloseText}>-</Text></Pressable>
                  </View>
                ))}
              </View>
            );
          })}
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>

        <Modal visible={agendaOpen} animationType="slide" onRequestClose={() => setAgendaOpen(false)}>
          <SafeAreaView style={styles.modalScreen}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Agenda ONG</Text>
              <Pressable style={styles.modalClose} onPress={() => setAgendaOpen(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
            </View>
            <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
              <View style={styles.summaryBox}>
                <Text style={styles.cardTitle}>Meeting details</Text>
                <DateField label="Date" value={agendaDraft.date_iso || formatYmd(new Date())} onChange={(date_iso) => setAgendaDraft((current) => ({ ...current, date_iso, date: longEnglishDate(date_iso) }))} />
                <Text style={styles.helperText}>{longEnglishDate(agendaDraft.date_iso || formatYmd(new Date()))}</Text>
                <Text style={styles.label}>Start</Text>
                <View style={styles.inlineFields}>
                  <TextInput style={[styles.input, styles.timePartInput]} value={(agendaDraft.start_time || "09:00").slice(0, 2)} keyboardType="number-pad" maxLength={2} onChangeText={(hour) => setAgendaDraft((current) => ({ ...current, start_time: `${hour.padStart(2, "0").slice(0, 2)}:${(current.start_time || "09:00").slice(3, 5)}` }))} />
                  <Text style={styles.helperText}>:</Text>
                  <TextInput style={[styles.input, styles.timePartInput]} value={(agendaDraft.start_time || "09:00").slice(3, 5)} keyboardType="number-pad" maxLength={2} onChangeText={(minute) => setAgendaDraft((current) => ({ ...current, start_time: `${(current.start_time || "09:00").slice(0, 2)}:${minute.padStart(2, "0").slice(0, 2)}` }))} />
                </View>
                <Text style={styles.label}>End</Text>
                <View style={styles.inlineFields}>
                  <TextInput style={[styles.input, styles.timePartInput]} value={(agendaDraft.end_time || "10:00").slice(0, 2)} keyboardType="number-pad" maxLength={2} onChangeText={(hour) => setAgendaDraft((current) => ({ ...current, end_time: `${hour.padStart(2, "0").slice(0, 2)}:${(current.end_time || "10:00").slice(3, 5)}` }))} />
                  <Text style={styles.helperText}>:</Text>
                  <TextInput style={[styles.input, styles.timePartInput]} value={(agendaDraft.end_time || "10:00").slice(3, 5)} keyboardType="number-pad" maxLength={2} onChangeText={(minute) => setAgendaDraft((current) => ({ ...current, end_time: `${(current.end_time || "10:00").slice(0, 2)}:${minute.padStart(2, "0").slice(0, 2)}` }))} />
                </View>
                {["place", "person", "phone", "company", "topic"].map((field) => (
                  <View key={field} style={styles.formField}>
                    <Text style={styles.label}>{field === "place" ? "Place" : field === "person" ? "Person" : field === "phone" ? "Phone" : field === "company" ? "Company/Role" : "Topic"}</Text>
                    <TextInput style={styles.input} value={String(agendaDraft[field as keyof LograAgendaItem] || "")} onChangeText={(value) => setAgendaDraft((current) => ({ ...current, [field]: value }))} />
                  </View>
                ))}
                <SelectField label="Priority" value={String(agendaDraft.priority || "Media")} options={["Alta", "Media", "Baja"]} onChange={(priority) => setAgendaDraft((current) => ({ ...current, priority }))} />
                <SelectField label="Status" value={String(agendaDraft.status || "Pendiente")} options={["Pendiente", "En proceso", "Completado"]} onChange={(status) => setAgendaDraft((current) => ({ ...current, status }))} />
                <Text style={styles.label}>Reminder min</Text>
                <TextInput style={styles.input} keyboardType="number-pad" value={String(agendaDraft.reminder_minutes || 30)} onChangeText={(reminder_minutes) => setAgendaDraft((current) => ({ ...current, reminder_minutes }))} />
                <Pressable style={styles.actionButton} onPress={() => updateSelectedAgendaLine()}>
                  <Text style={styles.actionButtonText}>Editar agenda</Text>
                </Pressable>
              </View>

              <View style={styles.lograAgendaToolbar}>
                <View style={styles.lograToolbarHeader}>
                  <Pressable style={styles.secondaryButtonCompact} onPress={searchAgenda}><Text style={styles.secondaryButtonText}>Buscar</Text></Pressable>
                  <Pressable style={styles.secondaryButtonCompact} onPress={resetAgendaDraftForNewLine}><Text style={styles.secondaryButtonText}>Nueva</Text></Pressable>
                  <Pressable style={styles.actionButtonCompact} onPress={() => updateSelectedAgendaLine()}><Text style={styles.actionButtonText}>Editar agenda</Text></Pressable>
                  <Pressable style={styles.secondaryButtonCompact} onPress={changeAgendaStatus}><Text style={styles.secondaryButtonText}>Status</Text></Pressable>
                  <Pressable style={styles.secondaryButtonCompact} onPress={openAgendaNotes}><Text style={styles.secondaryButtonText}>Notas</Text></Pressable>
                  <Pressable style={styles.secondaryButtonCompact} onPress={removeAgendaLine}><Text style={styles.secondaryButtonText}>Eliminar</Text></Pressable>
                  <View style={styles.segmentedControl}>
                    <Pressable style={[styles.segmentedOption, agendaView === "list" && styles.segmentedOptionActive]} onPress={() => setAgendaView("list")}>
                      <Text style={agendaView === "list" ? styles.segmentedTextActive : styles.segmentedText}>Lista</Text>
                    </Pressable>
                    <Pressable style={[styles.segmentedOption, agendaView === "calendar" && styles.segmentedOptionActive]} onPress={() => setAgendaView("calendar")}>
                      <Text style={agendaView === "calendar" ? styles.segmentedTextActive : styles.segmentedText}>Calendario</Text>
                    </Pressable>
                  </View>
                  <Pressable style={styles.actionButton} onPress={saveAgendaOnly}><Text style={styles.actionButtonText}>Guardar</Text></Pressable>
                </View>

                <View style={styles.contextActionPanel}>
                  <Text style={styles.contextActionTitle}>Reunion</Text>
                  <View style={styles.contextActionRow}>
                    <View style={styles.contextActionSelect}>
                      <SelectField
                        label="Accion"
                        value={agendaAction}
                        options={["Nueva", "Cargar seleccion", "Editar agenda", "Cambiar status", "Notas", "Eliminar"]}
                        onChange={setAgendaAction}
                      />
                    </View>
                    <Pressable style={styles.actionButtonCompact} onPress={runAgendaAction}><Text style={styles.actionButtonText}>Ejecutar</Text></Pressable>
                    {selectedAgenda !== null && agendaItems[selectedAgenda] ? (
                      <Text style={styles.helperText}>Seleccionada: {agendaItems[selectedAgenda].topic || agendaItems[selectedAgenda].person || "Reunion ONG"}</Text>
                    ) : (
                      <Text style={styles.helperText}>Selecciona una linea para editar, status, notas o eliminar.</Text>
                    )}
                  </View>
                </View>
              </View>

              {agendaView === "calendar" ? (
                <View style={styles.lograCalendarPanel}>
                  <View style={styles.lograCalendarHeader}>
                    <Pressable style={styles.modalClose} onPress={() => setCalendarMonth((current) => new Date(current.getFullYear(), current.getMonth() - 1, 1))}>
                      <Text style={styles.modalCloseText}>Anterior</Text>
                    </Pressable>
                    <Text style={styles.lograCalendarTitle}>{monthName(calendarMonth)}</Text>
                    <Pressable style={styles.modalClose} onPress={() => setCalendarMonth((current) => new Date(current.getFullYear(), current.getMonth() + 1, 1))}>
                      <Text style={styles.modalCloseText}>Siguiente</Text>
                    </Pressable>
                  </View>
                  <View style={styles.lograCalendarWeekRow}>
                    {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => <Text key={day} style={styles.lograCalendarWeekday}>{day}</Text>)}
                  </View>
                  <View style={styles.lograCalendarGrid}>
                    {calendarDays.map((day) => {
                      const dayKey = formatYmd(day);
                      const meetings = agendaByDate[dayKey] || [];
                      const inMonth = day.getMonth() === calendarMonth.getMonth();
                      return (
                        <Pressable
                          key={dayKey}
                          style={[styles.lograCalendarDay, !inMonth && styles.lograCalendarDayMuted]}
                          onPress={() => {
                            setAgendaDraft((current) => ({ ...current, date_iso: dayKey, date: longEnglishDate(dayKey) }));
                            if (meetings[0]) {
                              const agendaIndex = agendaItems.findIndex((item) => lograAgendaKey(item) === lograAgendaKey(meetings[0]));
                              if (agendaIndex >= 0) selectAgendaLine(agendaIndex);
                            }
                          }}
                        >
                          <Text style={[styles.lograCalendarDayNumber, !inMonth && styles.lograCalendarDayNumberMuted]}>{day.getDate()}</Text>
                          {meetings.slice(0, 3).map((meeting, meetingIndex) => (
                            <View key={`${dayKey}-${meetingIndex}-${meeting.start_time}`} style={[styles.lograCalendarMeeting, { backgroundColor: lograAgendaTint(meeting) }]}>
                              <Text numberOfLines={1} style={styles.lograCalendarMeetingText}>{meeting.start_time || "--:--"} {meeting.topic || meeting.person || "Meeting"}</Text>
                            </View>
                          ))}
                          {meetings.length > 3 ? <Text style={styles.lograCalendarMoreText}>+{meetings.length - 3} mas</Text> : null}
                        </Pressable>
                      );
                    })}
                  </View>
                </View>
              ) : (
                <ScrollView horizontal>
                  <View>
                    <View style={[styles.lograAgendaRow, styles.lograAgendaHeader]}>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Date</Text>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Time</Text>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Place</Text>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Person</Text>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Phone</Text>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Company/Role</Text>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Topic</Text>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Priority</Text>
                      <Text style={[styles.lograAgendaCell, styles.lograAgendaHeaderCell]}>Status</Text>
                    </View>
                    {agendaItems.map((item, index) => (
                      <Pressable key={`${index}-${item.date_iso}-${item.start_time}`} style={[styles.lograAgendaRow, { backgroundColor: lograAgendaTint(item) }, selectedAgenda === index && styles.selectedRow]} onPress={() => selectAgendaLine(index)}>
                        <Text style={styles.lograAgendaCell}>{longEnglishDate(String(item.date_iso || item.date || ""))}</Text>
                        <Text style={styles.lograAgendaCell}>{item.start_time} - {item.end_time}</Text>
                        <Text style={styles.lograAgendaCell}>{item.place}</Text>
                        <Text style={styles.lograAgendaCell}>{item.person}</Text>
                        <Text style={styles.lograAgendaCell}>{item.phone || item.telefono}</Text>
                        <Text style={styles.lograAgendaCell}>{item.company || item.company_role}</Text>
                        <Text style={styles.lograAgendaCell}>{item.topic}</Text>
                        <Text style={styles.lograAgendaCell}>{item.priority}</Text>
                        <Text style={styles.lograAgendaCell}>{item.status}</Text>
                      </Pressable>
                    ))}
                  </View>
                </ScrollView>
              )}
              {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
              {message ? <Text style={styles.error}>{message}</Text> : null}
            </ScrollView>
          </SafeAreaView>
        </Modal>

        <Modal visible={agendaStatusOpen} animationType="slide" onRequestClose={() => setAgendaStatusOpen(false)}>
          <SafeAreaView style={styles.modalScreen}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Cambiar status</Text>
              <Pressable style={styles.modalClose} onPress={() => setAgendaStatusOpen(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
            </View>
            <ScrollView contentContainerStyle={styles.modalBody}>
              <Text style={styles.label}>Status</Text>
              <Text style={styles.helperText}>
                Actual: {selectedAgenda !== null ? String(agendaItems[selectedAgenda]?.status || "Pendiente") : "Selecciona una linea"}
              </Text>
              <SelectField label="Nuevo status" value={agendaStatusDraft} options={["Pendiente", "En proceso", "Completado"]} onChange={setAgendaStatusDraft} />
              <Pressable
                style={styles.actionButton}
                onPress={() => {
                  if (selectedAgenda === null) {
                    Alert.alert("Agenda ONG", "Selecciona una linea de agenda.");
                    return;
                  }
                  updateSelectedAgendaLine({ status: agendaStatusDraft }, false).then((updated) => {
                    if (updated) setAgendaStatusOpen(false);
                  });
                }}
              >
                <Text style={styles.actionButtonText}>Actualizar status</Text>
              </Pressable>
            </ScrollView>
          </SafeAreaView>
        </Modal>

        <Modal visible={agendaNotesOpen} animationType="slide" onRequestClose={() => setAgendaNotesOpen(false)}>
          <SafeAreaView style={styles.modalScreen}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Anotaciones de agenda</Text>
              <Pressable style={styles.modalClose} onPress={() => setAgendaNotesOpen(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
            </View>
            <ScrollView contentContainerStyle={styles.modalBody}>
              <Text style={styles.helperText}>
                {selectedAgenda !== null && agendaItems[selectedAgenda]
                  ? `${agendaItems[selectedAgenda].topic || "Reunion ONG"} - ${agendaItems[selectedAgenda].person || ""}`
                  : "Selecciona una linea de agenda."}
              </Text>
              <TextInput style={[styles.input, styles.multilineInput]} multiline value={agendaLineNote} onChangeText={setAgendaLineNote} />
              <Pressable style={styles.actionButton} onPress={saveAgendaLineNote}><Text style={styles.actionButtonText}>Guardar anotaciones</Text></Pressable>
            </ScrollView>
          </SafeAreaView>
        </Modal>

        <Modal visible={portiaOpen} animationType="slide" onRequestClose={() => setPortiaOpen(false)}>
          <SafeAreaView style={styles.modalScreen}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Mejorar con PORTIA - ONG</Text>
              <Pressable style={styles.modalClose} onPress={() => setPortiaOpen(false)}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
            </View>
            <ScrollView contentContainerStyle={styles.modalBody}>
              <SelectField label="Formulario" value={portiaForm} options={ONG_QUESTIONNAIRES.map((item) => item.title)} onChange={setPortiaForm} />
              <SelectField label="Tipo" value={portiaSection} options={Object.keys(ONG_SECTION_LABELS)} onChange={(value) => setPortiaSection(value as keyof typeof ONG_SECTION_LABELS)} />
              <SelectField label="Pregunta" value={portiaQuestionKey} options={portiaQuestions.map(lograItemKey)} onChange={(value) => { setPortiaQuestionKey(value); setPortiaBullet("0"); }} />
              {portiaSelectedQuestion ? <Text style={styles.fieldValue}>{portiaSelectedQuestion.question}</Text> : null}
              <SelectField label="Bullet" value={portiaBullet} options={portiaBullets.map((_, index) => String(index))} onChange={setPortiaBullet} />
              <SelectField label="Salida" value={portiaLanguage} options={["ES", "EN"]} onChange={setPortiaLanguage} />
              <Pressable style={styles.actionButton} onPress={runPortia}><Text style={styles.actionButtonText}>Mejorar con PORTIA</Text></Pressable>
              {portiaResult ? (
                <View style={styles.summaryBox}>
                  <Text style={styles.cardTitle}>Comparacion</Text>
                  <Text style={styles.label}>Original</Text>
                  <Text style={styles.fieldValue}>{portiaResult.original}</Text>
                  <Text style={styles.label}>PORTIA</Text>
                  <Text style={styles.fieldValue}>{portiaResult.improved}</Text>
                  <Pressable
                    style={styles.actionButton}
                    onPress={() => {
                      setAnswers((current) => {
                        const next = [...(current[portiaResult.answerKey] || [""])];
                        while (next.length <= portiaResult.bulletIndex) next.push("");
                        next[portiaResult.bulletIndex] = portiaResult.improved;
                        return { ...current, [portiaResult.answerKey]: next };
                      });
                      setPortiaResult(null);
                      setPortiaOpen(false);
                    }}
                  >
                    <Text style={styles.actionButtonText}>Aceptar texto</Text>
                  </Pressable>
                </View>
              ) : null}
              {message ? <Text style={styles.error}>{message}</Text> : null}
            </ScrollView>
          </SafeAreaView>
        </Modal>
      </SafeAreaView>
    </Modal>
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

function emptyWeightCertificateForm() {
  return {
    report_number: "",
    continent: "",
    country: "",
    port: "",
    operation: "",
    vessel: "",
    voyage: "",
    commodity: "",
    bl_figure: "",
    cargo_hold: "",
    shipper: "",
    consignee: "",
    terminal: "",
    loading_port: "",
    weight_determination: "",
    date: formatYmd(new Date()),
    quantity: "",
    remarks: ""
  } as Record<string, string>;
}

function weightCertificateFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const vessel = formatValue(row.buque_contenedor);
  const continent = formatValue(row.continente);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const operation = formatValue(row.operacion);
  const detail = formatValue(row.detalle);
  const serviceDate = monthStartFromService(row);

  return {
    report_number: reportNumber === "-" ? "" : reportNumber,
    vessel: vessel === "-" ? "" : vessel,
    continent: continent === "-" ? "" : continent,
    country: country === "-" ? "" : country,
    port: port === "-" ? "" : port,
    operation: operation === "-" ? "" : operation,
    commodity: detail === "-" ? "" : detail,
    loading_port: port === "-" ? "" : port,
    date: serviceDate
  };
}

function emptyHoldsInspectionCertificateForm() {
  return {
    report_number: "",
    port: "",
    country: "",
    vessel: "",
    voyage: "",
    load_port: "",
    place: "",
    installation: "",
    product: "",
    date: formatYmd(new Date()),
    inspection_time: "",
    vessel_holds: "",
    vessel_holds_status: "",
    cargo_holds: "",
    accepted_time: "",
    place_location: "",
    place_date: formatYmd(new Date()),
    hose_test_start: "",
    hose_test_end: "",
    remarks: "",
    master_chief_officer: ""
  } as Record<string, string>;
}

function holdsInspectionCertificateFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const vessel = formatValue(row.buque_contenedor);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const detail = formatValue(row.detalle);
  const serviceDate = monthStartFromService(row);

  return {
    report_number: reportNumber === "-" ? "" : reportNumber,
    port: port === "-" ? "" : port,
    country: country === "-" ? "" : country,
    vessel: vessel === "-" ? "" : vessel,
    load_port: port === "-" ? "" : port,
    place: port === "-" ? "" : port,
    place_location: port === "-" ? "" : port,
    product: detail === "-" ? "" : detail,
    date: serviceDate,
    place_date: serviceDate
  };
}

function emptySamplingCertificateForm() {
  const base = {
    report_no: "",
    port: "",
    country: "",
    customer: "",
    certificate_no: "",
    vessel: "",
    date: formatYmd(new Date()),
    place: "",
    cargo: "",
    holds_inspected: "",
    observations: "",
    closing_date: formatYmd(new Date()),
    closing_time: "",
    master: ""
  } as Record<string, string>;
  for (let index = 1; index <= 10; index += 1) {
    base[`hold_${index}_seal`] = "";
  }
  return base;
}

function samplingCertificateFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const vessel = formatValue(row.buque_contenedor);
  const client = formatValue(row.cliente);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const detail = formatValue(row.detalle);
  const serviceDate = monthStartFromService(row);
  const place = [port, country].filter((item) => item !== "-").join(", ");

  return {
    report_no: reportNumber === "-" ? "" : reportNumber,
    certificate_no: reportNumber === "-" ? "" : reportNumber,
    port: port === "-" ? "" : port,
    country: country === "-" ? "" : country,
    customer: client === "-" ? "" : client,
    vessel: vessel === "-" ? "" : vessel,
    place,
    cargo: detail === "-" ? "" : detail,
    date: serviceDate,
    closing_date: serviceDate
  };
}

function emptySealingCertificateForm() {
  const base = {
    report_no: "",
    port: "",
    country: "",
    customer: "",
    certificate_no: "",
    vessel: "",
    date: formatYmd(new Date()),
    location: "",
    cargo: "",
    remarks: "",
    chief_officer: "",
    closing_date: formatYmd(new Date()),
    closing_time: ""
  } as Record<string, string>;
  for (let index = 1; index <= 6; index += 1) {
    base[`hold_${index}_fwd_escape`] = "";
    base[`hold_${index}_fwd_aft_hatch`] = "";
    base[`hold_${index}_aft_escape`] = "";
  }
  return base;
}

function sealingCertificateFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const vessel = formatValue(row.buque_contenedor);
  const client = formatValue(row.cliente);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const detail = formatValue(row.detalle);
  const serviceDate = monthStartFromService(row);
  const location = [port, country].filter((item) => item !== "-").join(", ");

  return {
    report_no: reportNumber === "-" ? "" : reportNumber,
    certificate_no: reportNumber === "-" ? "" : reportNumber,
    port: port === "-" ? "" : port,
    country: country === "-" ? "" : country,
    customer: client === "-" ? "" : client,
    vessel: vessel === "-" ? "" : vessel,
    location,
    cargo: detail === "-" ? "" : detail,
    date: serviceDate,
    closing_date: serviceDate
  };
}

function emptyLashingCertificateForm() {
  return {
    report_no: "",
    customer: "",
    port: "",
    country: "",
    flat_rack_container: "",
    cargo_type: "",
    lashing_material: "",
    place: "",
    date: formatYmd(new Date()),
    ratchet_quantity: "",
    where_carry_out: "",
    completion_date: formatYmd(new Date()),
    status: "Draft"
  } as Record<string, string>;
}

function lashingCertificateFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const client = formatValue(row.cliente);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const detail = formatValue(row.detalle);
  const container = formatValue(row.buque_contenedor);
  const serviceDate = monthStartFromService(row);
  const place = [port, country].filter((item) => item !== "-").join(", ");

  return {
    report_no: reportNumber === "-" ? "" : reportNumber,
    customer: client === "-" ? "" : client,
    port: port === "-" ? "" : port,
    country: country === "-" ? "" : country,
    flat_rack_container: container === "-" ? "" : container,
    cargo_type: detail === "-" ? "" : detail,
    place,
    where_carry_out: place,
    date: serviceDate,
    completion_date: serviceDate,
    status: "Draft"
  };
}

type BunkerTank = {
  name: string;
  dist_mtrs: string;
  gauge_mtrs: string;
  volume_m3: string;
  temp_c: string;
  temp_f: string;
  density_15c: string;
  weight_mt: string;
};

type BunkerFigure = {
  name: string;
  ifo: string;
  vlsfo: string;
  lsmgo: string;
};

const BUNKER_CERTIFICATE_OPTIONS = ["ON_HIRE", "OFF_HIRE", "SPOT"];
const BUNKER_MAIN_FIELDS: Array<[string, string, ("text" | "date" | "select" | "multiline")?]> = [
  ["bunker_cert_no", "Cert No", "text"],
  ["certificate", "Type", "select"],
  ["ship_name", "Ship Name", "text"],
  ["port_of_registry", "Port of Registry", "text"],
  ["gross_tonnage", "Gross Tonnage", "text"],
  ["report_date", "Report Date", "date"],
  ["client", "Client", "text"],
  ["port", "Port", "text"],
  ["country", "Country", "text"],
  ["report_category", "Report Category", "text"],
  ["antecedent_arrived_port", "Vessel arrived to", "text"],
  ["antecedent_arrived_dt", "Arrival Date", "date"],
  ["antecedent_survey_date_from", "Survey From", "date"],
  ["antecedent_survey_hour_from", "Survey From HH", "text"],
  ["antecedent_survey_minute_from", "Survey From MM", "text"],
  ["antecedent_survey_date_to", "Survey Until", "date"],
  ["antecedent_survey_hour_to", "Survey Until HH", "text"],
  ["antecedent_survey_minute_to", "Survey Until MM", "text"],
  ["inspection_with", "Inspection Joint With", "text"],
  ["remarks", "3- Remark", "multiline"]
];
const BUNKER_DELIVERY_FIELDS: Array<[string, string, ("text" | "date")?]> = [
  ["dslop_port", "DLOSP Port"],
  ["dslop_country", "DLOSP Country"],
  ["dslop_date", "DLOSP Date", "date"],
  ["dslop_hour", "DLOSP HH"],
  ["dslop_minute", "DLOSP MM"],
  ["draft_fwd", "Draft FWD"],
  ["draft_aft", "Draft AFT"],
  ["trim", "TRIM"],
  ["list", "LIST"],
  ["bunker_delivery_declared", "Bunker Delivery Declared"],
  ["rob_diff", "ROB Difference"],
  ["plus_consumption", "Plus Consumption"],
  ["generator_until_aps", "Generator Until APS"],
  ["cons_dept", "Cons. Dept"],
  ["me_to_sea_buoy", "ME to Sea Buoy"]
];
const BUNKER_LOG_EVENTS = [
  ["log_eosp", "E.O.S.P"],
  ["log_pob", "P.O.B"],
  ["log_fwe", "F.W.E"],
  ["log_bunker", "BUNKER ON LOG BOOK FIGURES"],
  ["log_at_survey", "LOG BOOK FIGURES AT SURVEY"]
] as const;
const BUNKER_CONSUMPTION_ROWS = [
  ["cons_sea_loaded", "AT SEA - LOADED"],
  ["cons_sea_ballast", "AT SEA - BALLAST"],
  ["cons_port_ship_gear", "AT PORT - SHIP GEAR IN USE"],
  ["cons_port_shore_gear", "AT PORT - SHORE GEAR IN USE"]
] as const;
const BUNKER_SIGNATURE_FIELDS = [
  ["surveyor_name", "Surveyor Name"],
  ["master_name", "Master Name"],
  ["chief_engineer_name", "C. Engineer"],
  ["owner_name", "Owner"],
  ["charterers_name", "Charterers"]
] as const;

function emptyBunkerForm() {
  return {
    bunker_cert_no: "",
    certificate: "ON_HIRE",
    ship_name: "",
    port_of_registry: "",
    gross_tonnage: "",
    report_date: formatYmd(new Date()),
    client: "",
    port: "",
    country: "",
    report_category: "",
    antecedent_arrived_port: "",
    antecedent_arrived_dt: formatYmd(new Date()),
    antecedent_survey_date_from: formatYmd(new Date()),
    antecedent_survey_hour_from: "08",
    antecedent_survey_minute_from: "00",
    antecedent_survey_date_to: formatYmd(new Date()),
    antecedent_survey_hour_to: "17",
    antecedent_survey_minute_to: "00",
    inspection_with: "",
    remarks: "",
    dslop_port: "",
    dslop_country: "",
    dslop_date: formatYmd(new Date()),
    dslop_hour: "08",
    dslop_minute: "00",
    draft_fwd: "",
    draft_aft: "",
    trim: "",
    list: "",
    bunker_delivery_declared: "",
    rob_diff: "",
    plus_consumption: "",
    generator_until_aps: "",
    cons_dept: "",
    me_to_sea_buoy: "",
    surveyor_name: "",
    master_name: "",
    chief_engineer_name: "",
    owner_name: "",
    charterers_name: "",
    status: "Pending",
    workflow_status: "Pending Review"
  } as Record<string, string>;
}

function emptyBunkerTank(): BunkerTank {
  return { name: "", dist_mtrs: "", gauge_mtrs: "", volume_m3: "", temp_c: "", temp_f: "", density_15c: "", weight_mt: "" };
}

function emptyBunkerFigure(): BunkerFigure {
  return { name: "", ifo: "", vlsfo: "", lsmgo: "" };
}

function bunkerFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const client = formatValue(row.cliente);
  const vessel = formatValue(row.buque_contenedor);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const operation = formatValue(row.operacion);
  const reportDate = monthStartFromService(row);

  return {
    bunker_cert_no: reportNumber === "-" ? "" : reportNumber,
    report_category: operation === "-" ? "" : operation,
    ship_name: vessel === "-" ? "" : vessel,
    client: client === "-" ? "" : client,
    port: port === "-" ? "" : port,
    country: country === "-" ? "" : country,
    report_date: reportDate,
    antecedent_arrived_port: port === "-" ? "" : port,
    antecedent_arrived_dt: reportDate,
    dslop_port: port === "-" ? "" : port,
    dslop_country: country === "-" ? "" : country,
    dslop_date: reportDate
  };
}

function normalizeBunkerPayload(payload: Record<string, unknown>) {
  const base = emptyBunkerForm();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      base[key] = String(value);
    }
  });
  return base;
}

function extractBunkerTanks(payload: Record<string, unknown>, prefix: "vlsfo" | "mgo") {
  const rows: BunkerTank[] = [];
  for (let index = 1; index <= 20; index += 1) {
    const tank = emptyBunkerTank();
    (Object.keys(tank) as Array<keyof BunkerTank>).forEach((key) => {
      const value = formatValue(payload[`${prefix}_tank_${index}_${key}`]);
      tank[key] = value === "-" ? "" : value;
    });
    if (Object.values(tank).some(Boolean)) rows.push(tank);
  }
  return rows;
}

function extractBunkerFigures(payload: Record<string, unknown>) {
  const rows: BunkerFigure[] = [];
  for (let index = 1; index <= 10; index += 1) {
    const figure = emptyBunkerFigure();
    (Object.keys(figure) as Array<keyof BunkerFigure>).forEach((key) => {
      const value = formatValue(payload[`bunker_figure_${index}_${key}`]);
      figure[key] = value === "-" ? "" : value;
    });
    if (Object.values(figure).some(Boolean)) rows.push(figure);
  }
  return rows;
}

type CargoBulletSection = "narrative" | "findings" | "remarks" | "conclusion";

const CARGO_CONDITION_GENERAL_FIELDS: Array<[string, string, ("text" | "date")?]> = [
  ["report_number", "Report Number"],
  ["continent", "Continent"],
  ["operation", "Operation"],
  ["service_start_date", "Service Start Date", "date"],
  ["vessel", "Vessel"],
  ["port", "Port"],
  ["country", "Country"],
  ["requested_by", "Survey Requested By"],
  ["arrival_date", "Date Arrival", "date"],
  ["arrival_hour", "Arrival HH"],
  ["arrival_minute", "Arrival MM"],
  ["inspection_date", "Date/Time Inspection", "date"],
  ["inspection_hour", "Inspection HH"],
  ["inspection_minute", "Inspection MM"],
  ["master", "Master of the Ship"],
  ["chief_officer", "Chief Officer"],
  ["cargo_type", "Cargo Type"]
];

const CARGO_CONDITION_VESSEL_FIELDS = [
  ["vessel_port_registry_flag", "Port of Registry / Flag"],
  ["vessel_grt", "GRT"],
  ["vessel_nrt", "NRT"],
  ["vessel_imo_no", "IMO No"],
  ["vessel_year_build", "Year Build"]
] as const;

const CARGO_CONDITION_TIME_EVENTS = [
  "Vessel Arrived at sea buoy",
  "N.O.R Tendered",
  "Unsealing Inspection",
  "All fast",
  "Free pratique",
  "Surveyor Onboard",
  "Discharging commenced",
  "Discharging completed"
] as const;

const CARGO_BULLET_LABELS: Record<CargoBulletSection, string> = {
  narrative: "Narrative",
  findings: "Survey Findings",
  remarks: "Remarks",
  conclusion: "Conclusion"
};

function emptyCargoConditionForm() {
  const today = formatYmd(new Date());
  return {
    report_number: "",
    continent: "",
    operation: "",
    service_start_date: today,
    vessel: "",
    port: "",
    country: "",
    requested_by: "",
    arrival_date: today,
    arrival_hour: "08",
    arrival_minute: "00",
    inspection_date: today,
    inspection_hour: "08",
    inspection_minute: "00",
    master: "",
    chief_officer: "",
    cargo_type: "",
    vessel_port_registry_flag: "",
    vessel_grt: "",
    vessel_nrt: "",
    vessel_imo_no: "",
    vessel_year_build: "",
    link_picture: "",
    status: "Pending for review"
  } as Record<string, string>;
}

function emptyCargoBullets() {
  return {
    narrative: [""],
    findings: [""],
    remarks: [""],
    conclusion: [""]
  } as Record<CargoBulletSection, string[]>;
}

function cargoConditionFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const client = formatValue(row.cliente);
  const vessel = formatValue(row.buque_contenedor);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const continent = formatValue(row.continente);
  const operation = formatValue(row.operacion);
  const serviceDate = monthStartFromService(row);

  return {
    report_number: reportNumber === "-" ? "" : reportNumber,
    continent: continent === "-" ? "" : continent,
    operation: operation === "-" ? "" : operation,
    service_start_date: serviceDate,
    vessel: vessel === "-" ? "" : vessel,
    port: port === "-" ? "" : port,
    country: country === "-" ? "" : country,
    requested_by: client === "-" ? "" : client,
    arrival_date: serviceDate,
    inspection_date: serviceDate
  };
}

function normalizeCargoConditionPayload(payload: Record<string, unknown>) {
  const base = emptyCargoConditionForm();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      base[key] = String(value);
    }
  });
  return base;
}

function extractCargoBullets(payload: Record<string, unknown>) {
  const result = emptyCargoBullets();
  (Object.keys(CARGO_BULLET_LABELS) as CargoBulletSection[]).forEach((section) => {
    const rows: string[] = [];
    for (let index = 1; index <= 10; index += 1) {
      const value = formatValue(payload[`${section}_${index}`]);
      if (value !== "-") rows.push(value);
    }
    result[section] = rows.length ? rows : [""];
  });
  return result;
}

type VesselConditionBulletSection = "narrative" | "survey_findings" | "remarks" | "conclusion";

const VESSEL_CONDITION_REPORT_TYPES = [
  "Cargo Holds Condition",
  "Hull Condition",
  "Mooring Lines Condition (Mooring Ropes)",
  "P&I Vessel Condition Survey"
];

const VESSEL_CONDITION_GENERAL_FIELDS: Array<[string, string, ("text" | "date" | "select")?]> = [
  ["report_number", "Report Number"],
  ["continent", "Continent"],
  ["country", "Country"],
  ["port", "Port"],
  ["popup_operation", "Operation (popup)"],
  ["service_start_date", "Service Start Date", "date"],
  ["report_type", "Report Type", "select"],
  ["requested_by", "Survey Requested By"],
  ["arrival_date", "Date of Arrival", "date"],
  ["arrival_hour", "Arrival HH"],
  ["arrival_minute", "Arrival MM"],
  ["inspection_date", "Date/Time of Inspection", "date"],
  ["inspection_hour", "Inspection HH"],
  ["inspection_minute", "Inspection MM"],
  ["master_of_ship", "Master of the Ship"],
  ["chief_officer", "Chief Officer"]
];

const VESSEL_CONDITION_VESSEL_FIELDS = [
  ["vessel", "Name"],
  ["port_registry_flag", "Port of Registry / Flag"],
  ["grt", "GRT"],
  ["nrt", "NRT"],
  ["imo_no", "IMO No"],
  ["year_built", "Year Built"]
] as const;

const VESSEL_CONDITION_TIME_EVENTS = [
  ["ts_1", "Vessel Arrived at sea buoy"],
  ["ts_2", "N.O.R Tendered"],
  ["ts_3", "Vessel Berthed"],
  ["ts_4", "Discharge / Charging commenced"],
  ["ts_5", "Surveyor on board"],
  ["ts_6", "Master Meeting"],
  ["ts_7", "Visual Inspection"],
  ["ts_8", "Surveyor off"]
] as const;

const VESSEL_CONDITION_BULLET_LABELS: Record<VesselConditionBulletSection, string> = {
  narrative: "4. Narrative",
  survey_findings: "5. Survey Findings",
  remarks: "6. Remarks",
  conclusion: "7. Conclusion"
};

function emptyVesselConditionForm() {
  const today = formatYmd(new Date());
  const form: Record<string, string> = {
    report_number: "",
    continent: "",
    country: "",
    port: "",
    popup_operation: "",
    service_start_date: today,
    report_type: "P&I Vessel Condition Survey",
    requested_by: "",
    arrival_date: today,
    arrival_hour: "08",
    arrival_minute: "00",
    inspection_date: today,
    inspection_hour: "08",
    inspection_minute: "00",
    master_of_ship: "",
    chief_officer: "",
    vessel: "",
    port_registry_flag: "",
    grt: "",
    nrt: "",
    imo_no: "",
    year_built: "",
    operation: "",
    ts_4_operation: "Discharge",
    link_picture: "",
    status: "Pending for review"
  };

  VESSEL_CONDITION_TIME_EVENTS.forEach(([key]) => {
    form[`${key}_date`] = today;
    form[`${key}_hour`] = "08";
    form[`${key}_minute`] = "00";
  });

  return form;
}

function emptyVesselConditionBullets() {
  return {
    narrative: [""],
    survey_findings: [""],
    remarks: [""],
    conclusion: [""]
  } as Record<VesselConditionBulletSection, string[]>;
}

function vesselConditionFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const client = formatValue(row.cliente);
  const vessel = formatValue(row.buque_contenedor);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const continent = formatValue(row.continente);
  const operation = formatValue(row.operacion);
  const serviceDate = monthStartFromService(row);
  const normalizedOperation = /carga|loading|charge|charging/i.test(operation) ? "Charging" : /descarga|discharge|unloading/i.test(operation) ? "Discharge" : "";

  return {
    report_number: reportNumber === "-" ? "" : reportNumber,
    vessel: vessel === "-" ? "" : vessel,
    requested_by: client === "-" ? "" : client,
    continent: continent === "-" ? "" : continent,
    country: country === "-" ? "" : country,
    port: port === "-" ? "" : port,
    popup_operation: operation === "-" ? "" : operation,
    operation: normalizedOperation,
    ts_4_operation: normalizedOperation || "Discharge",
    service_start_date: serviceDate,
    arrival_date: serviceDate,
    inspection_date: serviceDate,
    ts_1_date: serviceDate,
    ts_2_date: serviceDate,
    ts_3_date: serviceDate,
    ts_4_date: serviceDate,
    ts_5_date: serviceDate,
    ts_6_date: serviceDate,
    ts_7_date: serviceDate,
    ts_8_date: serviceDate
  };
}

function normalizeVesselConditionPayload(payload: Record<string, unknown>) {
  const base = emptyVesselConditionForm();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      base[key] = String(value);
    }
  });
  if (!base.ts_4_operation && base.operation) base.ts_4_operation = base.operation;
  return base;
}

function extractVesselConditionBullets(payload: Record<string, unknown>) {
  const result = emptyVesselConditionBullets();
  (Object.keys(VESSEL_CONDITION_BULLET_LABELS) as VesselConditionBulletSection[]).forEach((section) => {
    const listValue = payload[section];
    const rows = Array.isArray(listValue)
      ? listValue.map((item) => formatValue(item)).filter((item) => item !== "-")
      : [];
    if (!rows.length) {
      for (let index = 1; index <= 20; index += 1) {
        const value = formatValue(payload[`${section}_${index}`]);
        if (value !== "-") rows.push(value);
      }
    }
    result[section] = rows.length ? rows : [""];
  });
  return result;
}

type PortCaptancyBulletSection = "operation_summary" | "remarks" | "conclusion";

const PORT_CAPTANCY_GENERAL_FIELDS: Array<[string, string, ("text" | "date")?]> = [
  ["report_number", "Report Number"],
  ["continent", "Continent"],
  ["country", "Country"],
  ["port", "Port"],
  ["operation", "Operation"],
  ["report_type", "Report Type"],
  ["requested_by", "Survey Requested By"],
  ["arrival_date", "Date of Arrival", "date"],
  ["arrival_hour", "Arrival HH"],
  ["arrival_minute", "Arrival MM"],
  ["inspection_date", "Inspection Date", "date"],
  ["inspection_hour", "Inspection HH"],
  ["inspection_minute", "Inspection MM"],
  ["master", "Master of the Ship"],
  ["chief", "Chief Officer"]
];

const PORT_CAPTANCY_VESSEL_FIELDS = [
  ["vessel", "Name"],
  ["flag", "Port of Registry / Flag"],
  ["grt", "GRT"],
  ["nrt", "NRT"],
  ["imo", "IMO"],
  ["year_built", "Year Built"]
] as const;

const PORT_CAPTANCY_TIME_EVENTS = [
  "Vessel Arrive",
  "NOR Tendered",
  "ALL Fast",
  "Supervision commenced",
  "Supervision completed"
] as const;

const PORT_CAPTANCY_BULLET_LABELS: Record<PortCaptancyBulletSection, string> = {
  operation_summary: "4. Operation Summary",
  remarks: "5. Remarks",
  conclusion: "6. Conclusion"
};

function emptyPortCaptancyForm() {
  const today = formatYmd(new Date());
  const form: Record<string, string> = {
    report_number: "",
    continent: "",
    country: "",
    port: "",
    operation: "",
    report_type: "Port Captancy",
    vessel: "",
    requested_by: "",
    arrival_date: today,
    arrival_hour: "08",
    arrival_minute: "00",
    inspection_date: today,
    inspection_hour: "08",
    inspection_minute: "00",
    master: "",
    chief: "",
    flag: "",
    grt: "",
    nrt: "",
    imo: "",
    year_built: "",
    link_picture: "",
    status: "Pending for review"
  };

  PORT_CAPTANCY_TIME_EVENTS.forEach((_, index) => {
    form[`ts_date_${index}`] = today;
    form[`ts_hour_${index}`] = "08";
    form[`ts_min_${index}`] = "00";
  });

  return form;
}

function emptyPortCaptancyBullets() {
  return {
    operation_summary: [""],
    remarks: [""],
    conclusion: [""]
  } as Record<PortCaptancyBulletSection, string[]>;
}

function portCaptancyFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const client = formatValue(row.cliente);
  const vessel = formatValue(row.buque_contenedor);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const continent = formatValue(row.continente);
  const operation = formatValue(row.operacion);
  const serviceDate = monthStartFromService(row);

  const values: Record<string, string> = {
    report_number: reportNumber === "-" ? "" : reportNumber,
    vessel: vessel === "-" ? "" : vessel,
    requested_by: client === "-" ? "" : client,
    continent: continent === "-" ? "" : continent,
    country: country === "-" ? "" : country,
    port: port === "-" ? "" : port,
    operation: operation === "-" ? "" : operation,
    arrival_date: serviceDate,
    inspection_date: serviceDate
  };
  PORT_CAPTANCY_TIME_EVENTS.forEach((_, index) => {
    values[`ts_date_${index}`] = serviceDate;
  });
  return values;
}

function normalizePortCaptancyPayload(payload: Record<string, unknown>) {
  const base = emptyPortCaptancyForm();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      base[key] = String(value);
    }
  });
  return base;
}

function extractPortCaptancyBullets(payload: Record<string, unknown>) {
  const result = emptyPortCaptancyBullets();
  (Object.keys(PORT_CAPTANCY_BULLET_LABELS) as PortCaptancyBulletSection[]).forEach((section) => {
    const rows: string[] = [];
    for (let index = 1; index <= 15; index += 1) {
      const value = formatValue(payload[`${section}_${index}`]);
      if (value !== "-") rows.push(value);
    }
    result[section] = rows.length ? rows : [""];
  });
  return result;
}

const CRANE_STATUS_OPTIONS = [
  "",
  "Clean and no obstacles",
  "Clean",
  "Working",
  "Not working",
  "Greased",
  "Negative impressions",
  "Free to rotate / Unreadable scale",
  "No trunnion"
];

const CRANE_CHECKLIST = [
  ["crane_access", "1. Crane Access"],
  ["crane_machinery_space", "2. Crane machinery space"],
  ["crane_operator_cabin", "3. Crane operator cabin"],
  ["crane_jib_head_sheaves", "4. Crane jib head sheaves"],
  ["hoisting_wire_end_pin", "5. Hoisting wire end pin"],
  ["luffing_wire_end_pin", "6. Luffing wire end pin"],
  ["crane_wire_visual", "7. Crane wire rope visual inspection"],
  ["crane_housing_sheaves", "8. Crane housing top sheaves"],
  ["luffing_center_sheave", "9. Luffing center sheave visual inspection"],
  ["cargo_block_sheave", "10. Cargo block sheave shaft"],
  ["slack_hoisting_limit", "11. Slack hoisting wire limit"],
  ["crane_jib_angle_limits", "12. Crane jib angle limits"],
  ["crane_jib_angle_indicator", "13. Crane jib angle indicator"],
  ["crane_hoisting_limits", "14. Crane hoisting wire limits (upper/slack)"],
  ["pedestal_light_project", "15. Pedestal / Light project"]
] as const;

const CRANE_GENERAL_FIELDS: Array<[string, string, ("text" | "date")?]> = [
  ["report_number", "Report Number"],
  ["vessel", "Vessel Name"],
  ["grt", "GRT"],
  ["nrt", "NRT"],
  ["client", "Client"],
  ["port", "Port"],
  ["country", "Country"],
  ["report_date", "Report Date", "date"]
];

const CRANE_TIME_FIELDS: Array<[string, string]> = [
  ["intro_inspection", "Inspection Date"],
  ["gear_start", "Survey Start"],
  ["gear_end", "Survey End"]
];

type CraneBulletSection = "recommendations" | "grabs_condition" | "conclusion";
type CraneRemarks = Record<"1" | "2" | "3" | "4", string[]>;

const CRANE_BULLET_LABELS: Record<CraneBulletSection, string> = {
  recommendations: "Recommendations",
  grabs_condition: "GRABS CONDITION SURVEY",
  conclusion: "CONCLUSION"
};

function emptyCraneInspectionForm() {
  const today = formatYmd(new Date());
  const form: Record<string, string> = {
    report_number: "",
    vessel: "",
    grt: "",
    nrt: "",
    client: "",
    port: "",
    country: "",
    report_date: today,
    intro_text: "",
    intro_inspection_date: today,
    intro_inspection_hour: "08",
    intro_inspection_minute: "00",
    gear_start_date: today,
    gear_start_hour: "08",
    gear_start_minute: "00",
    gear_end_date: today,
    gear_end_hour: "17",
    gear_end_minute: "00",
    gear_condition: "",
    gear_wires: "",
    gear_sheaves: "",
    gear_operability: "",
    link_picture: "",
    status: "Pending for review"
  };

  CRANE_CHECKLIST.forEach(([prefix]) => {
    form[`${prefix}_done`] = "false";
    form[`${prefix}_status`] = "";
    form[`${prefix}_status1`] = "";
    form[`${prefix}_status2`] = "";
    form[`${prefix}_status3`] = "";
  });

  return form;
}

function emptyCraneRemarks(): CraneRemarks {
  return { "1": [""], "2": [""], "3": [""], "4": [""] };
}

function emptyCraneBullets() {
  return {
    recommendations: [""],
    grabs_condition: [""],
    conclusion: [""]
  } as Record<CraneBulletSection, string[]>;
}

function craneInspectionFormFromServiceReport(row: Record<string, unknown>) {
  const reportNumber = formatValue(row.num_informe);
  const vessel = formatValue(row.buque_contenedor);
  const client = formatValue(row.cliente);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const serviceDate = monthStartFromService(row);

  return {
    report_number: reportNumber === "-" ? "" : reportNumber,
    vessel: vessel === "-" ? "" : vessel,
    client: client === "-" ? "" : client,
    port: port === "-" ? "" : port,
    country: country === "-" ? "" : country,
    report_date: serviceDate,
    intro_inspection_date: serviceDate,
    gear_start_date: serviceDate,
    gear_end_date: serviceDate
  };
}

function normalizeCraneInspectionPayload(payload: Record<string, unknown>) {
  const base = emptyCraneInspectionForm();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === null || value === undefined) return;
    if (typeof value === "boolean") base[key] = value ? "true" : "false";
    else if (typeof value === "string" || typeof value === "number") base[key] = String(value);
  });
  return base;
}

function extractCraneRemarks(payload: Record<string, unknown>) {
  const result = emptyCraneRemarks();
  (["1", "2", "3", "4"] as const).forEach((crane) => {
    const rows: string[] = [];
    for (let index = 1; index <= 10; index += 1) {
      const value = formatValue(payload[`crane${crane}_remark_${index}`]);
      if (value !== "-") rows.push(value);
    }
    result[crane] = rows.length ? rows : [""];
  });
  return result;
}

function extractCraneBullets(payload: Record<string, unknown>) {
  const result = emptyCraneBullets();
  (Object.keys(CRANE_BULLET_LABELS) as CraneBulletSection[]).forEach((section) => {
    const rows: string[] = [];
    const max = section === "conclusion" ? 20 : 10;
    const prefix = section === "recommendations" ? "recommendation" : section;
    for (let index = 1; index <= max; index += 1) {
      const value = formatValue(payload[`${prefix}_${index}`]);
      if (value !== "-") rows.push(value);
    }
    result[section] = rows.length ? rows : [""];
  });
  return result;
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

const DRAFT_GENERAL_FIELDS = [
  ["vessel_mv", "Vessel MV"], ["survey_no", "Survey no"], ["call_letters", "Call letters"], ["vessel_previous_names", "Vessel previous name/s"],
  ["flag", "Flag"], ["registry", "Registry"], ["built_year", "Built year"], ["by", "By"],
  ["master", "Master"], ["initial_surveyors", "Initial Surveyor/s"], ["chief_officer", "Chief Officer"], ["final_surveyors", "Final Surveyor/s"],
  ["chief_engineer", "Chief Engineer"], ["survey_requested_by", "Survey requested by"], ["witness_draughts", "Witness draughts"], ["on_account_of", "On the account of"],
  ["witness_sounding", "Witness sounding"], ["attended_also_by", "Attended also by"], ["init_ships_location", "Init Ship's location"], ["final_ships_location", "Final Ship's location"],
  ["length_overall", "Length overall"], ["length_between_pp", "Length between p.p."], ["extreme_breadth", "Extreme breadth"], ["moulded_breadth", "Moulded breadth"],
  ["depth_overall_incl_keel_plate", "Depth overall incl. keel plate"], ["moulded_depth", "Moulded depth"], ["summer_draught", "Summer draught"], ["summer_freeboard", "Summer freeboard"],
  ["constant_declared", "Constant declared"], ["constant_calculated", "Constant calculated"], ["light_displacement", "Light displacement"], ["light_shipweight_plan", "Light shipweight (plan)"],
  ["summer_displacement", "Summer displacement"], ["summer_deadweight", "Summer deadweight"], ["net_register_tons", "Net register tons"], ["gross_register_tons", "Gross register tons"],
  ["hydro_tables_issued", "Hydrostatic tables issued by and dated"], ["hydrometer_no", "Hydrometer no"]
] as const;

const DRAFT_TOP_FIELDS = [
  ["cargo", "Cargo"], ["port_from", "From"], ["port_to", "To"],
  ["init_date", "Initial Date", "date"], ["init_time_from", "Initial From"], ["init_time_to", "Initial To"],
  ["final_date", "Final Date", "date"], ["final_time_from", "Final From"], ["final_time_to", "Final To"]
] as const;

const DRAFT_SIDE_FIELDS = [
  ["draft_fwd_port", "FWD Port"], ["draft_fwd_stb", "FWD STB"], ["draft_fwd_marks", "FWD Marks"],
  ["draft_mid_port", "MID Port"], ["draft_mid_stb", "MID STB"], ["draft_mid_marks", "MID Marks"],
  ["draft_aft_port", "AFT Port"], ["draft_aft_stb", "AFT STB"], ["draft_aft_marks", "AFT Marks"],
  ["sg", "S.G"], ["lpp", "LPP"], ["tpc_p", "TPC - P"], ["tpc_s", "TPC - S"],
  ["ballast", "Ballast"], ["fresh_water", "F. Water"], ["fuel_oil", "Fuel Oil"], ["diesel_oil", "Diesel Oil"],
  ["lub_oil", "Lub Oil"], ["slop", "Slop"], ["swimming_pool", "Swimming Pool"], ["others", "Others"], ["bl_figure", "B/L Figure"]
] as const;

const DRAFT_HYDRO_FIELDS = [
  "hydro1_draft_1", "hydro1_disp_1", "hydro1_tpc_1", "hydro1_lcf_1",
  "hydro1_draft_2", "hydro1_disp_2", "hydro1_tpc_2", "hydro1_lcf_2",
  "hydro1_draft_mtc", "hydro1_mtc_p50_1", "hydro1_mtc_m50_1", "hydro1_mtc_p50_2", "hydro1_mtc_m50_2",
  "hydro2_draft_1", "hydro2_disp_1", "hydro2_tpc_1", "hydro2_lcf_1",
  "hydro2_draft_2", "hydro2_disp_2", "hydro2_tpc_2", "hydro2_lcf_2",
  "hydro2_draft_mtc", "hydro2_mtc_p50_1", "hydro2_mtc_m50_1", "hydro2_mtc_p50_2", "hydro2_mtc_m50_2"
];

const DRAFT_WORD_FIELDS = [
  ["word_mt", "Metric Tons (MT)"], ["word_product", "Product"], ["word_vessel", "Vessel"], ["word_port", "Port"], ["word_country", "Country"],
  ["word_survey_requested_by", "Survey requested by"], ["word_on_behalf_of", "On behalf of"], ["word_master", "Master of the ship"], ["word_chief_officer", "Chief Officer"],
  ["word_name", "Name"], ["word_port_registry", "Port of Registry / Flag"], ["word_grt", "GRT"], ["word_nrt", "NRT"], ["word_year", "Year Built"], ["word_imo", "IMO Number"],
  ["word_metric_tons", "Metric Tons"], ["word_goods_product", "Product"], ["word_holds", "Holds"], ["word_draft_figures", "Draft Survey Figures"],
  ["word_bl_figures", "B/L Figures"], ["word_difference", "Difference"], ["word_percentage", "Percentage (%)"],
  ["word_shore_scale", "Shore Scale Figures"], ["word_shore_bl", "B/L Figures"], ["word_shore_difference", "Difference"], ["word_shore_percentage", "Percentage (%)"]
] as const;

const DRAFT_WORD_DATETIME_FIELDS = [
  ["word_arrived_buoy", "Vessel Arrived at Sea Buoy"], ["word_nor_tendered", "N.O.R Tendered"], ["word_all_fast", "All Fast"],
  ["word_initial_draft", "Initial Draft Survey"], ["word_commenced", "Commenced Discharge"], ["word_completed", "Completed Discharge"], ["word_final_draft", "Final Draft Survey"]
] as const;

type DraftTank = { tank_name: string; height?: string; sounding: string; volume: string; density: string };

function emptyDraftForm() {
  const form: Record<string, string> = {
    year: "",
    month: "",
    continent: "",
    country: "",
    port: "",
    client: "",
    draft_report_number: "",
    loading: "true",
    unloading: "false",
    trim_tables_available: "true"
  };
  [...DRAFT_GENERAL_FIELDS, ...DRAFT_TOP_FIELDS, ...DRAFT_WORD_FIELDS].forEach(([key]) => { form[key] = ""; });
  for (const prefix of ["init", "final"]) {
    DRAFT_SIDE_FIELDS.forEach(([suffix]) => { form[`${prefix}_${suffix}`] = ""; });
  }
  DRAFT_HYDRO_FIELDS.forEach((suffix) => { form[`init_${suffix}`] = ""; });
  DRAFT_WORD_DATETIME_FIELDS.forEach(([key]) => {
    form[`${key}_date`] = formatYmd(new Date());
    form[`${key}_time`] = "00:00";
  });
  return form;
}

function normalizeDraftPayload(payload: Record<string, unknown>) {
  const data = asRecord(payload.data) || payload;
  const next = emptyDraftForm();
  Object.entries(data).forEach(([key, value]) => {
    if (value === null || value === undefined || typeof value === "object") return;
    next[key] = String(value);
  });
  return next;
}

function draftServiceFormFromRow(row: Record<string, unknown>) {
  const date = monthStartFromService(row);
  const report = formatValue(row.num_informe);
  const vessel = formatValue(row.buque_contenedor);
  const client = formatValue(row.cliente);
  const continent = formatValue(row.continente);
  const country = formatValue(row.pais);
  const port = formatValue(row.puerto);
  const operation = formatValue(row.operacion);
  const parsed = parseYmd(date);

  return {
    draft_report_number: report === "-" ? "" : report,
    survey_no: report === "-" ? "" : report,
    vessel_mv: vessel === "-" ? "" : vessel,
    word_vessel: vessel === "-" ? "" : vessel,
    word_name: vessel === "-" ? "" : vessel,
    client: client === "-" ? "" : client,
    survey_requested_by: client === "-" ? "" : client,
    word_survey_requested_by: client === "-" ? "" : client,
    continent: continent === "-" ? "" : continent,
    country: country === "-" ? "" : country,
    word_country: country === "-" ? "" : country,
    port: port === "-" ? "" : port,
    word_port: port === "-" ? "" : port,
    cargo: operation === "-" ? "" : operation,
    word_product: operation === "-" ? "" : operation,
    word_goods_product: operation === "-" ? "" : operation,
    year: parsed ? String(parsed.getFullYear()) : "",
    month: parsed ? String(parsed.getMonth() + 1) : "",
    init_date: date,
    final_date: date
  };
}

function extractDraftTanks(data: Record<string, unknown>, prefix: "init" | "final", freshwater = false): DraftTank[] {
  const raw = asRecord(data[freshwater ? "fresh_water" : "ballast"]);
  const direct = raw?.[prefix];
  if (Array.isArray(direct)) return direct.map((item) => asRecord(item)).filter(Boolean).map((item) => ({
    tank_name: formatValue(item?.tank_name) === "-" ? "" : formatValue(item?.tank_name),
    height: formatValue(item?.height) === "-" ? "" : formatValue(item?.height),
    sounding: formatValue(item?.sounding) === "-" ? "" : formatValue(item?.sounding),
    volume: formatValue(item?.volume) === "-" ? "" : formatValue(item?.volume),
    density: formatValue(item?.density) === "-" ? "" : formatValue(item?.density)
  }));

  const tanks: DraftTank[] = [];
  if (freshwater) {
    for (let index = 1; index <= 20; index += 1) {
      const base = `${prefix}_fw_${index}`;
      const name = data[`${base}_name`];
      const volume = data[`${base}_volume`];
      if (name || volume) tanks.push({
        tank_name: formatValue(name) === "-" ? "" : formatValue(name),
        height: formatValue(data[`${base}_height`]) === "-" ? "" : formatValue(data[`${base}_height`]),
        sounding: formatValue(data[`${base}_sounding`]) === "-" ? "" : formatValue(data[`${base}_sounding`]),
        volume: formatValue(volume) === "-" ? "" : formatValue(volume),
        density: formatValue(data[`${base}_density`]) === "-" ? "" : formatValue(data[`${base}_density`])
      });
    }
    return tanks;
  }

  for (const tank of ["fpt", "apt", "slop_tank"]) {
    const base = `${prefix}_${tank}`;
    const name = data[`${base}_name`];
    const volume = data[`${base}_volume`];
    if (name || volume) tanks.push({
      tank_name: formatValue(name) === "-" ? tank.toUpperCase().replace("_", " ") : formatValue(name),
      sounding: formatValue(data[`${base}_sounding`]) === "-" ? "" : formatValue(data[`${base}_sounding`]),
      volume: formatValue(volume) === "-" ? "" : formatValue(volume),
      density: formatValue(data[`${base}_density`]) === "-" ? "" : formatValue(data[`${base}_density`])
    });
  }
  for (let index = 1; index <= 20; index += 1) {
    for (const side of ["p", "s"]) {
      const base = `${prefix}_wbt_${index}${side}`;
      const name = data[`${base}_name`];
      const volume = data[`${base}_volume`];
      if (name || volume) tanks.push({
        tank_name: formatValue(name) === "-" ? `WBT ${index}${side.toUpperCase()}` : formatValue(name),
        sounding: formatValue(data[`${base}_sounding`]) === "-" ? "" : formatValue(data[`${base}_sounding`]),
        volume: formatValue(volume) === "-" ? "" : formatValue(volume),
        density: formatValue(data[`${base}_density`]) === "-" ? "" : formatValue(data[`${base}_density`])
      });
    }
  }
  return tanks;
}

function CraneInspectionMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>(emptyCraneInspectionForm());
  const [remarks, setRemarks] = useState<CraneRemarks>(emptyCraneRemarks());
  const [bullets, setBullets] = useState<Record<CraneBulletSection, string[]>>(emptyCraneBullets());
  const [tab, setTab] = useState<"header" | "gear" | "checklist" | "remarks" | "final">("header");
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editing, setEditing] = useState(true);
  const [aiLanguage, setAiLanguage] = useState("EN");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const readonly = Boolean(initialReportId) && !editing;

  useEffect(() => {
    if (!visible) return;
    setForm(emptyCraneInspectionForm());
    setRemarks(emptyCraneRemarks());
    setBullets(emptyCraneBullets());
    setTab("header");
    setEditing(!initialReportId);
    setAiLanguage("EN");
    setMessage("");
    if (initialReportId) loadExisting(initialReportId);
  }, [visible, initialReportId]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function loadExisting(reportId: string) {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/vessel-crane-inspection/${encodeURIComponent(reportId)}`, { session });
      const data = unwrapRecordPayload(payload) || payload;
      setForm(normalizeCraneInspectionPayload(data));
      setRemarks(extractCraneRemarks(data));
      setBullets(extractCraneBullets(data));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar Crane Inspection.");
    } finally {
      setBusy(false);
    }
  }

  function buildPayload() {
    const payload: Record<string, unknown> = { ...form };

    CRANE_CHECKLIST.forEach(([prefix]) => {
      payload[`${prefix}_done`] = form[`${prefix}_done`] === "true";
      payload[`${prefix}_status`] = form[`${prefix}_status`] || null;
      payload[`${prefix}_status1`] = form[`${prefix}_status1`] || null;
      payload[`${prefix}_status2`] = form[`${prefix}_status2`] || null;
      payload[`${prefix}_status3`] = form[`${prefix}_status3`] || null;
    });

    (["1", "2", "3", "4"] as const).forEach((crane) => {
      for (let index = 1; index <= 10; index += 1) {
        payload[`crane${crane}_remark_${index}`] = (remarks[crane][index - 1] || "").trim() || null;
      }
    });

    (Object.keys(CRANE_BULLET_LABELS) as CraneBulletSection[]).forEach((section) => {
      const max = section === "conclusion" ? 20 : 10;
      const prefix = section === "recommendations" ? "recommendation" : section;
      for (let index = 1; index <= max; index += 1) {
        payload[`${prefix}_${index}`] = (bullets[section][index - 1] || "").trim() || null;
      }
    });

    payload.status = payload.status || "Pending for review";
    return payload;
  }

  async function save() {
    if (!form.report_number || !form.vessel || !form.client || !form.port || !form.country) {
      setMessage("Debe completar Report Number, buque, cliente, puerto y pais.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      if (initialReportId) {
        const result = await offlineApiRequest(`/vessel-crane-inspection/${encodeURIComponent(initialReportId)}`, {
          method: "PUT",
          session,
          body: buildPayload(),
          offlineLabel: `Actualizar Crane Inspection ${initialReportId}`
        });
        setEditing(isQueuedOffline(result) ? editing : false);
        setMessage(isQueuedOffline(result) ? "Sin internet: Crane Inspection guardado en cache local." : "Crane Inspection actualizado correctamente.");
      } else {
        const result = await offlineApiRequest("/vessel-crane-inspection", {
          method: "POST",
          session,
          body: { ...buildPayload(), status: "Pending for review" },
          offlineLabel: `Crear Crane Inspection ${form.report_number || form.vessel}`
        });
        setMessage(isQueuedOffline(result) ? "Sin internet: Crane Inspection guardado en cache local." : "Crane Inspection enviado a revision.");
      }
      onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Crane Inspection.");
    } finally {
      setBusy(false);
    }
  }

  async function improveItems(section: string, items: string[], apply: (nextItems: string[]) => void) {
    const cleanItems = items.map((item) => item.trim()).filter(Boolean);
    if (!cleanItems.length) {
      setMessage("La seccion seleccionada no tiene texto para mejorar.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await apiRequest<Record<string, unknown>>("/reports/ai/improve/crane-inspection", {
        method: "POST",
        session,
        body: {
          section,
          language: aiLanguage,
          vessel: form.vessel,
          port: form.port,
          items: cleanItems
        }
      });
      const nextItems = Array.isArray(response.items) ? response.items.map((item) => formatValue(item)).filter((item) => item !== "-") : [];
      if (!nextItems.length) throw new Error("PORTIA no devolvio texto valido.");
      apply(nextItems);
      setMessage(`PORTIA mejoro ${section}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo mejorar la seccion.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadFile(kind: "word" | "presentation") {
    const id = initialReportId || form.id;
    if (!id) {
      setMessage("Primero debe guardar o abrir el informe desde Review.");
      return;
    }
    const endpoint = kind === "word"
      ? `/vessel-crane-inspection-reports/${encodeURIComponent(id)}/generate-word`
      : `/vessel-crane-inspection-reports/${encodeURIComponent(id)}/presentation`;
    const extension = kind === "word" ? "docx" : "pdf";
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(endpoint, session, cleanFilePart(`Crane_Inspection_${kind}_${id}`) + `.${extension}`);
      setMessage(`${kind === "word" ? "Word" : "Presentacion"} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo generar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" | "multiline" = "text") {
    if (type === "date") return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={!readonly}
          style={[styles.input, type === "multiline" && styles.multilineInput, readonly && styles.readonlyInput]}
          multiline={type === "multiline"}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  function renderTime(prefix: string, label: string) {
    return (
      <View key={prefix} style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{label}</Text>
        {renderField(`${prefix}_date`, "Date", "date")}
        {renderField(`${prefix}_hour`, "HH")}
        {renderField(`${prefix}_minute`, "MM")}
      </View>
    );
  }

  function renderChecklist() {
    return CRANE_CHECKLIST.map(([prefix, label]) => (
      <View key={prefix} style={styles.summaryBox}>
        <View style={styles.rememberRow}>
          <Text style={styles.rememberText}>{label}</Text>
          <Switch
            disabled={readonly}
            value={form[`${prefix}_done`] === "true"}
            onValueChange={(value) => setValue(`${prefix}_done`, value ? "true" : "false")}
            trackColor={{ true: BLUE }}
          />
        </View>
        <SelectField label="Estado" value={form[`${prefix}_status`] || ""} options={CRANE_STATUS_OPTIONS} onChange={(value) => setValue(`${prefix}_status`, value)} />
        <SelectField label="Comentario 1" value={form[`${prefix}_status1`] || ""} options={CRANE_STATUS_OPTIONS} onChange={(value) => setValue(`${prefix}_status1`, value)} />
        <SelectField label="Comentario 2" value={form[`${prefix}_status2`] || ""} options={CRANE_STATUS_OPTIONS} onChange={(value) => setValue(`${prefix}_status2`, value)} />
        <SelectField label="Comentario 3" value={form[`${prefix}_status3`] || ""} options={CRANE_STATUS_OPTIONS} onChange={(value) => setValue(`${prefix}_status3`, value)} />
      </View>
    ));
  }

  function renderRemarkCrane(crane: "1" | "2" | "3" | "4") {
    const rows = remarks[crane];
    return (
      <View style={styles.summaryBox}>
        <Text style={styles.cardTitle}>Crane {crane}</Text>
        {rows.map((value, index) => (
          <View key={`crane-${crane}-${index}`} style={styles.formField}>
            <Text style={styles.label}>Remark {index + 1}</Text>
            <TextInput
              editable={!readonly}
              style={[styles.input, styles.multilineInput, readonly && styles.readonlyInput]}
              multiline
              value={value}
              onChangeText={(text) => setRemarks((current) => ({ ...current, [crane]: rows.map((item, rowIndex) => rowIndex === index ? text : item) }))}
            />
            <Pressable style={styles.modalClose} onPress={() => setRemarks((current) => ({ ...current, [crane]: rows.length <= 1 ? [""] : rows.filter((_, rowIndex) => rowIndex !== index) }))}>
              <Text style={styles.modalCloseText}>Remove</Text>
            </Pressable>
          </View>
        ))}
        <Pressable style={styles.secondaryButton} onPress={() => rows.length < 10 && setRemarks((current) => ({ ...current, [crane]: [...rows, ""] }))}>
          <Text style={styles.secondaryButtonText}>+ Add Remark</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => improveItems(`Crane ${crane} remarks`, rows, (next) => setRemarks((current) => ({ ...current, [crane]: next })))}>
          <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
        </Pressable>
      </View>
    );
  }

  function renderBulletSection(section: CraneBulletSection) {
    const rows = bullets[section];
    const max = section === "conclusion" ? 20 : 10;
    return (
      <View style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{CRANE_BULLET_LABELS[section]}</Text>
        {rows.map((value, index) => (
          <View key={`${section}-${index}`} style={styles.formField}>
            <Text style={styles.label}>Bullet {index + 1}</Text>
            <TextInput
              editable={!readonly}
              style={[styles.input, styles.multilineInput, readonly && styles.readonlyInput]}
              multiline
              value={value}
              onChangeText={(text) => setBullets((current) => ({ ...current, [section]: rows.map((item, rowIndex) => rowIndex === index ? text : item) }))}
            />
            <Pressable style={styles.modalClose} onPress={() => setBullets((current) => ({ ...current, [section]: rows.length <= 1 ? [""] : rows.filter((_, rowIndex) => rowIndex !== index) }))}>
              <Text style={styles.modalCloseText}>Remove</Text>
            </Pressable>
          </View>
        ))}
        <Pressable style={styles.secondaryButton} onPress={() => rows.length < max && setBullets((current) => ({ ...current, [section]: [...rows, ""] }))}>
          <Text style={styles.secondaryButtonText}>+ Add Bullet</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => improveItems(CRANE_BULLET_LABELS[section], rows, (next) => setBullets((current) => ({ ...current, [section]: next })))}>
          <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
        </Pressable>
      </View>
    );
  }

  const tabs = [
    ["header", "Header"],
    ["gear", "Gear Survey"],
    ["checklist", "Checklist"],
    ["remarks", "Remarks"],
    ["final", "Final"]
  ] as const;

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>CRANE INSPECTION SURVEY</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <View style={styles.financeFilterBox}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            <Pressable style={styles.secondaryButton} onPress={() => setServiceSelectorOpen(true)}><Text style={styles.secondaryButtonText}>Seleccionar Reporte</Text></Pressable>
            {initialReportId ? <Pressable style={styles.secondaryButton} onPress={() => setEditing((value) => !value)}><Text style={styles.secondaryButtonText}>{editing ? "Bloquear" : "Editar"}</Text></Pressable> : null}
            <Pressable style={styles.actionButton} onPress={save}><Text style={styles.actionButtonText}>{initialReportId ? "Guardar Cambios" : "Enviar a revision"}</Text></Pressable>
          </ScrollView>
          <View style={styles.summaryBox}>
            <Text style={styles.fieldKey}>Crane Inspection</Text>
            <Text style={styles.fieldValue}>{[form.report_number, form.vessel, form.client, form.port, form.country].filter(Boolean).join(" | ") || "Sin servicio seleccionado"}</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            {tabs.map(([key, label]) => (
              <Pressable key={key} style={tab === key ? styles.actionButton : styles.modalClose} onPress={() => setTab(key)}>
                <Text style={tab === key ? styles.actionButtonText : styles.modalCloseText}>{label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          {tab === "header" ? (
            <>
              {CRANE_GENERAL_FIELDS.map(([key, label, type]) => renderField(key, label, type))}
              {CRANE_TIME_FIELDS.slice(0, 1).map(([prefix, label]) => renderTime(prefix, label))}
              {renderField("intro_text", "Introduction Text", "multiline")}
              <Pressable
                style={styles.secondaryButton}
                onPress={() => {
                  const text = `On ${form.intro_inspection_date || "[DATE]"}, we were appointed to carry out a crane inspection survey in MV ${form.vessel || "[VESSEL]"} at ${form.port || "[PORT]"}, ${form.country || "[COUNTRY]"}.`;
                  setValue("intro_text", text);
                }}
              >
                <Text style={styles.secondaryButtonText}>Auto-fill Introduction</Text>
              </Pressable>
              <Pressable style={styles.secondaryButton} onPress={() => improveItems("Introduction", [form.intro_text], (next) => setValue("intro_text", next[0] || ""))}>
                <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
              </Pressable>
            </>
          ) : null}
          {tab === "gear" ? (
            <>
              {CRANE_TIME_FIELDS.slice(1).map(([prefix, label]) => renderTime(prefix, label))}
              {renderField("gear_condition", "2. Condition (shortcomings / notes)", "multiline")}
              {renderField("gear_wires", "3. Hoisting & Luffing Wires (found as)", "multiline")}
              {renderField("gear_sheaves", "4. Hoisting & Luffing Sheaves (impressions)", "multiline")}
              {renderField("gear_operability", "5. Operability Inspection (notes)", "multiline")}
              {["gear_condition", "gear_wires", "gear_sheaves", "gear_operability"].map((key) => (
                <Pressable key={key} style={styles.secondaryButton} onPress={() => improveItems(key.replaceAll("_", " "), [form[key]], (next) => setValue(key, next[0] || ""))}>
                  <Text style={styles.secondaryButtonText}>Mejorar {key.replaceAll("_", " ")} con PORTIA</Text>
                </Pressable>
              ))}
            </>
          ) : null}
          {tab === "checklist" ? renderChecklist() : null}
          {tab === "remarks" ? (
            <>
              <SelectField label="PORTIA Language" value={aiLanguage} options={["EN", "ES"]} onChange={setAiLanguage} />
              {(["1", "2", "3", "4"] as const).map((crane) => renderRemarkCrane(crane))}
              {(Object.keys(CRANE_BULLET_LABELS) as CraneBulletSection[]).map((section) => renderBulletSection(section))}
            </>
          ) : null}
          {tab === "final" ? (
            <View style={styles.summaryBox}>
              <Text style={styles.cardTitle}>Enclosure / Final Report</Text>
              {renderField("link_picture", "Link Picture")}
              <Pressable style={styles.secondaryButton} onPress={() => downloadFile("word")}><Text style={styles.secondaryButtonText}>Generar Word</Text></Pressable>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFile("presentation")}><Text style={styles.secondaryButtonText}>Generar Presentacion PDF</Text></Pressable>
            </View>
          ) : null}
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={message.includes("correctamente") || message.includes("revision") || message.includes("PORTIA mejoro") ? styles.helperText : styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(row) => {
            setForm((current) => ({ ...current, ...craneInspectionFormFromServiceReport(row) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function CargoConditionMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>(emptyCargoConditionForm());
  const [bullets, setBullets] = useState<Record<CargoBulletSection, string[]>>(emptyCargoBullets());
  const [tab, setTab] = useState<"general" | "vessel" | "times" | "text" | "final">("general");
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editing, setEditing] = useState(true);
  const [aiLanguage, setAiLanguage] = useState("EN");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const readonly = Boolean(initialReportId) && !editing;

  useEffect(() => {
    if (!visible) return;
    setForm(emptyCargoConditionForm());
    setBullets(emptyCargoBullets());
    setTab("general");
    setEditing(!initialReportId);
    setAiLanguage("EN");
    setMessage("");
    if (initialReportId) loadExisting(initialReportId);
  }, [visible, initialReportId]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function loadExisting(reportId: string) {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/vessel-cargo-condition-surveys/${encodeURIComponent(reportId)}`, { session });
      const data = unwrapRecordPayload(payload) || payload;
      setForm(normalizeCargoConditionPayload(data));
      setBullets(extractCargoBullets(data));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar Cargo Condition.");
    } finally {
      setBusy(false);
    }
  }

  function buildPayload() {
    const payload: Record<string, unknown> = { ...form };
    (Object.keys(CARGO_BULLET_LABELS) as CargoBulletSection[]).forEach((section) => {
      for (let index = 1; index <= 10; index += 1) {
        payload[`${section}_${index}`] = (bullets[section][index - 1] || "").trim() || null;
      }
    });
    CARGO_CONDITION_TIME_EVENTS.forEach((_, index) => {
      payload[`time_${index}_date`] = form[`time_${index}_date`] || null;
      payload[`time_${index}_hour`] = form[`time_${index}_hour`] || null;
      payload[`time_${index}_minute`] = form[`time_${index}_minute`] || null;
    });
    payload.status = payload.status || "Pending for review";
    return payload;
  }

  async function save() {
    if (!form.report_number || !form.vessel || !form.requested_by || !form.port || !form.country) {
      setMessage("Debe completar Report Number, buque, cliente, puerto y pais.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      if (initialReportId) {
        const result = await offlineApiRequest(`/vessel-cargo-condition-surveys/${encodeURIComponent(initialReportId)}`, {
          method: "PUT",
          session,
          body: buildPayload(),
          offlineLabel: `Actualizar Cargo Condition ${initialReportId}`
        });
        setEditing(isQueuedOffline(result) ? editing : false);
        setMessage(isQueuedOffline(result) ? "Sin internet: Cargo Condition guardado en cache local." : "Cargo Condition actualizado correctamente.");
      } else {
        const result = await offlineApiRequest("/vessel-cargo-condition-surveys/", {
          method: "POST",
          session,
          body: { ...buildPayload(), status: "Pending for review" },
          offlineLabel: `Crear Cargo Condition ${form.report_number || form.vessel}`
        });
        setMessage(isQueuedOffline(result) ? "Sin internet: Cargo Condition guardado en cache local." : "Cargo Condition enviado a revision.");
      }
      onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Cargo Condition.");
    } finally {
      setBusy(false);
    }
  }

  async function improveSection(section: CargoBulletSection) {
    const items = bullets[section].map((item) => item.trim()).filter(Boolean);
    if (!items.length) {
      setMessage(`La seccion ${CARGO_BULLET_LABELS[section]} no tiene texto para mejorar.`);
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await apiRequest<Record<string, unknown>>("/reports/ai/improve/cargo-condition", {
        method: "POST",
        session,
        body: {
          section,
          language: aiLanguage,
          vessel: form.vessel,
          port: form.port,
          items
        }
      });
      const nextItems = Array.isArray(response.items) ? response.items.map((item) => formatValue(item)).filter((item) => item !== "-") : [];
      if (!nextItems.length) throw new Error("PORTIA no devolvio texto valido.");
      setBullets((current) => ({ ...current, [section]: nextItems }));
      setMessage(`PORTIA mejoro ${CARGO_BULLET_LABELS[section]}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo mejorar la seccion.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadFile(kind: "word" | "presentation") {
    const id = initialReportId || form.id;
    if (!id) {
      setMessage("Primero debe guardar o abrir el informe desde Review.");
      return;
    }
    const endpoint = kind === "word"
      ? `/vessel-cargo-condition-surveys/word/${encodeURIComponent(id)}`
      : `/vessel-cargo-condition-surveys/presentation/${encodeURIComponent(id)}`;
    const extension = kind === "word" ? "docx" : "pdf";
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(endpoint, session, cleanFilePart(`Cargo_Condition_${kind}_${id}`) + `.${extension}`);
      setMessage(`${kind === "word" ? "Word" : "Presentacion"} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo generar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" = "text") {
    if (type === "date") return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={!readonly}
          style={[styles.input, readonly && styles.readonlyInput]}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  function renderBulletSection(section: CargoBulletSection) {
    const rows = bullets[section];
    return (
      <View style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{CARGO_BULLET_LABELS[section]}</Text>
        {rows.map((value, index) => (
          <View key={`${section}-${index}`} style={styles.formField}>
            <Text style={styles.label}>Bullet {index + 1}</Text>
            <TextInput
              editable={!readonly}
              style={[styles.input, styles.multilineInput, readonly && styles.readonlyInput]}
              multiline
              value={value}
              onChangeText={(text) => setBullets((current) => ({ ...current, [section]: rows.map((item, rowIndex) => rowIndex === index ? text : item) }))}
            />
            <Pressable style={styles.modalClose} onPress={() => setBullets((current) => ({ ...current, [section]: rows.length <= 1 ? [""] : rows.filter((_, rowIndex) => rowIndex !== index) }))}>
              <Text style={styles.modalCloseText}>Remove</Text>
            </Pressable>
          </View>
        ))}
        <Pressable style={styles.secondaryButton} onPress={() => rows.length < 10 && setBullets((current) => ({ ...current, [section]: [...rows, ""] }))}>
          <Text style={styles.secondaryButtonText}>+ Add Bullet</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => improveSection(section)}>
          <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
        </Pressable>
      </View>
    );
  }

  const tabs = [
    ["general", "General"],
    ["vessel", "Vessel"],
    ["times", "Time Sheet"],
    ["text", "Text"],
    ["final", "Final"]
  ] as const;

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>CARGO CONDITION SURVEY</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <View style={styles.financeFilterBox}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            <Pressable style={styles.secondaryButton} onPress={() => setServiceSelectorOpen(true)}><Text style={styles.secondaryButtonText}>Seleccionar Reporte</Text></Pressable>
            {initialReportId ? <Pressable style={styles.secondaryButton} onPress={() => setEditing((value) => !value)}><Text style={styles.secondaryButtonText}>{editing ? "Bloquear" : "Editar"}</Text></Pressable> : null}
            <Pressable style={styles.actionButton} onPress={save}><Text style={styles.actionButtonText}>{initialReportId ? "Guardar Cambios" : "Enviar a revision"}</Text></Pressable>
          </ScrollView>
          <View style={styles.summaryBox}>
            <Text style={styles.fieldKey}>Cargo Condition</Text>
            <Text style={styles.fieldValue}>{[form.report_number, form.vessel, form.requested_by, form.port, form.country].filter(Boolean).join(" | ") || "Sin servicio seleccionado"}</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            {tabs.map(([key, label]) => (
              <Pressable key={key} style={tab === key ? styles.actionButton : styles.modalClose} onPress={() => setTab(key)}>
                <Text style={tab === key ? styles.actionButtonText : styles.modalCloseText}>{label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          {tab === "general" ? CARGO_CONDITION_GENERAL_FIELDS.map(([key, label, type]) => renderField(key, label, type)) : null}
          {tab === "vessel" ? (
            <>
              {CARGO_CONDITION_VESSEL_FIELDS.map(([key, label]) => renderField(key, label))}
              {renderField("link_picture", "Image URL")}
            </>
          ) : null}
          {tab === "times" ? CARGO_CONDITION_TIME_EVENTS.map((label, index) => (
            <View key={label} style={styles.summaryBox}>
              <Text style={styles.cardTitle}>{label}</Text>
              {renderField(`time_${index}_date`, "Date", "date")}
              {renderField(`time_${index}_hour`, "HH")}
              {renderField(`time_${index}_minute`, "MM")}
            </View>
          )) : null}
          {tab === "text" ? (
            <>
              <SelectField label="PORTIA Language" value={aiLanguage} options={["EN", "ES"]} onChange={setAiLanguage} />
              {(Object.keys(CARGO_BULLET_LABELS) as CargoBulletSection[]).map((section) => renderBulletSection(section))}
            </>
          ) : null}
          {tab === "final" ? (
            <View style={styles.summaryBox}>
              <Text style={styles.cardTitle}>Generar Informe Final</Text>
              <Text style={styles.helperText}>La app genera Word y la presentacion PDF del backend. La union con un PDF externo de condition sigue siendo una accion de escritorio porque requiere seleccionar un archivo local.</Text>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFile("word")}><Text style={styles.secondaryButtonText}>Generar Word</Text></Pressable>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFile("presentation")}><Text style={styles.secondaryButtonText}>Generar Presentacion PDF</Text></Pressable>
            </View>
          ) : null}
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={message.includes("correctamente") || message.includes("revision") || message.includes("PORTIA mejoro") ? styles.helperText : styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(row) => {
            setForm((current) => ({ ...current, ...cargoConditionFormFromServiceReport(row) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function VesselConditionMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>(emptyVesselConditionForm());
  const [bullets, setBullets] = useState<Record<VesselConditionBulletSection, string[]>>(emptyVesselConditionBullets());
  const [tab, setTab] = useState<"general" | "vessel" | "times" | "text" | "final">("general");
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editing, setEditing] = useState(true);
  const [aiLanguage, setAiLanguage] = useState("EN");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const readonly = Boolean(initialReportId) && !editing;

  useEffect(() => {
    if (!visible) return;
    setForm(emptyVesselConditionForm());
    setBullets(emptyVesselConditionBullets());
    setTab("general");
    setEditing(!initialReportId);
    setAiLanguage("EN");
    setMessage("");
    if (initialReportId) loadExisting(initialReportId);
  }, [visible, initialReportId]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function loadExisting(reportId: string) {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/vessel-condition-surveys/id/${encodeURIComponent(reportId)}`, { session });
      const data = unwrapRecordPayload(payload) || payload;
      setForm(normalizeVesselConditionPayload(data));
      setBullets(extractVesselConditionBullets(data));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar Vessel Condition.");
    } finally {
      setBusy(false);
    }
  }

  function buildPayload() {
    const payload: Record<string, unknown> = { ...form };
    payload.operation = form.ts_4_operation || form.operation || null;
    (Object.keys(VESSEL_CONDITION_BULLET_LABELS) as VesselConditionBulletSection[]).forEach((section) => {
      const rows = bullets[section].map((item) => item.trim()).filter(Boolean).slice(0, 20);
      payload[section] = rows;
      for (let index = 1; index <= 20; index += 1) {
        payload[`${section}_${index}`] = rows[index - 1] || null;
      }
    });
    payload.status = payload.status || "Pending for review";
    return payload;
  }

  async function save() {
    if (!form.report_number || !form.vessel || !form.requested_by || !form.port || !form.country) {
      setMessage("Debe completar Report Number, buque, cliente, puerto y pais.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      if (initialReportId) {
        const result = await offlineApiRequest(`/vessel-condition-surveys/id/${encodeURIComponent(initialReportId)}`, {
          method: "PUT",
          session,
          body: buildPayload(),
          offlineLabel: `Actualizar Vessel Condition ${initialReportId}`
        });
        setEditing(isQueuedOffline(result) ? editing : false);
        setMessage(isQueuedOffline(result) ? "Sin internet: Vessel Condition guardado en cache local." : "Vessel Condition actualizado correctamente.");
      } else {
        const result = await offlineApiRequest("/vessel-condition-surveys", {
          method: "POST",
          session,
          body: { ...buildPayload(), status: "Pending for review" },
          offlineLabel: `Crear Vessel Condition ${form.report_number || form.vessel}`
        });
        setMessage(isQueuedOffline(result) ? "Sin internet: Vessel Condition guardado en cache local." : "Vessel Condition enviado a revision.");
      }
      onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Vessel Condition.");
    } finally {
      setBusy(false);
    }
  }

  async function improveSection(section: VesselConditionBulletSection) {
    const items = bullets[section].map((item) => item.trim()).filter(Boolean);
    if (!items.length) {
      setMessage(`La seccion ${VESSEL_CONDITION_BULLET_LABELS[section]} no tiene texto para mejorar.`);
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await apiRequest<Record<string, unknown>>("/reports/ai/improve/vessel-condition", {
        method: "POST",
        session,
        body: {
          section,
          language: aiLanguage,
          vessel: form.vessel,
          port: form.port,
          report_type: form.report_type,
          items
        }
      });
      const nextItems = Array.isArray(response.items) ? response.items.map((item) => formatValue(item)).filter((item) => item !== "-") : [];
      if (!nextItems.length) throw new Error("PORTIA no devolvio texto valido.");
      setBullets((current) => ({ ...current, [section]: nextItems.slice(0, 20) }));
      setMessage(`PORTIA mejoro ${VESSEL_CONDITION_BULLET_LABELS[section]}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo mejorar la seccion.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadFile(kind: "word" | "presentation") {
    const id = initialReportId || form.id;
    if (!id) {
      setMessage("Primero debe guardar o abrir el informe desde Review.");
      return;
    }
    const endpoint = kind === "word"
      ? `/vessel-condition-surveys/word/${encodeURIComponent(id)}`
      : `/vessel-condition-surveys/presentation/${encodeURIComponent(id)}`;
    const extension = kind === "word" ? "docx" : "pdf";
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(endpoint, session, cleanFilePart(`Vessel_Condition_${kind}_${id}`) + `.${extension}`);
      setMessage(`${kind === "word" ? "Word" : "Presentacion"} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo generar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" | "select" = "text") {
    if (type === "date") return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    if (type === "select") return <SelectField key={key} label={label} value={form[key] || ""} options={VESSEL_CONDITION_REPORT_TYPES} onChange={(value) => setValue(key, value)} />;
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={!readonly}
          style={[styles.input, readonly && styles.readonlyInput]}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  function renderTimeEvent(key: string, label: string) {
    return (
      <View key={key} style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{label}</Text>
        {key === "ts_4" ? <SelectField label="Operation" value={form.ts_4_operation || "Discharge"} options={["Discharge", "Charging"]} onChange={(value) => setValue("ts_4_operation", value)} /> : null}
        {renderField(`${key}_date`, "Date", "date")}
        {renderField(`${key}_hour`, "HH")}
        {renderField(`${key}_minute`, "MM")}
      </View>
    );
  }

  function renderBulletSection(section: VesselConditionBulletSection) {
    const rows = bullets[section];
    return (
      <View style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{VESSEL_CONDITION_BULLET_LABELS[section]}</Text>
        {rows.map((value, index) => (
          <View key={`${section}-${index}`} style={styles.formField}>
            <Text style={styles.label}>Bullet {index + 1}</Text>
            <TextInput
              editable={!readonly}
              style={[styles.input, styles.multilineInput, readonly && styles.readonlyInput]}
              multiline
              value={value}
              onChangeText={(text) => setBullets((current) => ({ ...current, [section]: rows.map((item, rowIndex) => rowIndex === index ? text : item) }))}
            />
            <Pressable style={styles.modalClose} onPress={() => setBullets((current) => ({ ...current, [section]: rows.length <= 1 ? [""] : rows.filter((_, rowIndex) => rowIndex !== index) }))}>
              <Text style={styles.modalCloseText}>Remove</Text>
            </Pressable>
          </View>
        ))}
        <Pressable style={styles.secondaryButton} onPress={() => rows.length < 20 && setBullets((current) => ({ ...current, [section]: [...rows, ""] }))}>
          <Text style={styles.secondaryButtonText}>+ Add Bullet</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => improveSection(section)}>
          <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
        </Pressable>
      </View>
    );
  }

  const tabs = [
    ["general", "General"],
    ["vessel", "Vessel"],
    ["times", "Time Sheet"],
    ["text", "Text"],
    ["final", "Final"]
  ] as const;

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>VESSEL CONDITION SURVEY</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <View style={styles.financeFilterBox}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            <Pressable style={styles.secondaryButton} onPress={() => setServiceSelectorOpen(true)}><Text style={styles.secondaryButtonText}>Seleccionar Reporte</Text></Pressable>
            {initialReportId ? <Pressable style={styles.secondaryButton} onPress={() => setEditing((value) => !value)}><Text style={styles.secondaryButtonText}>{editing ? "Bloquear" : "Editar"}</Text></Pressable> : null}
            <Pressable style={styles.actionButton} onPress={save}><Text style={styles.actionButtonText}>{initialReportId ? "Guardar Cambios" : "Enviar a revision"}</Text></Pressable>
          </ScrollView>
          <View style={styles.summaryBox}>
            <Text style={styles.fieldKey}>Vessel Condition</Text>
            <Text style={styles.fieldValue}>{[form.report_number, form.vessel, form.requested_by, form.port, form.country].filter(Boolean).join(" | ") || "Sin servicio seleccionado"}</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            {tabs.map(([key, label]) => (
              <Pressable key={key} style={tab === key ? styles.actionButton : styles.modalClose} onPress={() => setTab(key)}>
                <Text style={tab === key ? styles.actionButtonText : styles.modalCloseText}>{label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          {tab === "general" ? VESSEL_CONDITION_GENERAL_FIELDS.map(([key, label, type]) => renderField(key, label, type)) : null}
          {tab === "vessel" ? (
            <>
              {VESSEL_CONDITION_VESSEL_FIELDS.map(([key, label]) => renderField(key, label))}
              {renderField("link_picture", "8.1 Link Picture")}
            </>
          ) : null}
          {tab === "times" ? VESSEL_CONDITION_TIME_EVENTS.map(([key, label]) => renderTimeEvent(key, label)) : null}
          {tab === "text" ? (
            <>
              <SelectField label="PORTIA Language" value={aiLanguage} options={["EN", "ES"]} onChange={setAiLanguage} />
              {(Object.keys(VESSEL_CONDITION_BULLET_LABELS) as VesselConditionBulletSection[]).map((section) => renderBulletSection(section))}
            </>
          ) : null}
          {tab === "final" ? (
            <View style={styles.summaryBox}>
              <Text style={styles.cardTitle}>Generate Vessel Condition Report</Text>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFile("word")}><Text style={styles.secondaryButtonText}>Generar Word</Text></Pressable>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFile("presentation")}><Text style={styles.secondaryButtonText}>Generar Presentacion PDF</Text></Pressable>
            </View>
          ) : null}
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={message.includes("correctamente") || message.includes("revision") || message.includes("PORTIA mejoro") ? styles.helperText : styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(row) => {
            setForm((current) => ({ ...current, ...vesselConditionFormFromServiceReport(row) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function PortCaptancyMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>(emptyPortCaptancyForm());
  const [bullets, setBullets] = useState<Record<PortCaptancyBulletSection, string[]>>(emptyPortCaptancyBullets());
  const [tab, setTab] = useState<"general" | "vessel" | "times" | "text" | "final">("general");
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editing, setEditing] = useState(true);
  const [aiLanguage, setAiLanguage] = useState("EN");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const readonly = Boolean(initialReportId) && !editing;

  useEffect(() => {
    if (!visible) return;
    setForm(emptyPortCaptancyForm());
    setBullets(emptyPortCaptancyBullets());
    setTab("general");
    setEditing(!initialReportId);
    setAiLanguage("EN");
    setMessage("");
    if (initialReportId) loadExisting(initialReportId);
  }, [visible, initialReportId]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function loadExisting(reportId: string) {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/port-captancy-reports/id/${encodeURIComponent(reportId)}`, { session });
      const data = unwrapRecordPayload(payload) || payload;
      setForm(normalizePortCaptancyPayload(data));
      setBullets(extractPortCaptancyBullets(data));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar Port Captancy.");
    } finally {
      setBusy(false);
    }
  }

  function buildPayload() {
    const payload: Record<string, unknown> = { ...form };
    (Object.keys(PORT_CAPTANCY_BULLET_LABELS) as PortCaptancyBulletSection[]).forEach((section) => {
      const rows = bullets[section].map((item) => item.trim()).filter(Boolean).slice(0, 15);
      for (let index = 1; index <= 15; index += 1) {
        payload[`${section}_${index}`] = rows[index - 1] || null;
      }
    });
    return payload;
  }

  async function save() {
    if (!form.report_number || !form.vessel || !form.requested_by || !form.port || !form.country) {
      setMessage("Debe completar Report Number, buque, cliente, puerto y pais.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      if (initialReportId) {
        const result = await offlineApiRequest(`/port-captancy-reports/${encodeURIComponent(form.report_number)}`, {
          method: "PUT",
          session,
          body: buildPayload(),
          offlineLabel: `Actualizar Port Captancy ${form.report_number}`
        });
        setEditing(isQueuedOffline(result) ? editing : false);
        setMessage(isQueuedOffline(result) ? "Sin internet: Port Captancy guardado en cache local." : "Port Captancy actualizado correctamente.");
      } else {
        const result = await offlineApiRequest("/port-captancy-reports", {
          method: "POST",
          session,
          body: buildPayload(),
          offlineLabel: `Crear Port Captancy ${form.report_number || form.vessel}`
        });
        setMessage(isQueuedOffline(result) ? "Sin internet: Port Captancy guardado en cache local." : "Port Captancy enviado a revision.");
      }
      onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Port Captancy.");
    } finally {
      setBusy(false);
    }
  }

  async function improveSection(section: PortCaptancyBulletSection) {
    const items = bullets[section].map((item) => item.trim()).filter(Boolean);
    if (!items.length) {
      setMessage(`La seccion ${PORT_CAPTANCY_BULLET_LABELS[section]} no tiene texto para mejorar.`);
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const response = await apiRequest<Record<string, unknown>>("/reports/ai/improve/port-captancy", {
        method: "POST",
        session,
        body: {
          section,
          language: aiLanguage,
          vessel: form.vessel,
          port: form.port,
          operation: form.operation,
          items
        }
      });
      const nextItems = Array.isArray(response.items) ? response.items.map((item) => formatValue(item)).filter((item) => item !== "-") : [];
      if (!nextItems.length) throw new Error("PORTIA no devolvio texto valido.");
      setBullets((current) => ({ ...current, [section]: nextItems.slice(0, 15) }));
      setMessage(`PORTIA mejoro ${PORT_CAPTANCY_BULLET_LABELS[section]}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "PORTIA no pudo mejorar la seccion.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadFile(kind: "word" | "presentation") {
    const id = initialReportId || form.id;
    if (!id) {
      setMessage("Primero debe guardar o abrir el informe desde Review.");
      return;
    }
    const endpoint = kind === "word"
      ? `/port-captancy-reports/${encodeURIComponent(id)}/word`
      : `/port-captancy-reports/presentation/${encodeURIComponent(id)}`;
    const extension = kind === "word" ? "docx" : "pdf";
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(endpoint, session, cleanFilePart(`Port_Captancy_${kind}_${id}`) + `.${extension}`);
      setMessage(`${kind === "word" ? "Word" : "Presentacion"} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo generar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" = "text") {
    if (type === "date") return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={!readonly}
          style={[styles.input, readonly && styles.readonlyInput]}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  function renderTimeEvent(label: string, index: number) {
    return (
      <View key={label} style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{label}</Text>
        {renderField(`ts_date_${index}`, "Date", "date")}
        {renderField(`ts_hour_${index}`, "HH")}
        {renderField(`ts_min_${index}`, "MM")}
      </View>
    );
  }

  function renderBulletSection(section: PortCaptancyBulletSection) {
    const rows = bullets[section];
    return (
      <View style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{PORT_CAPTANCY_BULLET_LABELS[section]}</Text>
        {rows.map((value, index) => (
          <View key={`${section}-${index}`} style={styles.formField}>
            <Text style={styles.label}>Bullet {index + 1}</Text>
            <TextInput
              editable={!readonly}
              style={[styles.input, styles.multilineInput, readonly && styles.readonlyInput]}
              multiline
              value={value}
              onChangeText={(text) => setBullets((current) => ({ ...current, [section]: rows.map((item, rowIndex) => rowIndex === index ? text : item) }))}
            />
            <Pressable style={styles.modalClose} onPress={() => setBullets((current) => ({ ...current, [section]: rows.length <= 1 ? [""] : rows.filter((_, rowIndex) => rowIndex !== index) }))}>
              <Text style={styles.modalCloseText}>Remove</Text>
            </Pressable>
          </View>
        ))}
        <Pressable style={styles.secondaryButton} onPress={() => rows.length < 15 && setBullets((current) => ({ ...current, [section]: [...rows, ""] }))}>
          <Text style={styles.secondaryButtonText}>+ Add Bullet</Text>
        </Pressable>
        <Pressable style={styles.secondaryButton} onPress={() => improveSection(section)}>
          <Text style={styles.secondaryButtonText}>Mejorar con PORTIA</Text>
        </Pressable>
      </View>
    );
  }

  const tabs = [
    ["general", "General"],
    ["vessel", "Vessel"],
    ["times", "Time Sheet"],
    ["text", "Text"],
    ["final", "Final"]
  ] as const;

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>PORT CAPTANCY REPORT</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <View style={styles.financeFilterBox}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            <Pressable style={styles.secondaryButton} onPress={() => setServiceSelectorOpen(true)}><Text style={styles.secondaryButtonText}>Seleccionar Informe</Text></Pressable>
            {initialReportId ? <Pressable style={styles.secondaryButton} onPress={() => setEditing((value) => !value)}><Text style={styles.secondaryButtonText}>{editing ? "Bloquear" : "Editar"}</Text></Pressable> : null}
            <Pressable style={styles.actionButton} onPress={save}><Text style={styles.actionButtonText}>{initialReportId ? "Guardar Cambios" : "Enviar a revision"}</Text></Pressable>
          </ScrollView>
          <View style={styles.summaryBox}>
            <Text style={styles.fieldKey}>Port Captancy</Text>
            <Text style={styles.fieldValue}>{[form.report_number, form.vessel, form.requested_by, form.port, form.country].filter(Boolean).join(" | ") || "Sin servicio seleccionado"}</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            {tabs.map(([key, label]) => (
              <Pressable key={key} style={tab === key ? styles.actionButton : styles.modalClose} onPress={() => setTab(key)}>
                <Text style={tab === key ? styles.actionButtonText : styles.modalCloseText}>{label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          {tab === "general" ? PORT_CAPTANCY_GENERAL_FIELDS.map(([key, label, type]) => renderField(key, label, type)) : null}
          {tab === "vessel" ? (
            <>
              {PORT_CAPTANCY_VESSEL_FIELDS.map(([key, label]) => renderField(key, label))}
              {renderField("link_picture", "7. Link Picture")}
            </>
          ) : null}
          {tab === "times" ? PORT_CAPTANCY_TIME_EVENTS.map((label, index) => renderTimeEvent(label, index)) : null}
          {tab === "text" ? (
            <>
              <SelectField label="PORTIA Language" value={aiLanguage} options={["EN", "ES"]} onChange={setAiLanguage} />
              {(Object.keys(PORT_CAPTANCY_BULLET_LABELS) as PortCaptancyBulletSection[]).map((section) => renderBulletSection(section))}
            </>
          ) : null}
          {tab === "final" ? (
            <View style={styles.summaryBox}>
              <Text style={styles.cardTitle}>Generate Port Captancy Report</Text>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFile("word")}><Text style={styles.secondaryButtonText}>Generar Word</Text></Pressable>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFile("presentation")}><Text style={styles.secondaryButtonText}>Generar Presentacion PDF</Text></Pressable>
            </View>
          ) : null}
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={message.includes("correctamente") || message.includes("revision") || message.includes("PORTIA mejoro") ? styles.helperText : styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(row) => {
            setForm((current) => ({ ...current, ...portCaptancyFormFromServiceReport(row) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function VesselBunkerMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>(emptyBunkerForm());
  const [vlsfoTanks, setVlsfoTanks] = useState<BunkerTank[]>([]);
  const [mgoTanks, setMgoTanks] = useState<BunkerTank[]>([]);
  const [figures, setFigures] = useState<BunkerFigure[]>([]);
  const [tab, setTab] = useState<"header" | "figures" | "tanks" | "logs" | "final">("header");
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editing, setEditing] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const readonly = Boolean(initialReportId) && !editing;

  useEffect(() => {
    if (!visible) return;
    setForm(emptyBunkerForm());
    setVlsfoTanks([]);
    setMgoTanks([]);
    setFigures([]);
    setTab("header");
    setEditing(!initialReportId);
    setMessage("");
    if (initialReportId) loadExisting(initialReportId);
  }, [visible, initialReportId]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function loadExisting(reportId: string) {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/vessel-bunker-reports/${encodeURIComponent(reportId)}`, { session });
      const data = unwrapRecordPayload(payload) || payload;
      setForm(normalizeBunkerPayload(data));
      setVlsfoTanks(extractBunkerTanks(data, "vlsfo"));
      setMgoTanks(extractBunkerTanks(data, "mgo"));
      setFigures(extractBunkerFigures(data));
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar Vessel Bunker.");
    } finally {
      setBusy(false);
    }
  }

  function buildPayload() {
    const payload: Record<string, unknown> = { ...form };
    payload.workflow_status = payload.workflow_status || "Pending Review";
    payload.status = payload.status || "Pending";

    for (let index = 1; index <= 20; index += 1) {
      const vlsfo = vlsfoTanks[index - 1] || emptyBunkerTank();
      const mgo = mgoTanks[index - 1] || emptyBunkerTank();
      (Object.keys(vlsfo) as Array<keyof BunkerTank>).forEach((key) => {
        payload[`vlsfo_tank_${index}_${key}`] = vlsfo[key] || null;
        payload[`mgo_tank_${index}_${key}`] = mgo[key] || null;
      });
    }
    for (let index = 1; index <= 10; index += 1) {
      const figure = figures[index - 1] || emptyBunkerFigure();
      (Object.keys(figure) as Array<keyof BunkerFigure>).forEach((key) => {
        payload[`bunker_figure_${index}_${key}`] = figure[key] || null;
      });
    }
    return payload;
  }

  async function previewExcel() {
    if (!form.bunker_cert_no || !form.ship_name) {
      setMessage("Debe seleccionar un reporte y completar buque antes de visualizar.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const filename = cleanFilePart(`${form.bunker_cert_no || "Vessel_Bunker"}_preview`) + ".xlsx";
      await downloadSessionFile("/vessel-bunker-preview/excel", session, filename, "POST", buildPayload());
      setMessage("Excel preview generado correctamente.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo generar el Excel preview.");
    } finally {
      setBusy(false);
    }
  }

  async function save(sendToReview: boolean) {
    if (!form.bunker_cert_no || !form.ship_name || !form.client || !form.port || !form.country) {
      setMessage("Debe completar Cert No, buque, cliente, puerto y pais.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      if (initialReportId) {
        const result = await offlineApiRequest(`/vessel-bunker-reports/${encodeURIComponent(initialReportId)}`, {
          method: "PUT",
          session,
          body: buildPayload(),
          offlineLabel: `Actualizar Vessel Bunker ${initialReportId}`
        });
        setEditing(isQueuedOffline(result) ? editing : false);
        setMessage(isQueuedOffline(result) ? "Sin internet: Vessel Bunker guardado en cache local." : "Vessel Bunker actualizado correctamente.");
      } else {
        const result = await offlineApiRequest("/vessel-bunker-reports/", {
          method: "POST",
          session,
          body: { ...buildPayload(), workflow_status: "Pending Review", status: "Pending" },
          offlineLabel: `Crear Vessel Bunker ${form.bunker_cert_no || form.ship_name}`
        });
        setMessage(isQueuedOffline(result) ? "Sin internet: Vessel Bunker guardado en cache local." : "Vessel Bunker enviado a revision.");
      }
      if (sendToReview || initialReportId) onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Vessel Bunker.");
    } finally {
      setBusy(false);
    }
  }

  async function downloadFinal(kind: "excel" | "pdf" | "presentation") {
    const id = initialReportId || form.id;
    if (!id) {
      setMessage("Primero debe guardar el informe para generar archivos finales.");
      return;
    }
    const endpoint = kind === "excel"
      ? `/vessel-bunker-excel/generate/${encodeURIComponent(id)}`
      : kind === "pdf"
        ? `/vessel-bunker-excel/generate-pdf/${encodeURIComponent(id)}`
        : `/vessel-bunker-reports/presentation/${encodeURIComponent(id)}`;
    const extension = kind === "excel" ? "xlsx" : "pdf";
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(endpoint, session, cleanFilePart(`Vessel_Bunker_${kind}_${id}`) + `.${extension}`);
      setMessage(`${kind.toUpperCase()} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo generar el archivo.");
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" | "select" | "multiline" = "text") {
    if (type === "date") return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    if (type === "select") return <SelectField key={key} label={label} value={form[key] || ""} options={BUNKER_CERTIFICATE_OPTIONS} onChange={(value) => setValue(key, value)} />;
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={!readonly}
          style={[styles.input, type === "multiline" && styles.multilineInput, readonly && styles.readonlyInput]}
          multiline={type === "multiline"}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  function renderTankRows(title: string, rows: BunkerTank[], setRows: (rows: BunkerTank[]) => void) {
    return (
      <View style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{title}</Text>
        {rows.map((tank, index) => (
          <View key={`${title}-${index}`} style={styles.summaryBox}>
            {(Object.keys(emptyBunkerTank()) as Array<keyof BunkerTank>).map((key) => (
              <View key={key} style={styles.formField}>
                <Text style={styles.label}>{key.replaceAll("_", " ")}</Text>
                <TextInput
                  editable={!readonly}
                  style={[styles.input, readonly && styles.readonlyInput]}
                  value={tank[key]}
                  onChangeText={(value) => setRows(rows.map((item, rowIndex) => rowIndex === index ? { ...item, [key]: value } : item))}
                />
              </View>
            ))}
            <Pressable style={styles.modalClose} onPress={() => setRows(rows.filter((_, rowIndex) => rowIndex !== index))}>
              <Text style={styles.modalCloseText}>Remove Tank</Text>
            </Pressable>
          </View>
        ))}
        <Pressable style={styles.secondaryButton} onPress={() => rows.length < 20 && setRows([...rows, emptyBunkerTank()])}>
          <Text style={styles.secondaryButtonText}>+ Add Tank</Text>
        </Pressable>
      </View>
    );
  }

  const tabs = [
    ["header", "Header"],
    ["figures", "Figures"],
    ["tanks", "Tanks"],
    ["logs", "Log Book"],
    ["final", "Final"]
  ] as const;

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>ON/OFF/SPOT BUNKER SURVEY</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <View style={styles.financeFilterBox}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            <Pressable style={styles.secondaryButton} onPress={() => setServiceSelectorOpen(true)}><Text style={styles.secondaryButtonText}>Seleccionar Reporte</Text></Pressable>
            <Pressable style={styles.secondaryButton} onPress={previewExcel}><Text style={styles.secondaryButtonText}>Visualizar Excel</Text></Pressable>
            {initialReportId ? <Pressable style={styles.secondaryButton} onPress={() => setEditing((value) => !value)}><Text style={styles.secondaryButtonText}>{editing ? "Bloquear" : "Editar"}</Text></Pressable> : null}
            {initialReportId ? <Pressable style={styles.actionButton} onPress={() => save(false)}><Text style={styles.actionButtonText}>Guardar Cambios</Text></Pressable> : <Pressable style={styles.actionButton} onPress={() => save(true)}><Text style={styles.actionButtonText}>Enviar a revision</Text></Pressable>}
          </ScrollView>
          <View style={styles.summaryBox}>
            <Text style={styles.fieldKey}>Bunker Report</Text>
            <Text style={styles.fieldValue}>{[form.bunker_cert_no, form.ship_name, form.client, form.port, form.country].filter(Boolean).join(" | ") || "Sin servicio seleccionado"}</Text>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
            {tabs.map(([key, label]) => (
              <Pressable key={key} style={tab === key ? styles.actionButton : styles.modalClose} onPress={() => setTab(key)}>
                <Text style={tab === key ? styles.actionButtonText : styles.modalCloseText}>{label}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          {tab === "header" ? (
            <>
              {BUNKER_MAIN_FIELDS.map(([key, label, type]) => renderField(key, label, type))}
              <View style={styles.summaryBox}>
                <Text style={styles.cardTitle}>Signatures</Text>
                {BUNKER_SIGNATURE_FIELDS.map(([key, label]) => renderField(key, label))}
              </View>
            </>
          ) : null}
          {tab === "figures" ? (
            <>
              {BUNKER_DELIVERY_FIELDS.map(([key, label, type]) => renderField(key, label, type))}
              <View style={styles.summaryBox}>
                <Text style={styles.cardTitle}>Bunker Figures</Text>
                {figures.map((figure, index) => (
                  <View key={`figure-${index}`} style={styles.summaryBox}>
                    {(Object.keys(emptyBunkerFigure()) as Array<keyof BunkerFigure>).map((key) => (
                      <View key={key} style={styles.formField}>
                        <Text style={styles.label}>{key.toUpperCase()}</Text>
                        <TextInput
                          editable={!readonly}
                          style={[styles.input, readonly && styles.readonlyInput]}
                          value={figure[key]}
                          onChangeText={(value) => setFigures(figures.map((item, rowIndex) => rowIndex === index ? { ...item, [key]: value } : item))}
                        />
                      </View>
                    ))}
                    <Pressable style={styles.modalClose} onPress={() => setFigures(figures.filter((_, rowIndex) => rowIndex !== index))}>
                      <Text style={styles.modalCloseText}>Remove Figure</Text>
                    </Pressable>
                  </View>
                ))}
                <Pressable style={styles.secondaryButton} onPress={() => figures.length < 10 && setFigures([...figures, emptyBunkerFigure()])}>
                  <Text style={styles.secondaryButtonText}>+ Add Bunker Figure</Text>
                </Pressable>
              </View>
            </>
          ) : null}
          {tab === "tanks" ? (
            <>
              {renderTankRows("FUEL OIL - VLSFO Tanks", vlsfoTanks, setVlsfoTanks)}
              {renderTankRows("DIESEL / MGO Tanks", mgoTanks, setMgoTanks)}
            </>
          ) : null}
          {tab === "logs" ? (
            <>
              {BUNKER_LOG_EVENTS.map(([prefix, label]) => (
                <View key={prefix} style={styles.summaryBox}>
                  <Text style={styles.cardTitle}>{label}</Text>
                  {renderField(`${prefix}_date`, "Date", "date")}
                  {renderField(`${prefix}_hour`, "HH")}
                  {renderField(`${prefix}_minute`, "MM")}
                  {["vlsfo", "hfso", "mdo", "lsmgo"].map((fuel) => renderField(`${prefix}_${fuel}`, fuel.toUpperCase()))}
                </View>
              ))}
              <View style={styles.summaryBox}>
                <Text style={styles.cardTitle}>Consumption (MT / DAY)</Text>
                {BUNKER_CONSUMPTION_ROWS.map(([prefix, label]) => (
                  <View key={prefix} style={styles.summaryBox}>
                    <Text style={styles.fieldKey}>{label}</Text>
                    {["vlsfo", "hfso", "mdo", "lsmgo"].map((fuel) => renderField(`${prefix}_${fuel}`, fuel.toUpperCase()))}
                  </View>
                ))}
              </View>
            </>
          ) : null}
          {tab === "final" ? (
            <View style={styles.summaryBox}>
              <Text style={styles.cardTitle}>Crear Informe Final</Text>
              <Text style={styles.helperText}>Primero guarda o abre un Vessel Bunker desde Review. Luego puedes generar el Excel, el PDF final o la presentacion.</Text>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFinal("excel")}><Text style={styles.secondaryButtonText}>Generate Excel</Text></Pressable>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFinal("pdf")}><Text style={styles.secondaryButtonText}>Generate Final Report (Bunker Only)</Text></Pressable>
              <Pressable style={styles.secondaryButton} onPress={() => downloadFinal("presentation")}><Text style={styles.secondaryButtonText}>Generate Presentation PDF</Text></Pressable>
            </View>
          ) : null}
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={message.includes("correctamente") || message.includes("revision") ? styles.helperText : styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(row) => {
            setForm((current) => ({ ...current, ...bunkerFormFromServiceReport(row) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function DraftSurveyMobileModal({
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
  const [mode, setMode] = useState<"choose" | "create" | "existing">("choose");
  const [tab, setTab] = useState<"general" | "draft" | "ballast" | "word">("general");
  const [form, setForm] = useState<Record<string, string>>(emptyDraftForm());
  const [ballast, setBallast] = useState<{ init: DraftTank[]; final: DraftTank[] }>({ init: [], final: [] });
  const [freshWater, setFreshWater] = useState<{ init: DraftTank[]; final: DraftTank[] }>({ init: [], final: [] });
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [existingSelectorOpen, setExistingSelectorOpen] = useState(false);
  const [editing, setEditing] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const draftNumber = form.draft_report_number || form.survey_no;
  const readonly = mode === "existing" && !editing;

  useEffect(() => {
    if (!visible) return;
    setMode("choose");
    setTab("general");
    setForm(emptyDraftForm());
    setBallast({ init: [], final: [] });
    setFreshWater({ init: [], final: [] });
    setEditing(true);
    setMessage("");
  }, [visible]);

  function setValue(key: string, value: string) {
    setForm((current) => {
      const next = { ...current, [key]: value };
      if (key === "loading" && value === "true") next.unloading = "false";
      if (key === "unloading" && value === "true") next.loading = "false";
      return next;
    });
  }

  function buildPayload(): Record<string, unknown> {
    const payload: Record<string, unknown> = { ...form };
    payload.draft_report_number = payload.draft_report_number || payload.survey_no;
    payload.survey_no = payload.survey_no || payload.draft_report_number;
    return {
      ...payload,
      ballast,
      fresh_water: freshWater
    };
  }

  function buildWordPayload() {
    const payload: Record<string, unknown> = {};
    DRAFT_WORD_FIELDS.forEach(([key]) => { payload[key] = form[key] || null; });
    DRAFT_WORD_DATETIME_FIELDS.forEach(([key]) => {
      payload[`${key}_date`] = form[`${key}_date`] || null;
      payload[`${key}_time`] = form[`${key}_time`] || null;
    });
    ["year", "month", "continent", "country", "port", "client", "draft_report_number"].forEach((key) => {
      payload[key] = form[key] || null;
    });
    return payload;
  }

  async function loadExisting(draftReportNumber: string) {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest<Record<string, unknown>>(`/draft-survey/unified/${encodeURIComponent(draftReportNumber)}`, { session });
      const data = asRecord(payload.data) || payload;
      setForm(normalizeDraftPayload(payload));
      setBallast({ init: extractDraftTanks(data, "init"), final: extractDraftTanks(data, "final") });
      setFreshWater({ init: extractDraftTanks(data, "init", true), final: extractDraftTanks(data, "final", true) });
      setMode("existing");
      setEditing(false);
      setTab("general");
      setExistingSelectorOpen(false);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar el Draft.");
    } finally {
      setBusy(false);
    }
  }

  async function previewExcel() {
    const payload = buildPayload();
    if (!payload["vessel_mv"]) {
      setMessage("Debe seleccionar un servicio o cargar un Draft antes de visualizar.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const filename = cleanFilePart(`${payload["draft_report_number"] || "Draft_Survey"}_preview`) + ".xlsx";
      await downloadSessionFile("/draft-survey/preview/excel", session, filename, "POST", payload);
      setMessage("Excel de Draft generado correctamente.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo generar el Excel.");
    } finally {
      setBusy(false);
    }
  }

  async function saveDraft(sendToReview: boolean) {
    const payload = buildPayload();
    if (!payload["vessel_mv"] || !payload["draft_report_number"] || !payload["year"] || !payload["month"] || !payload["country"] || !payload["port"] || !payload["client"]) {
      setMessage("Debe completar servicio, metadata y buque antes de guardar.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      if (mode === "existing") {
        const mainResult = await offlineApiRequest(`/draft-survey/${encodeURIComponent(draftNumber)}`, {
          method: "PUT",
          session,
          body: payload,
          offlineLabel: `Actualizar Draft Survey ${draftNumber}`
        });
        const ballastResult = await offlineApiRequest(`/draft-survey-extra/ballast/${encodeURIComponent(draftNumber)}`, {
          method: "PUT",
          session,
          body: { ballast, fresh_water: freshWater },
          offlineLabel: `Actualizar tanques Draft Survey ${draftNumber}`
        });
        const wordResult = await offlineApiRequest(`/draft-survey-extra/word/${encodeURIComponent(draftNumber)}`, {
          method: "POST",
          session,
          body: buildWordPayload(),
          offlineLabel: `Actualizar Word Draft Survey ${draftNumber}`
        });
        const queued = [mainResult, ballastResult, wordResult].some(isQueuedOffline);
        setMessage(queued ? "Sin internet: Draft Survey guardado en cache local." : "Draft actualizado correctamente.");
        if (!queued) setEditing(false);
      } else {
        const created = await offlineApiRequest<Record<string, unknown>>("/draft-survey/", {
          method: "POST",
          session,
          body: payload,
          offlineLabel: `Crear Draft Survey ${payload["draft_report_number"] || payload["vessel_mv"]}`
        });
        if (isQueuedOffline(created)) {
          setMessage("Sin internet: Draft Survey guardado en cache local para sincronizar.");
          return;
        }
        const generalId = formatValue(created.general_id);
        if (generalId === "-") throw new Error("El backend no devolvio general_id.");
        const ballastResult = await offlineApiRequest(`/draft-survey-extra/ballast/${encodeURIComponent(generalId)}`, {
          method: "POST",
          session,
          body: { ballast, fresh_water: freshWater },
          offlineLabel: `Crear tanques Draft Survey ${generalId}`
        });
        const wordResult = await offlineApiRequest(`/draft-survey-extra/word/${encodeURIComponent(generalId)}`, {
          method: "POST",
          session,
          body: buildWordPayload(),
          offlineLabel: `Crear Word Draft Survey ${generalId}`
        });
        setForm((current) => ({ ...current, general_id: generalId }));
        setMode("existing");
        const queued = [ballastResult, wordResult].some(isQueuedOffline);
        if (!queued) setEditing(false);
        setMessage(queued ? "Sin internet: extras de Draft Survey guardados en cache local." : sendToReview ? "Draft enviado a revision." : "Draft guardado correctamente.");
      }
      if (sendToReview) onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Draft Survey.");
    } finally {
      setBusy(false);
    }
  }

  function renderTextField(key: string, label: string, multiline = false) {
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={!readonly}
          style={[styles.input, multiline && styles.multilineInput, readonly && styles.readonlyInput]}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
          multiline={multiline}
        />
      </View>
    );
  }

  function renderTankEditor(kind: "ballast" | "fresh", prefix: "init" | "final") {
    const rows = kind === "ballast" ? ballast[prefix] : freshWater[prefix];
    const setRows = (nextRows: DraftTank[]) => {
      if (kind === "ballast") setBallast((current) => ({ ...current, [prefix]: nextRows }));
      else setFreshWater((current) => ({ ...current, [prefix]: nextRows }));
    };
    return (
      <View style={styles.summaryBox}>
        <Text style={styles.cardTitle}>{prefix.toUpperCase()} {kind === "ballast" ? "BALLAST" : "FRESH WATER"}</Text>
        {rows.map((tank, index) => (
          <View key={`${kind}-${prefix}-${index}`} style={styles.summaryBox}>
            {renderTankInput(tank, index, "tank_name", "Tank", rows, setRows)}
            {kind === "fresh" ? renderTankInput(tank, index, "height", "Height", rows, setRows) : null}
            {renderTankInput(tank, index, "sounding", "Sounding", rows, setRows)}
            {renderTankInput(tank, index, "volume", "Volume", rows, setRows)}
            {renderTankInput(tank, index, "density", "Density", rows, setRows)}
            <Pressable style={styles.modalClose} onPress={() => setRows(rows.filter((_, rowIndex) => rowIndex !== index))}>
              <Text style={styles.modalCloseText}>Eliminar tanque</Text>
            </Pressable>
          </View>
        ))}
        <Pressable style={styles.secondaryButton} onPress={() => setRows([...rows, { tank_name: "", height: "", sounding: "", volume: "", density: "" }])}>
          <Text style={styles.secondaryButtonText}>+ Add {kind === "ballast" ? "Tank" : "FW Tank"}</Text>
        </Pressable>
      </View>
    );
  }

  function renderTankInput(tank: DraftTank, index: number, key: keyof DraftTank, label: string, rows: DraftTank[], setRows: (nextRows: DraftTank[]) => void) {
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={!readonly}
          style={[styles.input, readonly && styles.readonlyInput]}
          value={String(tank[key] || "")}
          onChangeText={(value) => setRows(rows.map((item, rowIndex) => rowIndex === index ? { ...item, [key]: value } : item))}
        />
      </View>
    );
  }

  const tabs = [
    ["general", "General"], ["draft", "Draft"], ["ballast", "Ballast"], ["word", "Word Report"]
  ] as const;

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Vessel Draft Survey</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        {mode === "choose" ? (
          <View style={styles.modalBody}>
            <Pressable style={styles.actionButton} onPress={() => { setMode("create"); setEditing(true); }}>
              <Text style={styles.actionButtonText}>Crear desde cero</Text>
            </Pressable>
            <Pressable style={styles.secondaryButton} onPress={() => setExistingSelectorOpen(true)}>
              <Text style={styles.secondaryButtonText}>Abrir Draft previo</Text>
            </Pressable>
            {message ? <Text style={styles.error}>{message}</Text> : null}
          </View>
        ) : (
          <>
            <View style={styles.financeFilterBox}>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
                <Pressable style={styles.secondaryButton} onPress={() => setServiceSelectorOpen(true)}><Text style={styles.secondaryButtonText}>Seleccionar Reporte</Text></Pressable>
                <Pressable style={styles.secondaryButton} onPress={previewExcel}><Text style={styles.secondaryButtonText}>Visualizar Draft Excel</Text></Pressable>
                {mode === "existing" ? <Pressable style={styles.secondaryButton} onPress={() => setEditing((value) => !value)}><Text style={styles.secondaryButtonText}>{editing ? "Bloquear" : "Editar"}</Text></Pressable> : null}
                <Pressable style={styles.actionButton} onPress={() => saveDraft(false)}><Text style={styles.actionButtonText}>Guardar</Text></Pressable>
                <Pressable style={styles.actionButton} onPress={() => saveDraft(true)}><Text style={styles.actionButtonText}>Enviar a revision</Text></Pressable>
              </ScrollView>
              <View style={styles.summaryBox}>
                <Text style={styles.fieldKey}>Draft Information</Text>
                <Text style={styles.fieldValue}>{[form.year, form.month, form.country, form.port, form.client, form.draft_report_number].filter(Boolean).join(" | ") || "Sin servicio seleccionado"}</Text>
              </View>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.actionBar}>
                {tabs.map(([key, label]) => (
                  <Pressable key={key} style={tab === key ? styles.actionButton : styles.modalClose} onPress={() => setTab(key)}>
                    <Text style={tab === key ? styles.actionButtonText : styles.modalCloseText}>{label}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            </View>
            <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
              {tab === "general" ? (
                <>
                  {DRAFT_GENERAL_FIELDS.map(([key, label]) => renderTextField(key, label, key === "hydro_tables_issued"))}
                  <View style={styles.rememberRow}>
                    <Text style={styles.rememberText}>Range of trim correction tables available</Text>
                    <Switch value={form.trim_tables_available === "true"} disabled={readonly} onValueChange={(value) => setValue("trim_tables_available", value ? "true" : "false")} trackColor={{ true: BLUE }} />
                  </View>
                </>
              ) : null}
              {tab === "draft" ? (
                <>
                  {DRAFT_TOP_FIELDS.map(([key, label, type]) => type === "date" ? (
                    <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />
                  ) : renderTextField(key, label))}
                  <View style={styles.rememberRow}><Text style={styles.rememberText}>Loading</Text><Switch value={form.loading === "true"} disabled={readonly} onValueChange={(value) => setValue("loading", value ? "true" : "false")} trackColor={{ true: BLUE }} /></View>
                  <View style={styles.rememberRow}><Text style={styles.rememberText}>Unloading</Text><Switch value={form.unloading === "true"} disabled={readonly} onValueChange={(value) => setValue("unloading", value ? "true" : "false")} trackColor={{ true: BLUE }} /></View>
                  {(["init", "final"] as const).map((prefix) => (
                    <View key={prefix} style={styles.summaryBox}>
                      <Text style={styles.cardTitle}>{prefix.toUpperCase()} SURVEY</Text>
                      {DRAFT_SIDE_FIELDS.map(([suffix, label]) => renderTextField(`${prefix}_${suffix}`, label))}
                    </View>
                  ))}
                  <View style={styles.summaryBox}>
                    <Text style={styles.cardTitle}>INITIAL - Hydrostatic Data</Text>
                    {DRAFT_HYDRO_FIELDS.map((suffix) => renderTextField(`init_${suffix}`, suffix.replaceAll("_", " ").toUpperCase()))}
                  </View>
                </>
              ) : null}
              {tab === "ballast" ? (
                <>
                  {renderTankEditor("ballast", "init")}
                  {renderTankEditor("ballast", "final")}
                  {renderTankEditor("fresh", "init")}
                  {renderTankEditor("fresh", "final")}
                </>
              ) : null}
              {tab === "word" ? (
                <>
                  {DRAFT_WORD_FIELDS.map(([key, label]) => renderTextField(key, label))}
                  {DRAFT_WORD_DATETIME_FIELDS.map(([key, label]) => (
                    <View key={key} style={styles.summaryBox}>
                      <Text style={styles.cardTitle}>{label}</Text>
                      <DateField label="Date" value={form[`${key}_date`] || ""} onChange={(value) => setValue(`${key}_date`, value)} />
                      {renderTextField(`${key}_time`, "Time HH:MM")}
                    </View>
                  ))}
                </>
              ) : null}
              {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
              {message ? <Text style={message.includes("correctamente") || message.includes("revision") ? styles.helperText : styles.error}>{message}</Text> : null}
            </ScrollView>
          </>
        )}
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(row) => {
            setForm((current) => ({ ...current, ...draftServiceFormFromRow(row) }));
            setServiceSelectorOpen(false);
          }}
        />
        <DraftExistingSelectorModal visible={existingSelectorOpen} session={session} onClose={() => setExistingSelectorOpen(false)} onSelect={loadExisting} />
      </SafeAreaView>
    </Modal>
  );
}

function WeightCertificateMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId?: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isReview = Boolean(initialReportId);
  const [form, setForm] = useState(emptyWeightCertificateForm());
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editEnabled, setEditEnabled] = useState(!isReview);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!visible) return;
    setMessage("");
    setEditEnabled(!initialReportId);
    if (!initialReportId) {
      setForm(emptyWeightCertificateForm());
      return;
    }
    setBusy(true);
    apiRequest<Record<string, unknown>>(`/weight-certificates/${initialReportId}`, { session })
      .then((payload) => {
        const next = emptyWeightCertificateForm();
        Object.entries(payload).forEach(([key, value]) => {
          if (value === null || value === undefined) return;
          if (key in next && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) {
            next[key] = String(value);
          }
        });
        setForm(next);
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo cargar Weight Certificate."))
      .finally(() => setBusy(false));
  }, [initialReportId, session, visible]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function buildPayload() {
    return Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, value.trim() ? value.trim() : null])
    );
  }

  async function save() {
    if (!form.report_number.trim()) {
      setMessage("Seleccione un servicio primero.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const endpoint = initialReportId ? `/weight-certificates/${initialReportId}` : "/weight-certificates";
      const result = await offlineApiRequest(endpoint, {
        method: initialReportId ? "PUT" : "POST",
        body: buildPayload(),
        session,
        offlineLabel: `${initialReportId ? "Actualizar" : "Crear"} Weight Certificate ${form.report_number}`
      });
      setMessage(isQueuedOffline(result) ? "Sin internet: Weight Certificate guardado en cache local para sincronizar." : initialReportId ? "Cambios guardados correctamente." : "Weight Certificate enviado a revision.");
      if (!isQueuedOffline(result)) await onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Weight Certificate.");
    } finally {
      setBusy(false);
    }
  }

  async function download(kind: "word" | "pdf") {
    if (!initialReportId) {
      setMessage("Primero debe enviar el certificado a revision.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(
        `/weight-certificates/${initialReportId}/${kind}`,
        session,
        cleanFilePart(`Weight_Certificate_${form.report_number || initialReportId}`) + `.${kind === "word" ? "docx" : "pdf"}`
      );
      setMessage(`${kind.toUpperCase()} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `No se pudo generar ${kind.toUpperCase()}.`);
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" | "multiline" = "text") {
    if (type === "date") {
      if (!editEnabled) {
        return (
          <View key={key} style={styles.formField}>
            <Text style={styles.label}>{label}</Text>
            <TextInput editable={false} style={[styles.input, styles.readonlyInput]} value={form[key] || ""} />
          </View>
        );
      }
      return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    }
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={editEnabled}
          style={[styles.input, type === "multiline" && styles.multilineInput, !editEnabled && styles.readonlyInput]}
          multiline={type === "multiline"}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>WEIGHT CERTIFICATE</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          <View style={styles.informesHomeActions}>
            {!isReview ? (
              <Pressable style={styles.actionButton} onPress={() => setServiceSelectorOpen(true)}>
                <Text style={styles.actionButtonText}>Seleccionar Servicio</Text>
              </Pressable>
            ) : (
              <Pressable style={styles.actionButton} onPress={() => setEditEnabled(true)}>
                <Text style={styles.actionButtonText}>Editar</Text>
              </Pressable>
            )}
            {isReview ? (
              <>
                <Pressable style={styles.secondaryButton} onPress={() => download("word")}><Text style={styles.secondaryButtonText}>Word</Text></Pressable>
                <Pressable style={styles.secondaryButton} onPress={() => download("pdf")}><Text style={styles.secondaryButtonText}>PDF</Text></Pressable>
              </>
            ) : null}
          </View>

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Header</Text></View>
          {renderField("report_number", "Report Number")}
          {renderField("continent", "Continent")}
          {renderField("country", "Country")}
          {renderField("port", "Port")}
          {renderField("operation", "Operation")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Weight Certificate Data</Text></View>
          {renderField("vessel", "Vessel")}
          {renderField("voyage", "Voyage Number")}
          {renderField("commodity", "Commodity Described As")}
          {renderField("bl_figure", "Bill of Lading Figure")}
          {renderField("cargo_hold", "Cargo Hold")}
          {renderField("shipper", "Shipper")}
          {renderField("consignee", "Consignee")}
          {renderField("terminal", "Terminal")}
          {renderField("loading_port", "Loading Port")}
          {renderField("weight_determination", "Weight Determination")}
          {renderField("date", "Date", "date")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Loaded Quantity</Text></View>
          {renderField("quantity", "Metric Tons")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Remarks</Text></View>
          {renderField("remarks", "Remarks", "multiline")}

          <Pressable style={styles.actionButton} onPress={save}>
            <Text style={styles.actionButtonText}>{isReview ? "Guardar Cambios" : "Enviar a Revision"}</Text>
          </Pressable>
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          title="Buscar Servicio - Weight Certificate"
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(report) => {
            setForm((current) => ({ ...current, ...weightCertificateFormFromServiceReport(report) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function HoldsInspectionCertificateMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId?: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isReview = Boolean(initialReportId);
  const [form, setForm] = useState(emptyHoldsInspectionCertificateForm());
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editEnabled, setEditEnabled] = useState(!isReview);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!visible) return;
    setMessage("");
    setEditEnabled(!initialReportId);
    if (!initialReportId) {
      setForm(emptyHoldsInspectionCertificateForm());
      return;
    }
    setBusy(true);
    apiRequest<Record<string, unknown>>(`/vessel-holds-inspection-certificates/${initialReportId}`, { session })
      .then((payload) => {
        const next = emptyHoldsInspectionCertificateForm();
        Object.entries(payload).forEach(([key, value]) => {
          if (value === null || value === undefined) return;
          if (key in next && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) {
            next[key] = String(value);
          }
        });
        setForm(next);
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo cargar Holds Inspection Certificate."))
      .finally(() => setBusy(false));
  }, [initialReportId, session, visible]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function buildPayload() {
    return Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, value.trim() ? value.trim() : null])
    );
  }

  async function save() {
    if (!form.report_number.trim()) {
      setMessage("Seleccione un informe primero.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const endpoint = initialReportId ? `/vessel-holds-inspection-certificates/${initialReportId}` : "/vessel-holds-inspection-certificates";
      const result = await offlineApiRequest(endpoint, {
        method: initialReportId ? "PUT" : "POST",
        body: buildPayload(),
        session,
        offlineLabel: `${initialReportId ? "Actualizar" : "Crear"} Holds Inspection Certificate ${form.report_number}`
      });
      setMessage(isQueuedOffline(result) ? "Sin internet: Holds Certificate guardado en cache local para sincronizar." : initialReportId ? "Cambios guardados correctamente." : "Holds Certificate enviado a revision.");
      if (!isQueuedOffline(result)) await onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Holds Inspection Certificate.");
    } finally {
      setBusy(false);
    }
  }

  async function download(kind: "excel" | "pdf") {
    if (!initialReportId) {
      setMessage("Primero debe enviar el certificado a revision.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(
        `/vessel-holds-inspection-certificates/${initialReportId}/${kind}`,
        session,
        cleanFilePart(`Holds_Inspection_Certificate_${form.report_number || initialReportId}`) + `.${kind === "excel" ? "xlsx" : "pdf"}`
      );
      setMessage(`${kind.toUpperCase()} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `No se pudo generar ${kind.toUpperCase()}.`);
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" | "time" | "multiline" = "text") {
    if (type === "date") {
      if (!editEnabled) {
        return (
          <View key={key} style={styles.formField}>
            <Text style={styles.label}>{label}</Text>
            <TextInput editable={false} style={[styles.input, styles.readonlyInput]} value={form[key] || ""} />
          </View>
        );
      }
      return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    }
    if (type === "time") {
      return (
        <View key={key} style={styles.formField}>
          <Text style={styles.label}>{label}</Text>
          <TextInput
            editable={editEnabled}
            placeholder="HH:MM"
            style={[styles.input, !editEnabled && styles.readonlyInput]}
            value={form[key] || ""}
            onChangeText={(value) => setValue(key, value)}
          />
        </View>
      );
    }
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={editEnabled}
          style={[styles.input, type === "multiline" && styles.multilineInput, !editEnabled && styles.readonlyInput]}
          multiline={type === "multiline"}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>VESSEL HOLDS INSPECTION CERTIFICATE</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          <View style={styles.informesHomeActions}>
            {!isReview ? (
              <Pressable style={styles.actionButton} onPress={() => setServiceSelectorOpen(true)}>
                <Text style={styles.actionButtonText}>Seleccionar Informe</Text>
              </Pressable>
            ) : (
              <Pressable style={styles.actionButton} onPress={() => setEditEnabled(true)}>
                <Text style={styles.actionButtonText}>Editar</Text>
              </Pressable>
            )}
            {isReview ? (
              <>
                <Pressable style={styles.secondaryButton} onPress={() => download("excel")}><Text style={styles.secondaryButtonText}>Excel</Text></Pressable>
                <Pressable style={styles.secondaryButton} onPress={() => download("pdf")}><Text style={styles.secondaryButtonText}>PDF</Text></Pressable>
              </>
            ) : null}
          </View>

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Report Header</Text></View>
          {renderField("report_number", "Report Number")}
          {renderField("port", "Port")}
          {renderField("country", "Country")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Certificate Header</Text></View>
          {renderField("vessel", "Vessel")}
          {renderField("voyage", "Voyage")}
          {renderField("load_port", "Load Port")}
          {renderField("place", "Place")}
          {renderField("installation", "Installation")}
          {renderField("product", "Product")}
          {renderField("date", "Date", "date")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Survey Information</Text></View>
          {renderField("inspection_time", "Inspection Time", "time")}
          {renderField("vessel_holds", "Vessel Holds")}
          {renderField("vessel_holds_status", "Vessel Holds Status", "multiline")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Cargo</Text></View>
          {renderField("cargo_holds", "Cargo Holds")}
          {renderField("accepted_time", "Accepted Time", "time")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Location</Text></View>
          {renderField("place_location", "Place")}
          {renderField("place_date", "Date", "date")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Water Tightness / Hose Test</Text></View>
          {renderField("hose_test_start", "Hose Test Start", "time")}
          {renderField("hose_test_end", "Hose Test End", "time")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Remarks</Text></View>
          {renderField("remarks", "Remarks", "multiline")}
          {renderField("master_chief_officer", "MASTER / CHIEF OFFICER")}

          <Pressable style={styles.actionButton} onPress={save}>
            <Text style={styles.actionButtonText}>{isReview ? "Guardar Cambios" : "Enviar a Revision"}</Text>
          </Pressable>
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          title="Buscar Servicio - Holds Inspection Certificate"
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(report) => {
            setForm((current) => ({ ...current, ...holdsInspectionCertificateFormFromServiceReport(report) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function SamplingCertificateMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId?: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isReview = Boolean(initialReportId);
  const [form, setForm] = useState(emptySamplingCertificateForm());
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editEnabled, setEditEnabled] = useState(!isReview);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!visible) return;
    setMessage("");
    setEditEnabled(!initialReportId);
    if (!initialReportId) {
      setForm(emptySamplingCertificateForm());
      return;
    }
    setBusy(true);
    apiRequest<Record<string, unknown>>(`/sampling-certificates/${initialReportId}`, { session })
      .then((payload) => {
        const next = emptySamplingCertificateForm();
        Object.entries(payload).forEach(([key, value]) => {
          if (value === null || value === undefined) return;
          if (key in next && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) {
            next[key] = String(value);
          }
        });
        setForm(next);
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo cargar Sampling Certificate."))
      .finally(() => setBusy(false));
  }, [initialReportId, session, visible]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function buildPayload() {
    const payload: Record<string, unknown> = Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, value.trim() ? value.trim() : null])
    );
    payload.holds = Array.from({ length: 10 }, (_, index) => {
      const hold = index + 1;
      const seal = form[`hold_${hold}_seal`]?.trim();
      return seal ? { hold, seal } : null;
    }).filter(Boolean);
    return payload;
  }

  async function save() {
    if (!form.report_no.trim()) {
      setMessage("Seleccione un informe primero.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const endpoint = initialReportId ? `/sampling-certificates/${initialReportId}` : "/sampling-certificates";
      const result = await offlineApiRequest(endpoint, {
        method: initialReportId ? "PUT" : "POST",
        body: buildPayload(),
        session,
        offlineLabel: `${initialReportId ? "Actualizar" : "Crear"} Sampling Certificate ${form.report_no}`
      });
      setMessage(isQueuedOffline(result) ? "Sin internet: Sampling Certificate guardado en cache local para sincronizar." : initialReportId ? "Cambios guardados correctamente." : "Sampling Certificate enviado a revision.");
      if (!isQueuedOffline(result)) await onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Sampling Certificate.");
    } finally {
      setBusy(false);
    }
  }

  async function download(kind: "excel" | "pdf") {
    if (!initialReportId) {
      setMessage("Primero debe enviar el certificado a revision.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(
        `/sampling-certificates/${initialReportId}/${kind}`,
        session,
        cleanFilePart(`Sampling_Certificate_${form.report_no || initialReportId}`) + `.${kind === "excel" ? "xlsx" : "pdf"}`
      );
      setMessage(`${kind.toUpperCase()} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `No se pudo generar ${kind.toUpperCase()}.`);
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" | "time" | "multiline" = "text") {
    if (type === "date") {
      if (!editEnabled) {
        return (
          <View key={key} style={styles.formField}>
            <Text style={styles.label}>{label}</Text>
            <TextInput editable={false} style={[styles.input, styles.readonlyInput]} value={form[key] || ""} />
          </View>
        );
      }
      return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    }
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={editEnabled}
          placeholder={type === "time" ? "HH:MM" : undefined}
          style={[styles.input, type === "multiline" && styles.multilineInput, !editEnabled && styles.readonlyInput]}
          multiline={type === "multiline"}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>SAMPLING CERTIFICATE</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          <View style={styles.informesHomeActions}>
            {!isReview ? (
              <Pressable style={styles.actionButton} onPress={() => setServiceSelectorOpen(true)}>
                <Text style={styles.actionButtonText}>SELECT REPORT</Text>
              </Pressable>
            ) : (
              <Pressable style={styles.actionButton} onPress={() => setEditEnabled(true)}>
                <Text style={styles.actionButtonText}>Editar</Text>
              </Pressable>
            )}
            {isReview ? (
              <>
                <Pressable style={styles.secondaryButton} onPress={() => download("excel")}><Text style={styles.secondaryButtonText}>Excel</Text></Pressable>
                <Pressable style={styles.secondaryButton} onPress={() => download("pdf")}><Text style={styles.secondaryButtonText}>PDF</Text></Pressable>
              </>
            ) : null}
          </View>

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Report Header</Text></View>
          {renderField("report_no", "Report No")}
          {renderField("port", "Port")}
          {renderField("country", "Country")}
          {renderField("customer", "Customer")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Sampling Certificate</Text></View>
          {renderField("certificate_no", "Certificate No")}
          {renderField("vessel", "Vessel")}
          {renderField("date", "Date", "date")}
          {renderField("place", "Place")}
          {renderField("cargo", "Cargo")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Holds Inspected</Text></View>
          {renderField("holds_inspected", "Holds")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Holds and Seal Numbers</Text></View>
          {Array.from({ length: 10 }, (_, index) => {
            const hold = index + 1;
            return renderField(`hold_${hold}_seal`, `HOLD ${hold}`);
          })}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Observations</Text></View>
          {renderField("observations", "Observations", "multiline")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Closing</Text></View>
          {renderField("closing_date", "Date", "date")}
          {renderField("closing_time", "Time", "time")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Signed By</Text></View>
          {renderField("master", "Master / Chief Officer")}

          <Pressable style={styles.actionButton} onPress={save}>
            <Text style={styles.actionButtonText}>{isReview ? "Guardar Cambios" : "Enviar a Revision"}</Text>
          </Pressable>
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          title="Buscar Servicio - Sampling Certificate"
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(report) => {
            setForm((current) => ({ ...current, ...samplingCertificateFormFromServiceReport(report) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function SealingCertificateMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId?: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isReview = Boolean(initialReportId);
  const [form, setForm] = useState(emptySealingCertificateForm());
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editEnabled, setEditEnabled] = useState(!isReview);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!visible) return;
    setMessage("");
    setEditEnabled(!initialReportId);
    if (!initialReportId) {
      setForm(emptySealingCertificateForm());
      return;
    }
    setBusy(true);
    apiRequest<Record<string, unknown>>(`/sealing-certificates/${initialReportId}`, { session })
      .then((payload) => {
        const next = emptySealingCertificateForm();
        Object.entries(payload).forEach(([key, value]) => {
          if (value === null || value === undefined) return;
          if (key in next && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) {
            next[key] = String(value);
          }
        });
        setForm(next);
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo cargar Sealing Certificate."))
      .finally(() => setBusy(false));
  }, [initialReportId, session, visible]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function buildPayload() {
    return Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, value.trim() ? value.trim() : null])
    );
  }

  async function save() {
    if (!form.report_no.trim()) {
      setMessage("Seleccione un informe primero.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const endpoint = initialReportId ? `/sealing-certificates/${initialReportId}` : "/sealing-certificates";
      const result = await offlineApiRequest(endpoint, {
        method: initialReportId ? "PUT" : "POST",
        body: buildPayload(),
        session,
        offlineLabel: `${initialReportId ? "Actualizar" : "Crear"} Sealing Certificate ${form.report_no}`
      });
      setMessage(isQueuedOffline(result) ? "Sin internet: Sealing Certificate guardado en cache local para sincronizar." : initialReportId ? "Cambios guardados correctamente." : "Sealing Certificate enviado a revision.");
      if (!isQueuedOffline(result)) await onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Sealing Certificate.");
    } finally {
      setBusy(false);
    }
  }

  async function download(kind: "excel" | "pdf") {
    if (!initialReportId) {
      setMessage("Primero debe enviar el certificado a revision.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(
        `/sealing-certificates/${initialReportId}/${kind}`,
        session,
        cleanFilePart(`Sealing_Certificate_${form.report_no || initialReportId}`) + `.${kind === "excel" ? "xlsx" : "pdf"}`
      );
      setMessage(`${kind.toUpperCase()} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `No se pudo generar ${kind.toUpperCase()}.`);
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" | "time" | "multiline" = "text") {
    if (type === "date") {
      if (!editEnabled) {
        return (
          <View key={key} style={styles.formField}>
            <Text style={styles.label}>{label}</Text>
            <TextInput editable={false} style={[styles.input, styles.readonlyInput]} value={form[key] || ""} />
          </View>
        );
      }
      return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    }
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={editEnabled}
          placeholder={type === "time" ? "HH:MM" : undefined}
          style={[styles.input, type === "multiline" && styles.multilineInput, !editEnabled && styles.readonlyInput]}
          multiline={type === "multiline"}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>SEALING CERTIFICATE</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          <View style={styles.informesHomeActions}>
            {!isReview ? (
              <Pressable style={styles.actionButton} onPress={() => setServiceSelectorOpen(true)}>
                <Text style={styles.actionButtonText}>SELECT REPORT</Text>
              </Pressable>
            ) : (
              <Pressable style={styles.actionButton} onPress={() => setEditEnabled(true)}>
                <Text style={styles.actionButtonText}>Editar</Text>
              </Pressable>
            )}
            {isReview ? (
              <>
                <Pressable style={styles.secondaryButton} onPress={() => download("excel")}><Text style={styles.secondaryButtonText}>Excel</Text></Pressable>
                <Pressable style={styles.secondaryButton} onPress={() => download("pdf")}><Text style={styles.secondaryButtonText}>PDF</Text></Pressable>
              </>
            ) : null}
          </View>

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Report Header</Text></View>
          {renderField("report_no", "Report No")}
          {renderField("port", "Port")}
          {renderField("country", "Country")}
          {renderField("customer", "Customer")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Sealing Certificate</Text></View>
          {renderField("certificate_no", "Certificate No")}
          {renderField("vessel", "Vessel")}
          {renderField("date", "Date", "date")}
          {renderField("location", "Location")}
          {renderField("cargo", "Cargo")}

          <View style={styles.summaryBox}>
            <Text style={styles.cardTitle}>Seal Placement</Text>
            <Text style={styles.helperText}>The seals of hatch covers were placed in Port/Std. Side positions.</Text>
          </View>

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Holds</Text></View>
          {Array.from({ length: 6 }, (_, index) => {
            const hold = index + 1;
            return (
              <View key={hold} style={styles.summaryBox}>
                <Text style={styles.fieldKey}>HOLD #{hold}</Text>
                {renderField(`hold_${hold}_fwd_escape`, "FWD ESCAPE")}
                {renderField(`hold_${hold}_fwd_aft_hatch`, "FWD/AFT HATCH")}
                {renderField(`hold_${hold}_aft_escape`, "AFT ESCAPE")}
              </View>
            );
          })}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Remarks</Text></View>
          {renderField("remarks", "Remarks", "multiline")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Witnessed / Closing</Text></View>
          {renderField("chief_officer", "Chief Officer")}
          {renderField("closing_date", "Date", "date")}
          {renderField("closing_time", "Time", "time")}

          <Pressable style={styles.actionButton} onPress={save}>
            <Text style={styles.actionButtonText}>{isReview ? "Guardar Cambios" : "Enviar a Revision"}</Text>
          </Pressable>
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          title="Buscar Servicio - Sealing Certificate"
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(report) => {
            setForm((current) => ({ ...current, ...sealingCertificateFormFromServiceReport(report) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function LashingCertificateMobileModal({
  visible,
  session,
  initialReportId,
  onClose,
  onSaved
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  initialReportId?: string | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isReview = Boolean(initialReportId);
  const [form, setForm] = useState(emptyLashingCertificateForm());
  const [serviceSelectorOpen, setServiceSelectorOpen] = useState(false);
  const [editEnabled, setEditEnabled] = useState(!isReview);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!visible) return;
    setMessage("");
    setEditEnabled(!initialReportId);
    if (!initialReportId) {
      setForm(emptyLashingCertificateForm());
      return;
    }
    setBusy(true);
    apiRequest<Record<string, unknown>>(`/lashing-certificates/${initialReportId}`, { session })
      .then((payload) => {
        const next = emptyLashingCertificateForm();
        Object.entries(payload).forEach(([key, value]) => {
          if (value === null || value === undefined) return;
          if (key in next && (typeof value === "string" || typeof value === "number" || typeof value === "boolean")) {
            next[key] = String(value);
          }
        });
        if (!next.status) next.status = "Draft";
        setForm(next);
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudo cargar Lashing Certificate."))
      .finally(() => setBusy(false));
  }, [initialReportId, session, visible]);

  function setValue(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function buildPayload() {
    const payload = Object.fromEntries(
      Object.entries(form).map(([key, value]) => [key, value.trim() ? value.trim() : null])
    ) as Record<string, unknown>;
    payload.status = form.status?.trim() || "Draft";
    return payload;
  }

  async function save() {
    if (!form.report_no.trim()) {
      setMessage("Seleccione un informe primero.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const endpoint = initialReportId ? `/lashing-certificates/${initialReportId}` : "/lashing-certificates/";
      const result = await offlineApiRequest(endpoint, {
        method: initialReportId ? "PUT" : "POST",
        body: buildPayload(),
        session,
        offlineLabel: `${initialReportId ? "Actualizar" : "Crear"} Lashing Certificate ${form.report_no}`
      });
      setMessage(isQueuedOffline(result) ? "Sin internet: Lashing Certificate guardado en cache local para sincronizar." : initialReportId ? "Cambios guardados correctamente." : "Lashing Certificate enviado a revision.");
      if (!isQueuedOffline(result)) await onSaved();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar Lashing Certificate.");
    } finally {
      setBusy(false);
    }
  }

  async function download(kind: "word" | "pdf") {
    if (!initialReportId) {
      setMessage("Primero debe enviar el certificado a revision.");
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      await downloadSessionFile(
        `/lashing-certificates/${initialReportId}/${kind}`,
        session,
        cleanFilePart(`Lashing_Certificate_${form.report_no || initialReportId}`) + `.${kind === "word" ? "docx" : "pdf"}`
      );
      setMessage(`${kind.toUpperCase()} generado correctamente.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : `No se pudo generar ${kind.toUpperCase()}.`);
    } finally {
      setBusy(false);
    }
  }

  function renderField(key: string, label: string, type: "text" | "date" = "text") {
    if (type === "date") {
      if (!editEnabled) {
        return (
          <View key={key} style={styles.formField}>
            <Text style={styles.label}>{label}</Text>
            <TextInput editable={false} style={[styles.input, styles.readonlyInput]} value={form[key] || ""} />
          </View>
        );
      }
      return <DateField key={key} label={label} value={form[key] || ""} onChange={(value) => setValue(key, value)} />;
    }
    return (
      <View key={key} style={styles.formField}>
        <Text style={styles.label}>{label}</Text>
        <TextInput
          editable={editEnabled}
          style={[styles.input, !editEnabled && styles.readonlyInput]}
          value={form[key] || ""}
          onChangeText={(value) => setValue(key, value)}
        />
      </View>
    );
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>LASHING CERTIFICATE</Text>
          <Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          <View style={styles.informesHomeActions}>
            {!isReview ? (
              <Pressable style={styles.actionButton} onPress={() => setServiceSelectorOpen(true)}>
                <Text style={styles.actionButtonText}>SELECT REPORT</Text>
              </Pressable>
            ) : (
              <Pressable style={styles.actionButton} onPress={() => setEditEnabled(true)}>
                <Text style={styles.actionButtonText}>Editar</Text>
              </Pressable>
            )}
            {isReview ? (
              <>
                <Pressable style={styles.secondaryButton} onPress={() => download("word")}><Text style={styles.secondaryButtonText}>Word</Text></Pressable>
                <Pressable style={styles.secondaryButton} onPress={() => download("pdf")}><Text style={styles.secondaryButtonText}>PDF</Text></Pressable>
              </>
            ) : null}
          </View>

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Report Header</Text></View>
          {renderField("report_no", "Report No")}
          {renderField("customer", "Customer")}
          {renderField("port", "Port")}
          {renderField("country", "Country")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Lashing Details</Text></View>
          {renderField("flat_rack_container", "Flat Rack Container No")}
          {renderField("cargo_type", "Type of Cargo")}
          {renderField("lashing_material", "Lashing Material")}
          {renderField("date", "Date", "date")}
          {renderField("place", "Place")}

          <View style={styles.summaryBox}><Text style={styles.cardTitle}>Ratchet Lashings</Text></View>
          {renderField("ratchet_quantity", "Ratchet Lashing Quantity")}
          {renderField("where_carry_out", "Where Was Carry Out")}
          {renderField("completion_date", "Completion Date", "date")}

          <Pressable style={styles.actionButton} onPress={save}>
            <Text style={styles.actionButtonText}>{isReview ? "Guardar Cambios" : "Enviar a Revision"}</Text>
          </Pressable>
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
        <DraftServiceSelectorModal
          visible={serviceSelectorOpen}
          session={session}
          title="Buscar Servicio - Lashing Certificate"
          onClose={() => setServiceSelectorOpen(false)}
          onSelect={(report) => {
            setForm((current) => ({ ...current, ...lashingCertificateFormFromServiceReport(report) }));
            setServiceSelectorOpen(false);
          }}
        />
      </SafeAreaView>
    </Modal>
  );
}

function DraftServiceSelectorModal({
  visible,
  session,
  onClose,
  onSelect,
  title = "Buscar Servicio - Draft Survey"
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
  onSelect: (report: Record<string, unknown>) => void;
  title?: string;
}) {
  const [filters, setFilters] = useState({ year: "", month: "", continente: "", pais: "", puerto: "", cliente: "", operacion: "" });
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const selectedRow = selected === null ? null : rows[selected] || null;
  const options = {
    years: [...new Set(rows.map((row) => formatValue(row.fecha_inicio).slice(0, 4)).filter((item) => item && item !== "-"))],
    months: Array.from({ length: 12 }, (_, index) => String(index + 1).padStart(2, "0")),
    continentes: [...new Set(rows.map((row) => formatValue(row.continente)).filter((item) => item !== "-"))],
    paises: [...new Set(rows.map((row) => formatValue(row.pais)).filter((item) => item !== "-"))],
    puertos: [...new Set(rows.map((row) => formatValue(row.puerto)).filter((item) => item !== "-"))],
    clientes: [...new Set(rows.map((row) => formatValue(row.cliente)).filter((item) => item !== "-"))],
    operaciones: [...new Set(rows.map((row) => formatValue(row.operacion)).filter((item) => item !== "-"))]
  };

  async function load(nextFilters = filters) {
    setBusy(true);
    setMessage("");
    try {
      const params = new URLSearchParams();
      Object.entries(nextFilters).forEach(([key, value]) => { if (value) params.set(key, value); });
      const payload = await apiRequest(`/draft-survey/servicios/filter${params.toString() ? `?${params.toString()}` : ""}`, { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar servicios Draft.");
    } finally {
      setBusy(false);
    }
  }

  function updateFilter(key: keyof typeof filters, value: string) {
    const next = { ...filters, [key]: value };
    setFilters(next);
    load(next);
  }

  useEffect(() => {
    if (!visible) return;
    const initial = { year: "", month: "", continente: "", pais: "", puerto: "", cliente: "", operacion: "" };
    setFilters(initial);
    load(initial);
  }, [visible]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}><Text style={styles.modalTitle}>{title}</Text><Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable></View>
        <ScrollView contentContainerStyle={styles.modalBody}>
          <SelectField label="Anio" value={filters.year} options={options.years} onChange={(value) => updateFilter("year", value)} />
          <SelectField label="Mes" value={filters.month} options={options.months} onChange={(value) => updateFilter("month", value)} />
          <SelectField label="Continente" value={filters.continente} options={options.continentes} onChange={(value) => updateFilter("continente", value)} />
          <SelectField label="Pais" value={filters.pais} options={options.paises} onChange={(value) => updateFilter("pais", value)} />
          <SelectField label="Puerto" value={filters.puerto} options={options.puertos} onChange={(value) => updateFilter("puerto", value)} />
          <SelectField label="Cliente" value={filters.cliente} options={options.clientes} onChange={(value) => updateFilter("cliente", value)} />
          <SelectField label="Operacion" value={filters.operacion} options={options.operaciones} onChange={(value) => updateFilter("operacion", value)} />
          <View style={styles.informesHomeActions}>
            <Pressable style={styles.actionButton} onPress={() => load(filters)}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
            <Pressable style={styles.modalClose} onPress={() => selectedRow ? onSelect(selectedRow) : setMessage("Seleccione un servicio.")}><Text style={styles.modalCloseText}>Seleccionar</Text></Pressable>
          </View>
          <Text style={styles.tableCount}>{rows.length} servicios</Text>
          <HRMiniTable rows={rows} columns={["num_informe", "buque_contenedor", "cliente", "continente", "pais", "puerto", "operacion", "fecha_inicio"]} selectedIndex={selected} onSelect={setSelected} />
          {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
          {message ? <Text style={styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

function DraftExistingSelectorModal({
  visible,
  session,
  onClose,
  onSelect
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
  onSelect: (draftReportNumber: string) => void;
}) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [filters, setFilters] = useState({ search: "", continent: "", country: "", year: "", month: "", port: "", client: "" });
  const [selected, setSelected] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const filtered = rows.filter((row) => {
    for (const key of ["continent", "country", "year", "month", "port", "client"] as const) {
      if (filters[key] && formatValue(row[key]).toLowerCase() !== filters[key].toLowerCase()) return false;
    }
    if (!filters.search.trim()) return true;
    const needle = filters.search.toLowerCase();
    return ["draft_report_number", "client", "port", "country"].some((key) => formatValue(row[key]).toLowerCase().includes(needle));
  });
  const selectedRow = selected === null ? null : filtered[selected] || null;

  async function load() {
    setBusy(true);
    setMessage("");
    try {
      const payload = await apiRequest("/draft-survey-headers/", { session });
      setRows(rowsFromAny(payload));
      setSelected(null);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron cargar Drafts previos.");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (!visible) return;
    setFilters({ search: "", continent: "", country: "", year: "", month: "", port: "", client: "" });
    load();
  }, [visible]);

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}><Text style={styles.modalTitle}>Select Existing Draft Survey</Text><Pressable style={styles.modalClose} onPress={onClose}><Text style={styles.modalCloseText}>Cerrar</Text></Pressable></View>
        <ScrollView contentContainerStyle={styles.modalBody}>
          <Text style={styles.label}>Buscar</Text>
          <TextInput style={styles.input} value={filters.search} onChangeText={(search) => setFilters((current) => ({ ...current, search }))} />
          {(["continent", "country", "year", "month", "port", "client"] as const).map((key) => (
            <View key={key} style={styles.formField}>
              <Text style={styles.label}>{key}</Text>
              <TextInput style={styles.input} value={filters[key]} onChangeText={(value) => setFilters((current) => ({ ...current, [key]: value }))} />
            </View>
          ))}
          <View style={styles.informesHomeActions}>
            <Pressable style={styles.actionButton} onPress={load}><Text style={styles.actionButtonText}>Buscar</Text></Pressable>
            <Pressable style={styles.modalClose} onPress={() => {
              const draft = formatValue(selectedRow?.draft_report_number);
              if (draft === "-") setMessage("Seleccione un Draft.");
              else onSelect(draft);
            }}><Text style={styles.modalCloseText}>Cargar Draft</Text></Pressable>
          </View>
          <Text style={styles.tableCount}>{filtered.length} drafts</Text>
          <HRMiniTable rows={filtered} columns={["draft_report_number", "client", "port", "country", "continent", "year", "month", "status"]} selectedIndex={selected} onSelect={setSelected} />
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
  "+1242",
  "+1246",
  "+1264",
  "+1268",
  "+1284",
  "+1340",
  "+1345",
  "+1441",
  "+1473",
  "+1649",
  "+1664",
  "+1670",
  "+1671",
  "+1684",
  "+1721",
  "+1758",
  "+1767",
  "+1784",
  "+1787",
  "+1809",
  "+1829",
  "+1849",
  "+1868",
  "+1869",
  "+1876",
  "+1939",
  "+51",
  "+52",
  "+53",
  "+54",
  "+55",
  "+56",
  "+57",
  "+58",
  "+500",
  "+501",
  "+502",
  "+503",
  "+504",
  "+505",
  "+506",
  "+507",
  "+509",
  "+590",
  "+591",
  "+592",
  "+593",
  "+594",
  "+595",
  "+596",
  "+597",
  "+598",
  "+599"
];
const PHONE_PREFIXES_SHORT = PHONE_PREFIXES_FULL;
const PHONE_PREFIXES_EMPLOYEE = PHONE_PREFIXES_FULL;
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

const COMPANY_FISCAL_FIELDS = [
  { key: "company_name", label: "Empresa" },
  { key: "legal_name", label: "Razon social" },
  { key: "trade_name", label: "Nombre comercial" },
  { key: "tax_id", label: "Cedula juridica" },
  { key: "economic_activity", label: "Actividad economica" },
  { key: "phone", label: "Telefono" },
  { key: "billing_email", label: "Correo facturacion" },
  { key: "email", label: "Correo general" },
  { key: "country", label: "Pais" },
  { key: "province", label: "Provincia" },
  { key: "canton", label: "Canton" },
  { key: "district", label: "Distrito" },
  { key: "address", label: "Direccion" },
  { key: "notes", label: "Notas" }
];

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

function csvEscape(value: unknown) {
  const text = formatValue(value) === "-" ? "" : formatValue(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function buildMasterCsvTemplate(config: MasterFormConfig) {
  const headers = config.fields.map((field) => field.key);
  const labels = config.fields.map((field) => field.label);
  return `${headers.map(csvEscape).join(",")}\n${labels.map(csvEscape).join(",")}\n`;
}

function splitCsvLine(line: string) {
  const cells: string[] = [];
  let current = "";
  let quoted = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];
    if (char === '"' && quoted && next === '"') {
      current += '"';
      index += 1;
      continue;
    }
    if (char === '"') {
      quoted = !quoted;
      continue;
    }
    if (char === "," && !quoted) {
      cells.push(current);
      current = "";
      continue;
    }
    current += char;
  }
  cells.push(current);
  return cells.map((cell) => cell.trim());
}

function parseMasterCsv(content: string, config: MasterFormConfig) {
  const lines = content
    .replace(/^\uFEFF/, "")
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return [];

  const headers = splitCsvLine(lines[0]);
  const validKeys = new Set(config.fields.map((field) => field.key));
  const dataLines = lines.slice(1).filter((line) => {
    const cells = splitCsvLine(line);
    return cells.some((cell) => cell.trim()) && !cells.every((cell, index) => cell === config.fields[index]?.label);
  });

  return dataLines.map((line) => {
    const cells = splitCsvLine(line);
    const row: Record<string, string> = {};
    headers.forEach((header, index) => {
      const cleanHeader = header.trim();
      if (validKeys.has(cleanHeader)) row[cleanHeader] = cells[index] || "";
    });
    return row;
  });
}

async function importMasterRecordsFromCsv({
  section,
  config,
  session
}: {
  section: AppSection;
  config: MasterFormConfig;
  session: Session;
}) {
  const table = section.table;
  if (!table?.createEndpoint) {
    throw new Error("Esta seccion no permite carga desde plantilla.");
  }

  const picked = await DocumentPicker.getDocumentAsync({
    type: ["text/csv", "text/comma-separated-values", "text/plain", "application/vnd.ms-excel"],
    multiple: false,
    copyToCacheDirectory: true
  });
  if (picked.canceled || !picked.assets?.length) return null;

  const content = await FileSystem.readAsStringAsync(picked.assets[0].uri);
  const records = parseMasterCsv(content, config).filter((row) => Object.values(row).some((value) => String(value || "").trim()));
  if (!records.length) {
    throw new Error("El archivo no contiene lineas para cargar.");
  }

  let created = 0;
  let updated = 0;
  const errors: string[] = [];
  for (const record of records) {
    const payload = { ...normalizeMasterPayload(section.key, record), company_code: session.company_code || DEFAULT_COMPANY.code };
    const id = String(record[config.codeKey] || "").trim();
    try {
      if (id && table.updateEndpoint) {
        await apiRequest(endpointWithId(table.updateEndpoint, id), { method: "PUT", body: payload, session });
        updated += 1;
      } else {
        await apiRequest(table.createEndpoint, { method: "POST", body: payload, session });
        created += 1;
      }
    } catch (err) {
      errors.push(`${id || config.title}: ${err instanceof Error ? err.message : "No se pudo cargar."}`);
    }
  }
  return { created, updated, errors };
}

async function shareMasterCsvTemplate(config: MasterFormConfig, session: Session) {
  const filename = `Formulario_MasterData_${config.title}_${session.company_code || DEFAULT_COMPANY.code}.csv`;
  const csv = buildMasterCsvTemplate(config);
  await Share.share({ title: filename, message: `${filename}\n\n${csv}` });
}

function MasterDataHomeActions({
  module,
  session,
  onReload
}: {
  module: AppModule;
  session: Session;
  onReload: () => void;
}) {
  const sections = module.sections.filter((section) => section.table && MASTER_FORMS[section.key]);
  const [entityKey, setEntityKey] = useState(sections[0]?.key || "clientes");
  const [companyFiscalOpen, setCompanyFiscalOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const selectedSection = sections.find((section) => section.key === entityKey) || sections[0];
  const selectedConfig = selectedSection ? MASTER_FORMS[selectedSection.key] : null;

  async function exportForm() {
    if (!selectedConfig) return;
    setBusy(true);
    setMessage("");
    try {
      await shareMasterCsvTemplate(selectedConfig, session);
      setMessage("Plantilla exportada.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo exportar.");
    } finally {
      setBusy(false);
    }
  }

  async function importForm() {
    if (!selectedSection || !selectedConfig) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await importMasterRecordsFromCsv({ section: selectedSection, config: selectedConfig, session });
      if (!result) return;
      onReload();
      setMessage(`Creados: ${result.created}. Actualizados: ${result.updated}.${result.errors.length ? ` Errores: ${result.errors.slice(0, 3).join(" | ")}` : ""}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <View style={styles.masterMobilePanel}>
      <Text style={styles.cardTitle}>Acciones Master Data</Text>
      <Text style={styles.helperText}>Visible desde el modulo. Empresa activa: {session.company_name || DEFAULT_COMPANY.name}.</Text>
      <SelectField
        label="Formulario"
        value={selectedSection?.label || ""}
        options={sections.map((section) => section.label)}
        onChange={(label) => {
          const next = sections.find((section) => section.label === label);
          if (next) setEntityKey(next.key);
        }}
      />
      <View style={styles.masterMobileActions}>
        <Pressable style={styles.actionButton} onPress={exportForm} disabled={busy}>
          <Text style={styles.actionButtonText}>Exportar formulario</Text>
        </Pressable>
        <Pressable style={styles.actionButton} onPress={importForm} disabled={busy}>
          <Text style={styles.actionButtonText}>Cargar formulario</Text>
        </Pressable>
        <Pressable style={styles.actionButton} onPress={() => setCompanyFiscalOpen(true)} disabled={busy}>
          <Text style={styles.actionButtonText}>Tarjeta fiscal</Text>
        </Pressable>
      </View>
      {busy ? <ActivityIndicator color={BLUE} style={styles.loader} /> : null}
      {message ? <Text style={message.includes("Errores") ? styles.error : styles.helperText}>{message}</Text> : null}
      <CompanyFiscalModal visible={companyFiscalOpen} session={session} onClose={() => setCompanyFiscalOpen(false)} />
    </View>
  );
}

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
  const [companyFiscalOpen, setCompanyFiscalOpen] = useState(false);
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
      await apiRequest(endpointWithId(endpoint, id), {
        method,
        body: { ...form, company_code: session.company_code || DEFAULT_COMPANY.code },
        session
      });
      setModalMode(null);
      onReload();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo guardar.");
    } finally {
      setBusy(false);
    }
  }

  async function exportMasterForm() {
    if (!masterForm) return;
    setMessage("");
    try {
      await shareMasterCsvTemplate(masterForm, session);
      setMessage("Plantilla generada para llenar y cargar de nuevo.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo exportar la plantilla.");
    }
  }

  async function importMasterForm() {
    if (!masterForm) return;
    setMessage("");
    try {
      setBusy(true);
      const result = await importMasterRecordsFromCsv({ section, config: masterForm, session });
      if (!result) return;
      onReload();
      setMessage(`Creados: ${result.created}. Actualizados: ${result.updated}.${result.errors.length ? ` Errores: ${result.errors.slice(0, 3).join(" | ")}` : ""}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudo cargar el archivo.");
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
      {masterForm ? (
        <View style={styles.masterMobilePanel}>
          <Text style={styles.cardTitle}>Acciones Master Data</Text>
          <Text style={styles.helperText}>Plantillas, carga masiva y datos fiscales de {session.company_name || DEFAULT_COMPANY.name}.</Text>
          <View style={styles.masterMobileActions}>
            <Pressable style={styles.actionButton} onPress={exportMasterForm}>
              <Text style={styles.actionButtonText}>Exportar form</Text>
            </Pressable>
            <Pressable style={styles.actionButton} onPress={importMasterForm}>
              <Text style={styles.actionButtonText}>Cargar form</Text>
            </Pressable>
            <Pressable style={styles.actionButton} onPress={() => setCompanyFiscalOpen(true)}>
              <Text style={styles.actionButtonText}>Datos fiscales</Text>
            </Pressable>
          </View>
        </View>
      ) : null}
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
      <CompanyFiscalModal
        visible={companyFiscalOpen}
        session={session}
        onClose={() => setCompanyFiscalOpen(false)}
      />
    </View>
  );
}

function CompanyFiscalModal({
  visible,
  session,
  onClose
}: {
  visible: boolean;
  session: NonNullable<ReturnType<typeof useAuth>["session"]>;
  onClose: () => void;
}) {
  const [form, setForm] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!visible) return;
    setBusy(true);
    setMessage("");
    apiRequest<Record<string, unknown>>("/companies/current", { session })
      .then((payload) => {
        const next = Object.fromEntries(COMPANY_FISCAL_FIELDS.map((field) => [field.key, formatValue(payload[field.key]) === "-" ? "" : formatValue(payload[field.key])]));
        setForm(next);
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : "No se pudieron cargar los datos fiscales."))
      .finally(() => setBusy(false));
  }, [session, visible]);

  function update(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function isLongFiscalField(key: string) {
    return ["company_name", "legal_name", "economic_activity", "billing_email", "email", "address", "notes"].includes(key);
  }

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await apiRequest(`/companies/${encodeURIComponent(session.company_code || DEFAULT_COMPANY.code)}`, {
        method: "PUT",
        session,
        body: form
      });
      setMessage("Datos fiscales guardados.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "No se pudieron guardar los datos fiscales.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <SafeAreaView style={styles.modalScreen}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Datos fiscales</Text>
          <Pressable style={styles.modalClose} onPress={onClose}>
            <Text style={styles.modalCloseText}>Cerrar</Text>
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.modalBody} keyboardShouldPersistTaps="handled">
          {COMPANY_FISCAL_FIELDS.map((field) => (
            <View key={field.key} style={styles.formField}>
              <Text style={styles.label}>{field.label}</Text>
              <TextInput
                value={form[field.key] || ""}
                onChangeText={(value) => update(field.key, value)}
                style={[styles.input, isLongFiscalField(field.key) && styles.longTextInput]}
                multiline={isLongFiscalField(field.key)}
                textAlignVertical={isLongFiscalField(field.key) ? "top" : "center"}
              />
            </View>
          ))}
          <PrimaryButton label="Guardar datos fiscales" loading={busy} onPress={save} />
          {message ? <Text style={message.includes("guardados") ? styles.helperText : styles.error}>{message}</Text> : null}
        </ScrollView>
      </SafeAreaView>
    </Modal>
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
                  {formatDateColumnValue(column, row[column])}
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

function formatDateColumnValue(column: string, value: unknown) {
  const raw = formatValue(value);
  if (raw === "-") return raw;
  const key = column.toLowerCase();
  const looksLikeDateColumn = key === "date" || key.startsWith("fecha_") || key.endsWith("_date");
  if (!looksLikeDateColumn) return raw;
  const date = parseYmd(raw.slice(0, 10));
  return date ? longEnglishDate(formatYmd(date)) : raw;
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
    month: "long",
    day: "numeric",
    year: "numeric"
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
      const prefix = companyPrefix(session.company_code);
      const fallbackCode = config.codeSuffix ? `${prefix}-0001-${config.codeSuffix}` : config.fallbackCode.replace(/^MSL/, prefix);
      nextForm[config.codeKey] = fallbackCode;
      if (config.ultimoEndpoint && config.codePrefix && config.codeSuffix) {
        apiRequest<{ ultimo?: number }>(config.ultimoEndpoint, { session })
          .then((payload) => {
            const nextNumber = Number(payload.ultimo || 0) + 1;
            setForm((current) => ({
              ...current,
              [config.codeKey]: `${prefix}-${String(nextNumber).padStart(4, "0")}-${config.codeSuffix}`
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
        body: { ...normalizeMasterPayload(sectionKey, form), company_code: session.company_code || DEFAULT_COMPANY.code }
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
  const currentYear = today.getFullYear();
  return Array.from({ length: 12 }, (_, index) => `${currentYear}-${String(index + 1).padStart(2, "0")}`);
}

function currentAccountingPeriod() {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
}

function previousAccountingPeriod() {
  const today = new Date();
  const previous = new Date(today.getFullYear(), today.getMonth() - 1, 1);
  return `${previous.getFullYear()}-${String(previous.getMonth() + 1).padStart(2, "0")}`;
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
        params.set("period", form.period || currentAccountingPeriod());
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
            `Sin asientos en ${form.search_mode === "RANGE" ? `${form.period_from} a ${form.period_to}` : form.period || currentAccountingPeriod()}. Ultimo periodo con asientos: ${latest.period} (${latest.count}).`
          );
        } else {
          onMessage("No existen asientos contables para la empresa y filtros seleccionados.");
        }
      } else if (sectionKey === "accounting") {
        onMessage(`Asientos cargados: ${nextRows.length} linea(s).`);
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
      const data = await withTimeout(
        apiRequest<Record<string, unknown>>("/exchange-rate/today", { session }),
        12000,
        "Tipo de cambio tardando demasiado. Puede buscar asientos sin TC."
      );
      const rate = Number(data.rate || 0);
      setForm((current) => ({
        ...current,
        tc_rate: Number.isFinite(rate) && rate > 0 ? rate.toFixed(2) : formatValue(data.rate),
        tc_date: formatValue(data.date)
      }));
      onMessage("Tipo de cambio cargado.");
    } catch (err) {
      onMessage(err instanceof Error ? err.message : "No se pudo obtener el tipo de cambio. Puede buscar asientos sin TC.");
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
        `/closing/period/status?company_code=${encodeURIComponent(session.company_code || DEFAULT_COMPANY.code)}&fiscal_year=${year}&period=${Number(month)}&ledger=0L`,
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
        params.set("period", form.period || currentAccountingPeriod());
      }
      if (form.origin && form.origin !== "TODOS") params.set("origin", form.origin);
      if (form.account && form.account !== "TODOS") params.set("account_code", form.account.split(" - ")[0]);
      params.set("company_code", session.company_code || DEFAULT_COMPANY.code);

      const format = form.report_format === "PDF" ? "pdf" : "excel";
      const extension = form.report_format === "PDF" ? "pdf" : "xlsx";
      const filename = cleanFilePart(`${label}.${extension}`);
      onMessage("");
      try {
        await downloadSessionFile(`/accounting/reports/${format}?${params.toString()}`, session, filename);
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
            <SelectField label="Periodo" value={form.period || currentAccountingPeriod()} options={accountingPeriods} onChange={(value) => setValue("period", value)} />
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
      const result = await offlineApiRequest("/servicios/add", {
        method: "POST",
        session,
        offlineLabel: `Crear Servicio ${form.cliente || form.buque_contenedor}`,
        body: {
          ...form,
          honorarios: Number(String(form.honorarios || "0").replace(",", "")),
          costo_operativo: Number(String(form.costo_operativo || "0").replace(",", ""))
        }
      });
      if (isQueuedOffline(result)) {
        setMessage("Sin internet: servicio guardado en cache local para sincronizar.");
      } else {
        onSaved();
      }
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
          <DateField label="Fecha inicio" value={form.fecha_inicio} onChange={(value) => update("fecha_inicio", value)} />
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
    const cleanField = (value: unknown) => {
      const formatted = formatValue(value);
      return formatted === "-" ? "" : formatted;
    };
    setForm({
      buque_contenedor: cleanField(service.buque_contenedor),
      surveyor: cleanField(service.surveyor),
      honorarios: cleanField(service.honorarios),
      costo_operativo: cleanField(service.costo_operativo),
      costo_tarjetas: cleanField(service.costo_tarjetas),
      fecha_inicio: cleanField(service.fecha_inicio),
      hora_inicio: cleanField(service.hora_inicio),
      fecha_fin: cleanField(service.fecha_fin),
      hora_fin: cleanField(service.hora_fin),
      demoras: cleanField(service.demoras),
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
    if (!dateValue.trim() || dateValue.trim() === "-" || !timeValue.trim() || timeValue.trim() === "-") {
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
        const result = await offlineApiRequest(`/servicios/editar/${consec}`, {
          method: "PUT",
          session,
          offlineLabel: `Editar Servicio ${consec}`,
          body: {
            buque_contenedor: form.buque_contenedor,
            surveyor: form.surveyor,
            honorarios: toNumber(form.honorarios),
            costo_operativo: toNumber(form.costo_operativo),
            costo_tarjetas: cardCostAllowed ? toNumber(form.costo_tarjetas) : null,
            fecha_inicio: form.fecha_inicio,
            hora_inicio: form.hora_inicio
          }
        });
        if (isQueuedOffline(result)) {
          setMessage("Sin internet: cambios del servicio guardados en cache local.");
          return;
        }
      } else if (mode === "Generar Consecutivo") {
        const result = await offlineApiRequest(`/servicios/confirmar/${consec}`, {
          method: "PUT",
          session,
          offlineLabel: `Generar consecutivo Servicio ${consec}`,
          body: { fecha_inicio: form.fecha_inicio, hora_inicio: form.hora_inicio }
        });
        if (isQueuedOffline(result)) {
          setMessage("Sin internet: consecutivo guardado en cache local.");
          return;
        }
      } else if (mode === "Finalizar") {
        const closeResult = await offlineApiRequest(`/servicios/cerrar/${consec}`, {
          method: "PUT",
          session,
          offlineLabel: `Finalizar Servicio ${consec}`,
          body: { fecha_fin: form.fecha_fin, hora_fin: form.hora_fin }
        });
        const reportResult = await offlineApiRequest(`/servicios/generar_informe/${consec}`, {
          method: "PUT",
          session,
          offlineLabel: `Generar informe Servicio ${consec}`
        });
        if ([closeResult, reportResult].some(isQueuedOffline)) {
          setMessage("Sin internet: finalizacion del servicio guardada en cache local.");
          return;
        }
      } else if (mode === "Cancelar") {
        const result = await offlineApiRequest(`/servicios/cancelar/${consec}`, {
          method: "PUT",
          session,
          offlineLabel: `Cancelar Servicio ${consec}`,
          body: {
            estado: "Cancelado",
            razon_cancelacion: form.razon_cancelacion,
            comentario_cancelacion: form.comentario_cancelacion
          }
        });
        if (isQueuedOffline(result)) {
          setMessage("Sin internet: cancelacion guardada en cache local.");
          return;
        }
      } else if (mode === "Demoras") {
        const result = await offlineApiRequest(`/servicios/demoras/${consec}`, {
          method: "PUT",
          session,
          offlineLabel: `Demoras Servicio ${consec}`,
          body: { total: String(delayTotal ?? 0) }
        });
        if (isQueuedOffline(result)) {
          setMessage("Sin internet: demoras guardadas en cache local.");
          return;
        }
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
                  <Text style={styles.fieldValue}>{formatDateColumnValue(key, value)}</Text>
                </View>
              ))
            : null}

          {mode === "edit" ? (
            <>
              <Text style={styles.label}>Buque / Contenedor</Text>
              <TextInput style={styles.input} value={form.buque_contenedor} onChangeText={(value) => setValue("buque_contenedor", value)} />
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
              <DateField label="Fecha inicio" value={form.fecha_inicio} onChange={(value) => setValue("fecha_inicio", value)} />
              <Text style={styles.label}>Hora inicio</Text>
              <TextInput style={styles.input} value={form.hora_inicio} onChangeText={(value) => setValue("hora_inicio", value)} placeholder="HH:MM" />
            </>
          ) : null}

          {mode === "Generar Consecutivo" ? (
            <>
              <Text style={styles.helperText}>El backend asignara num_informe y pasara el servicio a En Operacion.</Text>
              <DateField label="Fecha inicio" value={form.fecha_inicio} onChange={(value) => setValue("fecha_inicio", value)} />
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
                    <Text style={styles.fieldValue}>{formatDateColumnValue(key, service?.[key])}</Text>
                  </View>
                ))}
              </View>
              <DateField label="Fecha finalizacion" value={form.fecha_fin} onChange={(value) => setValue("fecha_fin", value)} />
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
                  <DateField label="Fecha inicio" value={row.f1} onChange={(value) => updateDelayRow(index, "f1", value)} />
                  <Text style={styles.label}>Hora inicio</Text>
                  <TextInput style={styles.input} value={row.h1} onChangeText={(value) => updateDelayRow(index, "h1", value)} placeholder="HH:MM" />
                  <DateField label="Fecha fin" value={row.f2} onChange={(value) => updateDelayRow(index, "f2", value)} />
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
  inlineFields: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 10 },
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
  longTextInput: { minHeight: 82, textAlignVertical: "top" },
  lograAgendaCell: { color: "#101828", fontSize: 11, fontWeight: "700", paddingHorizontal: 8, paddingVertical: 8, width: 132 },
  lograAgendaHeader: { backgroundColor: BLUE },
  lograAgendaHeaderCell: { color: "white", fontWeight: "900" },
  lograAgendaRow: { borderBottomColor: BORDER, borderBottomWidth: 1, flexDirection: "row", minWidth: 1188 },
  lograAgendaToolbar: { backgroundColor: "#F8FAFC", borderColor: BORDER, borderRadius: 8, borderWidth: 1, gap: 10, marginBottom: 12, padding: 10 },
  lograCalendarDay: {
    borderBottomWidth: 1,
    borderColor: BORDER,
    borderRightWidth: 1,
    minHeight: 88,
    padding: 5,
    width: "14.285%"
  },
  lograCalendarDayMuted: { backgroundColor: "#F2F4F7" },
  lograCalendarDayNumber: { color: "#101828", fontSize: 12, fontWeight: "900" },
  lograCalendarDayNumberMuted: { color: "#98A2B3" },
  lograCalendarGrid: { borderColor: BORDER, borderLeftWidth: 1, borderTopWidth: 1, flexDirection: "row", flexWrap: "wrap" },
  lograCalendarHeader: { alignItems: "center", flexDirection: "row", justifyContent: "space-between", marginBottom: 10 },
  lograCalendarMeeting: { borderRadius: 6, marginTop: 4, paddingHorizontal: 4, paddingVertical: 3 },
  lograCalendarMeetingText: { color: "#101828", fontSize: 9, fontWeight: "800" },
  lograCalendarMoreText: { color: BLUE, fontSize: 9, fontWeight: "900", marginTop: 4 },
  lograCalendarPanel: { backgroundColor: "white", borderColor: BORDER, borderRadius: 8, borderWidth: 1, padding: 10 },
  lograCalendarTitle: { color: BLUE, fontSize: 16, fontWeight: "900" },
  lograCalendarWeekday: { color: "#475467", fontSize: 11, fontWeight: "900", paddingBottom: 6, textAlign: "center", width: "14.285%" },
  lograCalendarWeekRow: { flexDirection: "row" },
  lograToolbarHeader: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: 8, justifyContent: "space-between" },
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
  masterMobileActions: { flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 2 },
  masterMobilePanel: {
    backgroundColor: "#EEF6FF",
    borderColor: "#98C7F5",
    borderRadius: 8,
    borderWidth: 1,
    marginBottom: 12,
    padding: 12
  },
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
  secondaryButtonCompact: { alignItems: "center", borderColor: BLUE, borderRadius: 6, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 8 },
  secondaryButtonText: { color: BLUE, fontSize: 14, fontWeight: "800" },
  segmentedControl: { alignSelf: "flex-start", borderColor: BLUE, borderRadius: 6, borderWidth: 1, flexDirection: "row", overflow: "hidden" },
  segmentedOption: { paddingHorizontal: 12, paddingVertical: 8 },
  segmentedOptionActive: { backgroundColor: BLUE },
  segmentedText: { color: BLUE, fontSize: 13, fontWeight: "800" },
  segmentedTextActive: { color: "white", fontSize: 13, fontWeight: "800" },
  smallDangerButton: { alignItems: "center", backgroundColor: "#F4CCCC", borderRadius: 4, height: 28, justifyContent: "center", width: 32 },
  smallDangerButtonText: { color: "#7A271A", fontSize: 13, fontWeight: "900" },
  actionBar: { gap: 8, paddingVertical: 12 },
  actionButton: { backgroundColor: BLUE, borderRadius: 6, paddingHorizontal: 12, paddingVertical: 10 },
  actionButtonCompact: { alignItems: "center", backgroundColor: BLUE, borderRadius: 6, paddingHorizontal: 12, paddingVertical: 8 },
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
  contextActionPanel: { borderColor: BORDER, borderRadius: 8, borderWidth: 1, padding: 10 },
  contextActionRow: { alignItems: "center", flexDirection: "row", flexWrap: "wrap", gap: 8 },
  contextActionSelect: { minWidth: 220 },
  contextActionTitle: { color: "#344054", fontSize: 12, fontWeight: "900", marginBottom: 8, textTransform: "uppercase" },
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
  modalCloseCompact: { borderColor: "#B42318", borderRadius: 6, borderWidth: 1, paddingHorizontal: 12, paddingVertical: 8 },
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
  selectedRow: { borderColor: BLUE, borderWidth: 2 },
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
  timePartInput: { marginBottom: 0, paddingHorizontal: 8, textAlign: "center", width: 48 },
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
  },
  syncRow: {
    alignItems: "center",
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 16,
    paddingTop: 8
  },
  syncButton: {
    backgroundColor: "#00B8D9",
    borderRadius: 6,
    paddingHorizontal: 12,
    paddingVertical: 8
  },
  syncButtonText: { color: "#FFFFFF", fontSize: 12, fontWeight: "800" },
  syncMessage: { color: "#D6F7FF", flex: 1, fontSize: 12 }
});

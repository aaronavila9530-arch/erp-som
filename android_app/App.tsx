import * as LocalAuthentication from "expo-local-authentication";
import * as SecureStore from "expo-secure-store";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View
} from "react-native";

import { apiRequest, confirmTotp, login, LoginResponse, verifyTotp } from "./src/api/client";
import { AuthProvider, useAuth } from "./src/auth/AuthContext";
import { AppModule, AppSection, getAllowedModules } from "./src/config/modules";

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
            {payload ? <DataView moduleCode={activeModule.code} payload={payload} /> : null}
          </>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function DataView({ moduleCode, payload }: { moduleCode: string; payload: unknown }) {
  const rows = extractRows(payload);
  const numbers = flattenNumbers(payload).slice(0, 8);

  if (moduleCode === "dashboard") {
    return <DashboardView numbers={numbers} rows={rows} />;
  }

  if (rows.length > 0) return <ListView rows={rows} />;

  if (numbers.length > 0) return <KpiGrid numbers={numbers} />;

  const obj = asRecord(payload);
  if (obj) return <ObjectCards obj={obj} />;

  return <Text style={styles.empty}>{formatValue(payload)}</Text>;
}

function DashboardView({ numbers, rows }: { numbers: Array<{ label: string; value: number }>; rows: Record<string, unknown>[] }) {
  return (
    <View>
      <KpiGrid numbers={numbers} />
      {numbers.length ? <BarChart numbers={numbers.slice(0, 6)} /> : null}
      {rows.length ? <ListView rows={rows.slice(0, 8)} /> : null}
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
  empty: { color: "#697386", fontSize: 15, marginTop: 16 },
  error: { color: "#B42318", fontSize: 14, marginTop: 14 },
  fieldKey: { color: "#667085", flex: 1, fontSize: 12, fontWeight: "700", textTransform: "capitalize" },
  fieldRow: { flexDirection: "row", gap: 10, marginTop: 6 },
  fieldValue: { color: "#1D2939", flex: 1.3, fontSize: 12, textAlign: "right" },
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

export const API_BASE_URL = "https://api-som-fastapi-production-e66d.up.railway.app";

export type Session = {
  usuario: string;
  rol: string;
  token: string;
  company_code?: string;
  company_name?: string;
  modules: Array<{ label: string; code: string }>;
};

export type LoginResponse =
  | {
      action: "ENROLL_TOTP";
      usuario: string;
      rol: string;
      qr_base64: string;
    }
  | {
      action: "VERIFY_TOTP";
      usuario: string;
      rol: string;
    };

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  session?: Session | null;
};

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method: options.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json, text/plain, */*",
        ...(options.session
          ? {
              "X-User": options.session.usuario,
              "X-Role": options.session.rol,
              "X-User-Role": options.session.rol,
              "X-Company-Code": options.session.company_code || "MSL-CR",
              "X-Company-Name": options.session.company_name || "MSL MARINE SURVEYORS AND LOGISTICS GROUP SRL"
            }
          : {})
      },
      body: options.body ? JSON.stringify(options.body) : undefined
    });
  } catch (err) {
    throw new Error(err instanceof Error ? err.message : "Network request failed");
  }

  const text = await response.text();
  let data: unknown = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { message: text };
    }
  }

  if (!response.ok) {
    const obj = data && typeof data === "object" && !Array.isArray(data) ? (data as Record<string, unknown>) : null;
    const detail = obj?.detail || obj?.error || obj?.message || "Error de comunicacion con ERP SOM";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data as T;
}

export function login(usuario: string, password: string) {
  return apiRequest<LoginResponse>("/auth/mobile/login", {
    method: "POST",
    body: { usuario, password }
  });
}

export function confirmTotp(usuario: string, codigo: string) {
  return apiRequest<Session>("/auth/mobile/totp/confirm", {
    method: "POST",
    body: { usuario, codigo }
  });
}

export function verifyTotp(usuario: string, codigo: string) {
  return apiRequest<Session>("/auth/mobile/totp/verify", {
    method: "POST",
    body: { usuario, codigo }
  });
}

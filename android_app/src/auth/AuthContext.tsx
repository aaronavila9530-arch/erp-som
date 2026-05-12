import AsyncStorage from "@react-native-async-storage/async-storage";
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

import type { Session } from "../api/client";

const SESSION_KEY = "erp_som_session";

type AuthContextValue = {
  session: Session | null;
  loading: boolean;
  setSession: (session: Session) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSessionState] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    AsyncStorage.getItem(SESSION_KEY)
      .then((value) => {
        if (value) {
          setSessionState(JSON.parse(value));
        }
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      loading,
      setSession: async (nextSession) => {
        setSessionState(nextSession);
        await AsyncStorage.setItem(SESSION_KEY, JSON.stringify(nextSession));
      },
      logout: async () => {
        setSessionState(null);
        await AsyncStorage.removeItem(SESSION_KEY);
      }
    }),
    [loading, session]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return ctx;
}

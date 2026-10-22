import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import authApi from "../api/auth";
import { endSession, logoutRequest, onAuthChange, refreshSession } from "../api/axiosClient";
import type { AuthSession, FeatureConfig, User } from "../api/types";
import { hasSessionHint, setSessionHint, setToken } from "../lib/authStorage";
import { FeaturesContext } from "./FeaturesContext";

type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: User | null;
  status: AuthStatus;
  isLoggedIn: boolean;
  googleEnabled: boolean;
  login: (accessToken: string, user: User) => void;
  logout: () => Promise<void>;
  completeOAuth: () => Promise<AuthSession>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // "loading" until we know whether the refresh cookie still holds a session
  const [status, setStatus] = useState<AuthStatus>(hasSessionHint() ? "loading" : "anonymous");
  const [features, setFeatures] = useState<FeatureConfig>({ google: false, sandbox: false });

  useEffect(() => {
    const unsubscribe = onAuthChange((event) => {
      if (event.type === "refreshed") {
        setUser(event.user);
        setStatus("authenticated");
      } else {
        setUser(null);
        setStatus("anonymous");
      }
    });

    if (hasSessionHint()) {
      refreshSession().catch(() => endSession());
    }
    authApi
      .config()
      .then(({ data }) => setFeatures({ google: Boolean(data.google), sandbox: Boolean(data.sandbox) }))
      .catch(() => {});

    return unsubscribe;
  }, []);

  const login = useCallback((accessToken: string, newUser: User) => {
    setToken(accessToken);
    setSessionHint(true);
    setUser(newUser);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest(); // revokes the refresh token and clears the cookie
    } catch {
      // still sign out locally
    }
    endSession();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      isLoggedIn: status === "authenticated",
      googleEnabled: features.google,
      login,
      logout,
      completeOAuth: refreshSession,
    }),
    [user, status, features.google, login, logout]
  );
  return (
    <AuthContext.Provider value={value}>
      <FeaturesContext.Provider value={features}>{children}</FeaturesContext.Provider>
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

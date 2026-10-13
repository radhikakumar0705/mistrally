import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import authApi from "../api/auth";
import { endSession, logoutRequest, onAuthChange, refreshSession } from "../api/axiosClient";
import { hasSessionHint, setSessionHint, setToken } from "../lib/authStorage";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // "loading" until we know whether the refresh cookie still holds a session
  const [status, setStatus] = useState(hasSessionHint() ? "loading" : "anonymous");
  const [googleEnabled, setGoogleEnabled] = useState(false);

  useEffect(() => {
    const unsubscribe = onAuthChange((event) => {
      if (event.type === "refreshed") {
        setUser(event.user);
        setStatus("authenticated");
      } else if (event.type === "ended") {
        setUser(null);
        setStatus("anonymous");
      }
    });

    if (hasSessionHint()) {
      refreshSession().catch(() => endSession());
    }
    authApi
      .config()
      .then(({ data }) => setGoogleEnabled(Boolean(data.google)))
      .catch(() => {});

    return unsubscribe;
  }, []);

  const login = useCallback((accessToken, newUser) => {
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

  const value = useMemo(
    () => ({
      user,
      status,
      isLoggedIn: status === "authenticated",
      googleEnabled,
      login,
      logout,
      completeOAuth: refreshSession,
    }),
    [user, status, googleEnabled, login, logout]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}

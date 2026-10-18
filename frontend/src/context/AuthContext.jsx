import { useCallback, useEffect, useState } from "react";
import { UNAUTHORIZED_EVENT, signOutRequest } from "../api";
import { AuthContext } from "./contexts";

const STORAGE_KEY = "letterlens_auth";

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(load);

  function signIn(session) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    setAuth(session);
  }

  const clear = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
  }, []);

  function signOut() {
    // Revoke the session server-side too; clear locally either way.
    if (auth?.token) signOutRequest(auth.token).catch(() => {});
    clear();
  }

  // The backend rejected our token (expired or revoked) -- sign in again.
  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, clear);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, clear);
  }, [clear]);

  return (
    <AuthContext.Provider
      value={{ token: auth?.token, userId: auth?.user_id, phone: auth?.phone, signIn, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

import { createContext, useContext, useState } from "react";

const STORAGE_KEY = "letterlens_auth";
const AuthContext = createContext(null);

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

  function signOut() {
    localStorage.removeItem(STORAGE_KEY);
    setAuth(null);
  }

  return (
    <AuthContext.Provider
      value={{ token: auth?.token, userId: auth?.user_id, phone: auth?.phone, signIn, signOut }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

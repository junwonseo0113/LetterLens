import { createContext } from "react";

// Kept apart from the provider components so Vite fast refresh works.
export const AuthContext = createContext(null);
export const LanguageContext = createContext(null);
export const FontScaleContext = createContext(null);

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import { FontScaleProvider } from "./context/FontScaleContext.jsx";
import { LanguageProvider } from "./context/LanguageContext.jsx";
import "./index.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <LanguageProvider>
        <FontScaleProvider>
          <AuthProvider>
            <App />
          </AuthProvider>
        </FontScaleProvider>
      </LanguageProvider>
    </BrowserRouter>
  </StrictMode>,
);

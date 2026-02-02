import "@assistant-ui/react-markdown/styles/dot.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/600.css";
import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import "./styles/base.css";
import "./styles/overrides.css";
import { App } from "./App";

// Polyfill clipboard API for non-secure contexts (HTTP)
// This is needed because navigator.clipboard is only available in secure contexts
if (!navigator.clipboard) {
  const clipboardPolyfill = {
    writeText: (text: string): Promise<void> => {
      return new Promise((resolve, reject) => {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.select();
        try {
          document.execCommand("copy");
          resolve();
        } catch {
          reject(new Error("Copy failed"));
        } finally {
          document.body.removeChild(textarea);
        }
      });
    },
    readText: () => Promise.reject(new Error("Not supported")),
    read: () => Promise.reject(new Error("Not supported")),
    write: () => Promise.reject(new Error("Not supported")),
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  };
  Object.defineProperty(navigator, "clipboard", {
    value: clipboardPolyfill,
    writable: false,
  });
}

const rootElement = document.getElementById("app");

if (!rootElement) {
  throw new Error("Missing #app element");
}

createRoot(rootElement).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/new" replace />} />
        <Route path="/new" element={<App />} />
        <Route path="/c/:conversationId" element={<App />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);

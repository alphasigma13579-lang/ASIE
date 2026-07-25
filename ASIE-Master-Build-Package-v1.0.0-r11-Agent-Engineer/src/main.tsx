import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { AdminConsole } from "./AdminConsole";
import { DIBWorkspace } from "./DIBWorkspace";
import "./styles.css";

function Root() {
  if (window.location.hash === "#admin") return <AdminConsole />;
  if (window.location.hash === "#dib") return <DIBWorkspace />;
  return (
    <>
      <a
        href="#dib"
        style={{
          position: "fixed",
          left: 18,
          bottom: 18,
          zIndex: 1000,
          borderRadius: 12,
          padding: "10px 14px",
          background: "#173f69",
          color: "#fff",
          textDecoration: "none",
          fontWeight: 700,
          boxShadow: "0 8px 24px rgba(0,0,0,.18)",
        }}
      >
        Dynamic Input Blueprint
      </a>
      <App />
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
);

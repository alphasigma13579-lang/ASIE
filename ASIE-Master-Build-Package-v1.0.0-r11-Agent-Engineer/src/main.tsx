import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { AdminConsole } from "./AdminConsole";
import { DIBWorkspace } from "./DIBWorkspace";
import "./styles.css";

const currentHash = window.location.hash;

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {currentHash === "#admin" ? <AdminConsole /> : currentHash.startsWith("#dib") ? <DIBWorkspace /> : <App />}
  </React.StrictMode>
);

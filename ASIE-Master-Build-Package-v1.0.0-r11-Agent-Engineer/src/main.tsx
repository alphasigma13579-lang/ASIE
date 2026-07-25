import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { AdminConsole } from "./AdminConsole";
import { DIBWorkspace } from "./DIBWorkspace";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {window.location.hash === "#admin" ? <AdminConsole /> : window.location.hash === "#dib" ? <DIBWorkspace /> : <App />}
  </React.StrictMode>
);

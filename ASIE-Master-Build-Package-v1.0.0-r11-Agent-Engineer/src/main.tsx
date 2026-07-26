import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { AdminConsole } from "./AdminConsole";
import { DIBProjectCardDirectActionMount } from "./DIBProjectCardDirectAction";
import { DIBProjectEntryPoint } from "./DIBProjectEntryPoint";
import { DIBWorkspace } from "./DIBWorkspace";
import "./styles.css";

const currentHash = window.location.hash;
const routedApp = currentHash === "#admin" ? <AdminConsole /> : currentHash.startsWith("#dib-entry") ? <DIBProjectEntryPoint /> : currentHash.startsWith("#dib") ? <DIBWorkspace /> : <App />;
const showDIBCardDirectAction = !currentHash.startsWith("#admin") && !currentHash.startsWith("#dib");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {routedApp}
    {showDIBCardDirectAction ? <DIBProjectCardDirectActionMount /> : null}
  </React.StrictMode>
);

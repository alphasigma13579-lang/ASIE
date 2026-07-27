import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { AdminConsole } from "./AdminConsole";
import { DIBControlledFinanceWiring } from "./DIBControlledFinanceWiring";
import { DIBE2EScenario } from "./DIBE2EScenario";
import { DIBIntakeItemGovernance } from "./DIBIntakeItemGovernance";
import { DIBManifestRunReadiness } from "./DIBManifestRunReadiness";
import { DIBProjectCardDirectActionMount } from "./DIBProjectCardDirectAction";
import { DIBProjectEntryPoint } from "./DIBProjectEntryPoint";
import { DIBSnapshotProjectionHandoff } from "./DIBSnapshotProjectionHandoff";
import { DIBWorkspace } from "./DIBWorkspace";
import "./styles.css";
import "./asie-reference-theme.css";

const currentHash = window.location.hash;
const routedApp = currentHash === "#admin"
  ? <AdminConsole />
  : currentHash.startsWith("#dib-e2e-scenario")
    ? <DIBE2EScenario />
    : currentHash.startsWith("#dib-snapshot-handoff")
      ? <DIBSnapshotProjectionHandoff />
      : currentHash.startsWith("#dib-finance-wiring")
        ? <DIBControlledFinanceWiring />
        : currentHash.startsWith("#dib-run-readiness")
          ? <DIBManifestRunReadiness />
          : currentHash.startsWith("#dib-governance")
            ? <DIBIntakeItemGovernance />
            : currentHash.startsWith("#dib-entry")
              ? <DIBProjectEntryPoint />
              : currentHash.startsWith("#dib")
                ? <DIBWorkspace />
                : <App />;
const showDIBCardDirectAction = !currentHash.startsWith("#admin") && !currentHash.startsWith("#dib");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    {routedApp}
    {showDIBCardDirectAction ? <DIBProjectCardDirectActionMount /> : null}
  </React.StrictMode>
);

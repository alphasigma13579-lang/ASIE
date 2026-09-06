import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import { AdminConsole } from "./AdminConsole";
import { ASIECompleteSurfaceMount } from "./ASIECompleteSurfaceMount";
import { CustomerLanguageProvider } from "./customerLanguage";
import { EngineeringSurfaceGate } from "./EngineeringSurfaceGate";
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
import "./asie-complete-surface.css";

const currentHash = window.location.hash;
const routedApp = currentHash === "#admin"
  ? <AdminConsole />
  : currentHash.startsWith("#dib-e2e-scenario")
    ? <EngineeringSurfaceGate><DIBE2EScenario /></EngineeringSurfaceGate>
    : currentHash.startsWith("#dib-snapshot-handoff")
      ? <EngineeringSurfaceGate><DIBSnapshotProjectionHandoff /></EngineeringSurfaceGate>
      : currentHash.startsWith("#dib-finance-wiring")
        ? <EngineeringSurfaceGate><DIBControlledFinanceWiring /></EngineeringSurfaceGate>
        : currentHash.startsWith("#dib-run-readiness")
          ? <EngineeringSurfaceGate><DIBManifestRunReadiness /></EngineeringSurfaceGate>
          : currentHash.startsWith("#dib-governance")
            ? <EngineeringSurfaceGate><DIBIntakeItemGovernance /></EngineeringSurfaceGate>
            : currentHash.startsWith("#dib-entry")
              ? <EngineeringSurfaceGate><DIBProjectEntryPoint /></EngineeringSurfaceGate>
              : currentHash.startsWith("#dib")
                ? <EngineeringSurfaceGate><DIBWorkspace /></EngineeringSurfaceGate>
                : <App />;
const showDIBCardDirectAction = !currentHash.startsWith("#admin") && !currentHash.startsWith("#dib");

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <CustomerLanguageProvider>
      {routedApp}
      <ASIECompleteSurfaceMount />
      {showDIBCardDirectAction ? <DIBProjectCardDirectActionMount /> : null}
    </CustomerLanguageProvider>
  </React.StrictMode>
);

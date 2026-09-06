import React, { useEffect, useState } from "react";
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
import { DIBProjectEntryPoint } from "./DIBProjectEntryPoint";
import { DIBSnapshotProjectionHandoff } from "./DIBSnapshotProjectionHandoff";
import { DIBWorkspace } from "./DIBWorkspace";
import "./styles.css";
import "./asie-reference-theme.css";
import "./asie-complete-surface.css";

function RoutedApplication() {
  const [currentHash, setCurrentHash] = useState(() => window.location.hash);

  useEffect(() => {
    const syncHash = () => setCurrentHash(window.location.hash);
    window.addEventListener("hashchange", syncHash);
    return () => window.removeEventListener("hashchange", syncHash);
  }, []);

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

  return (
    <>
      {routedApp}
      <ASIECompleteSurfaceMount />
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <CustomerLanguageProvider>
      <RoutedApplication />
    </CustomerLanguageProvider>
  </React.StrictMode>
);

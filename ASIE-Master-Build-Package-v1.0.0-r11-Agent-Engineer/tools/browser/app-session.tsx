import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "../../src/App";
import { CustomerLanguageProvider } from "../../src/customerLanguage";
import "../../src/styles.css";
import "../../src/asie-reference-theme.css";
import "../../src/asie-complete-surface.css";

createRoot(document.getElementById("root")!).render(<StrictMode><CustomerLanguageProvider><App /></CustomerLanguageProvider></StrictMode>);

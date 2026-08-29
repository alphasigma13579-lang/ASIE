/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GOOGLE_MAPS_BROWSER_KEY?: string;
  readonly VITE_GOOGLE_MAP_ID?: string;
  readonly VITE_ASIE_LIVE_BROWSER_MAPS_ENABLED?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

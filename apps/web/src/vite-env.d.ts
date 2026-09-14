/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ASK_DEADLINE_MS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

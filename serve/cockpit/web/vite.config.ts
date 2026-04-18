/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)

function pdsPartialsPlugin() {
  return {
    name: 'pds-partials',
    transformIndexHtml(html: string): string {
      try {
        const partials = require('@porsche-design-system/components-react/partials') as Record<
          string,
          (() => string) | undefined
        >
        const getInitialStyles = partials['getInitialStyles']
        if (typeof getInitialStyles !== 'function') return html
        const css = getInitialStyles()
        return css ? html.replace('</head>', `<style>${css}</style>\n  </head>`) : html
      } catch {
        return html
      }
    },
  }
}

export default defineConfig({
  plugins: [react(), pdsPartialsPlugin()],
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
  },
})

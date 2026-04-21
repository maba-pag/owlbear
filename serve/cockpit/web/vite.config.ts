import { defineConfig } from 'vitest/config'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)

function cspPlugin() {
  const policy = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "connect-src 'self'",
  ].join('; ')
  return {
    name: 'csp-meta',
    apply: 'build' as const,
    transformIndexHtml(html: string): string {
      return html.replace('</head>', `  <meta http-equiv="Content-Security-Policy" content="${policy}">\n  </head>`)
    },
  }
}

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
  plugins: [react(), babel({ presets: [reactCompilerPreset()] }), pdsPartialsPlugin(), cspPlugin()],
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    globals: true,
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    testTimeout: 10_000,
    teardownTimeout: 3_000,
  },
})

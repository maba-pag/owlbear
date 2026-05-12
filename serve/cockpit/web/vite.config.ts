import { defineConfig } from 'vitest/config'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'

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

export default defineConfig({
  plugins: [react(), babel({ presets: [reactCompilerPreset()] }), cspPlugin()],
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

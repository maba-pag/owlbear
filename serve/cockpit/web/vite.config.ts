import { defineConfig } from 'vitest/config'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import babel from '@rolldown/plugin-babel'
import { Features } from 'lightningcss'
import * as fs from 'node:fs'
import { join } from 'node:path'

const pdsColorSchemeCssPath = join(
  process.cwd(),
  'node_modules/@porsche-design-system/components-js/global-styles/color-scheme.css',
)

function cspPlugin() {
  const policy = [
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "font-src 'self' https://cdn.ui.porsche.com",
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

function pdsVersionCheckPlugin() {
  let rootDir = ''

  return {
    name: 'pds-version-check',
    configResolved(config: { root: string }) {
      rootDir = config.root
    },
    buildStart() {
      try {
        const packageJsonPath = join(rootDir, 'node_modules/@porsche-design-system/components-js/package.json')
        const packageVersion = JSON.parse(fs.readFileSync(packageJsonPath, 'utf-8')) as { version?: string }
        const npmVersion = packageVersion.version ?? ''

        const assetsDir = join(rootDir, 'public/porsche-design-system/components')
        const files = fs.readdirSync(assetsDir)
        const coreChunk = files.find((file) => /^porsche-design-system\.v(\d+\.\d+\.\d+)\./.test(file))

        if (!coreChunk) {
          console.warn('PDS version check: no matching core asset found. Run npm run sync:pds')
          return
        }

        const match = coreChunk.match(/^porsche-design-system\.v(\d+\.\d+\.\d+)\./)
        const assetVersion = match?.[1] ?? ''

        if (assetVersion !== npmVersion) {
          console.warn(
            `PDS version mismatch: assets=${assetVersion}, npm=${npmVersion}. Run npm run sync:pds`,
          )
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error)
        console.warn(`PDS version check skipped: ${message}`)
      }
    },
  }
}

export default defineConfig({
  plugins: [tailwindcss(), react(), babel({ presets: [reactCompilerPreset()] }), pdsVersionCheckPlugin(), cspPlugin()],
  resolve: {
    alias: {
      '@porsche-design-system/components-react/global-styles/color-scheme.css':
        pdsColorSchemeCssPath,
    },
  },
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  css: {
    lightningcss: {
      exclude: Features.LightDark,
    },
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

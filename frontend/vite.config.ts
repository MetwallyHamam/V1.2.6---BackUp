import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import type { Plugin } from 'vite'
import { loadEnv } from 'vite'

const redirectRootToSupportHub = (): Plugin => ({
  name: 'redirect-root-to-support-hub',
  configureServer(server) {
    server.middlewares.use((request, response, next) => {
      if ((request as { url?: string }).url === '/') {
        response.statusCode = 302
        response.setHeader('Location', '/SupportHub/login')
        response.end()
        return
      }
      next()
    })
  },
})

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, '.', '')
  return {
  base: environment.VITE_BASE_PATH || '/SupportHub/',
  plugins: [redirectRootToSupportHub(), react()],
  build: {
    modulePreload: {
      resolveDependencies: (_filename, dependencies) =>
        dependencies.filter((dependency) => !/\/query-[^/]+\.js$/.test(dependency)),
    },
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.indexOf('node_modules') === -1) return undefined
          if (id.indexOf('@mui') !== -1 || id.indexOf('@emotion') !== -1) return 'mui'
          if (id.indexOf('@tanstack') !== -1) return 'query'
          if (id.indexOf('leaflet') !== -1 || id.indexOf('geojson-world-map') !== -1) return 'maps'
          return 'vendor'
        },
      },
    },
  },
  server: { port: 5173 },
  optimizeDeps: { exclude: ['maplibre-gl'] },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', globals: true },
  }
})

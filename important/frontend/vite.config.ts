import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const backendPort = process.env.VITE_BACKEND_PORT || '8000'
const backendUrl = process.env.VITE_BACKEND_URL || `http://127.0.0.1:${backendPort}`
const frontendPort = parseInt(process.env.VITE_PORT || '5173', 10)

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    proxy: {
      '/api': {
        target: backendUrl,
        changeOrigin: true,
      },
    },
  },
})

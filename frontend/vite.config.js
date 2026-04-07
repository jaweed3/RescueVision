import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/detect': 'http://localhost:1150',
      '/health': 'http://localhost:1150',
      '/inject': 'http://localhost:1150',
      '/export': 'http://localhost:1150',
    }
  }
})

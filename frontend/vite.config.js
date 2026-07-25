import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const TARGET = 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health':            TARGET,
      '/upload':            TARGET,
      '/query':             TARGET,
      '/documents':         TARGET,
      '/config':            TARGET,
      '/conversations':     TARGET,
    },
  },
})
